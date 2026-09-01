"""Autenticación oficial de EcoNexo y registro gratuito de EcoNexoFoI."""
from __future__ import annotations

import re
import unicodedata
from uuid import uuid4

import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from .. import db
from ..config import get_settings
from ..deps import CurrentUser, current_user
from ..foi_schemas import CommunityRegisterIn
from ..rate_limit import clear_rate_limit, enforce_rate_limit
from ..schemas import (
    ChangePasswordIn,
    GoogleAuthIn,
    LoginIn,
    RegisterIn,
    RegistrationPendingOut,
    TokenOut,
)
from ..security import (
    burn_verification_time,
    create_access_token,
    hash_secret,
    verify_secret,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    clean = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return clean[:72] or "organizacion"


def _validate_password(password: str) -> None:
    if len(password) < 8 or not any(char.isalpha() for char in password) or not any(char.isdigit() for char in password):
        raise HTTPException(422, "La contraseña debe tener al menos 8 caracteres, una letra y un número")


def _session(row, *, is_new_user: bool = False) -> TokenOut:
    account_type = row.get("account_type") or "institutional"
    email = str(row.get("email") or "")
    platform_admin = bool(row.get("platform_admin") or email.lower() in get_settings().platform_admin_list)
    token = create_access_token(
        str(row["id"]),
        str(row["org_id"]),
        str(row["role"]),
        account_type=account_type,
        email=email,
        platform_admin=platform_admin,
    )
    return TokenOut(
        access_token=token,
        org_id=row["org_id"],
        role=str(row["role"]),
        name=str(row["name"]),
        email=email,
        avatar_url=row.get("avatar_url"),
        auth_provider=str(row.get("auth_provider") or "password"),
        account_type=account_type,
        is_new_user=is_new_user,
        platform_admin=platform_admin,
        must_change_password=bool(row.get("must_change_password") or False),
    )


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request) -> TokenOut:
    settings = get_settings()
    await enforce_rate_limit(
        request, bucket="auth-password", limit=settings.login_attempt_limit,
        window_seconds=settings.login_attempt_window_seconds,
    )
    row = await db.pool().fetchrow(
        """
        SELECT u.id, u.org_id, u.role::text AS role, u.name, u.email,
               u.password_hash, u.avatar_url, u.auth_provider, u.account_type,
               u.must_change_password, u.is_active,
               COALESCE(o.is_active, true) AS organization_active,
               COALESCE(o.access_status, 'approved') AS access_status,
               false AS platform_admin
        FROM users u
        JOIN organizations o ON o.id=u.org_id
        WHERE lower(u.email)=lower($1)
        """,
        str(body.email).strip(),
    )
    if row is None:
        # Se gasta el tiempo de argon2 igual: sin esto el correo inexistente
        # respondia mucho mas rapido y delataba que cuentas existen.
        burn_verification_time()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    if not verify_secret(body.password, row["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    # Recien con la contraseña verificada se explica por que no puede entrar:
    # antes de eso el mensaje delataria que la cuenta existe.
    if row["access_status"] == "pending":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Tu alta está pendiente de aprobación. Administración general te contactará "
            "por WhatsApp al teléfono que registraste para habilitar el acceso.",
        )
    if not row["is_active"] or not row["organization_active"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Tu cuenta está suspendida. Escribí a administración general para reactivarla.",
        )
    await db.pool().execute("UPDATE users SET last_login_at=now() WHERE id=$1", row["id"])
    # Credencial correcta: no hay fuerza bruta que limitar desde esta IP.
    await clear_rate_limit(request, bucket="auth-password")
    return _session(row)


@router.post(
    "/register",
    response_model=RegistrationPendingOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def register_organization(body: RegisterIn, request: Request) -> RegistrationPendingOut:
    """Registra la solicitud de alta institucional. No otorga acceso todavía.

    La organización queda en ``pending`` hasta que administración general la
    habilite, después de cobrar la licencia. El teléfono es el canal por el que
    se hace ese contacto.
    """
    await enforce_rate_limit(request, bucket="auth-register", limit=6, window_seconds=60 * 60)
    if not body.terms_accepted:
        raise HTTPException(422, "Debés aceptar los términos y la política de privacidad")
    _validate_password(body.password)
    email = str(body.email).strip().lower()
    base_slug = _slug(body.organization_name)
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            if await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE lower(email)=lower($1))", email):
                raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")
            slug = base_slug
            if await conn.fetchval("SELECT EXISTS(SELECT 1 FROM organizations WHERE slug=$1)", slug):
                slug = f"{base_slug[:62]}-{uuid4().hex[:8]}"
            org_id = await conn.fetchval(
                """
                INSERT INTO organizations (
                    name, slug, vertical, primary_color, province, department,
                    municipality, territory_scope, is_active, access_status
                ) VALUES ($1,$2,$3::org_vertical,'#059669','Misiones',$4,$5,'municipal',false,'pending')
                RETURNING id
                """,
                body.organization_name.strip(), slug, body.vertical,
                body.department, body.municipality,
            )
            try:
                await conn.execute(
                    """
                    INSERT INTO users (
                        org_id,email,name,phone,role,password_hash,auth_provider,
                        email_verified,terms_accepted_at,legal_version,account_type,is_active
                    ) VALUES ($1,$2,$3,$4,'admin',$5,'password',false,now(),$6,'institutional',true)
                    """,
                    org_id, email, body.name.strip(), body.phone,
                    hash_secret(body.password), body.legal_version,
                )
            except asyncpg.UniqueViolationError as exc:
                raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado") from exc
    return RegistrationPendingOut(
        organization_id=org_id,
        organization_name=body.organization_name.strip(),
        email=email,
        phone=body.phone,
        detail=(
            "Recibimos tu solicitud. Administración general va a contactarte por WhatsApp "
            f"al {body.phone} para coordinar la licencia y habilitar el acceso."
        ),
    )


@router.post("/community/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register_community(body: CommunityRegisterIn, request: Request) -> TokenOut:
    await enforce_rate_limit(request, bucket="auth-community-register", limit=6, window_seconds=60 * 60)
    if not body.terms_accepted:
        raise HTTPException(422, "Debés aceptar los términos y la política de privacidad")
    _validate_password(body.password)
    email = str(body.email).strip().lower()
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            if await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE lower(email)=lower($1))", email):
                raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")
            org_id = await conn.fetchval(
                """
                INSERT INTO organizations (name,slug,vertical,primary_color,baseline_response_s)
                VALUES ('EcoNexoFoI · Comunidad abierta','econexofoi-community','forestal','#059669',3600)
                ON CONFLICT (slug) DO UPDATE SET name=EXCLUDED.name
                RETURNING id
                """
            )
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO users (
                        org_id,email,name,role,password_hash,auth_provider,
                        email_verified,terms_accepted_at,legal_version,account_type,is_active
                    ) VALUES ($1,$2,$3,'visualizador',$4,'password',false,now(),$5,'community',true)
                    RETURNING id,org_id,role::text AS role,name,email,avatar_url,
                              auth_provider,account_type,must_change_password,false AS platform_admin
                    """,
                    org_id, email, body.name.strip(), hash_secret(body.password), body.legal_version,
                )
                await conn.execute(
                    """
                    INSERT INTO foi_profiles (user_id,headline,institution,discipline)
                    VALUES ($1,$2,$3,$4)
                    """,
                    row["id"],
                    body.discipline.strip() if body.discipline else "Investigador/a independiente",
                    body.institution.strip() if body.institution else None,
                    body.discipline.strip() if body.discipline else None,
                )
            except asyncpg.UniqueViolationError as exc:
                raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado") from exc
    return _session(row, is_new_user=True)


async def _verify_google_credential(credential: str) -> dict:
    settings = get_settings()
    if not settings.google_client_id_list:
        raise HTTPException(503, "El acceso con Google todavía no está configurado")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": credential},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Google no respondió. Intentá nuevamente") from exc
    if response.status_code != 200:
        raise HTTPException(401, "La credencial de Google no es válida")
    payload = response.json()
    if payload.get("aud") not in settings.google_client_id_list:
        raise HTTPException(401, "La credencial no corresponde a EcoNexo")
    if payload.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(401, "Emisor de Google no válido")
    if str(payload.get("email_verified", "")).lower() != "true" or not payload.get("email") or not payload.get("sub"):
        raise HTTPException(401, "Google no confirmó el correo de esta cuenta")
    return payload


@router.post("/google", response_model=TokenOut)
async def google_auth(body: GoogleAuthIn, request: Request) -> TokenOut:
    await enforce_rate_limit(request, bucket="auth-google", limit=20, window_seconds=15 * 60)
    identity = await _verify_google_credential(body.credential)
    email = str(identity["email"]).strip().lower()
    google_sub = str(identity["sub"])
    name = str(identity.get("name") or email.split("@", 1)[0])[:100]
    avatar_url = str(identity.get("picture") or "")[:1000] or None

    async with db.pool().acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT u.id,u.org_id,u.role::text AS role,u.name,u.email,u.avatar_url,
                       u.auth_provider,u.account_type,u.must_change_password,
                       false AS platform_admin,o.is_active AS organization_active,
                       COALESCE(o.access_status,'approved') AS access_status
                FROM users u JOIN organizations o ON o.id=u.org_id
                WHERE u.is_active AND (u.google_sub=$1 OR lower(u.email)=lower($2))
                """,
                google_sub, email,
            )
            if row is not None:
                if row["access_status"] == "pending":
                    raise HTTPException(
                        403,
                        "Tu alta está pendiente de aprobación. Administración general te "
                        "contactará por WhatsApp para habilitar el acceso.",
                    )
                if not row["organization_active"]:
                    raise HTTPException(403, "La organización está deshabilitada")
                await conn.execute(
                    """
                    UPDATE users SET google_sub=$2,auth_provider='google',email_verified=true,
                        avatar_url=COALESCE($3,avatar_url),last_login_at=now(),updated_at=now()
                    WHERE id=$1
                    """,
                    row["id"], google_sub, avatar_url,
                )
                data = dict(row)
                data.update({"auth_provider": "google", "avatar_url": avatar_url or row["avatar_url"]})
                return _session(data)

            if body.mode != "register":
                raise HTTPException(404, "No existe una cuenta de EcoNexo para este correo")
            # El alta institucional necesita un telefono de contacto para que
            # administracion general pueda coordinar la licencia, y Google no lo
            # entrega. Se deriva al formulario por email, que si lo pide.
            raise HTTPException(
                422,
                "El alta institucional se hace con el formulario de email, que pide un "
                "teléfono de contacto. Después vas a poder entrar con Google.",
            )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def change_password(body: ChangePasswordIn, request: Request, user: CurrentUser = Depends(current_user)) -> Response:
    await enforce_rate_limit(request, bucket="auth-change-password", limit=8, window_seconds=15 * 60)
    _validate_password(body.new_password)
    row = await db.pool().fetchrow("SELECT password_hash FROM users WHERE id=$1 AND is_active", user.id)
    if row is None or not verify_secret(body.current_password, row["password_hash"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña actual no es correcta")
    await db.pool().execute(
        """
        UPDATE users SET password_hash=$2,auth_provider='password',
                         must_change_password=false,password_changed_at=now(),updated_at=now()
        WHERE id=$1
        """,
        user.id, hash_secret(body.new_password),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
