"""Autenticacion por email/password y Google Identity Services."""
from __future__ import annotations

import asyncpg
from fastapi import APIRouter, HTTPException, Request, status

from .. import db
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from ..admin_notifications import create_notification, request_context
from ..rate_limit import enforce_rate_limit
from ..schemas import EmailRegisterIn, GoogleAuthIn, LoginIn, TokenOut
from ..subscriptions import ensure_subscription, sync_modules
from ..config import get_settings
from ..deps import CurrentUser, current_user

from ..schemas import (
    ChangePasswordIn,
    EmailRegisterIn,
    GoogleAuthIn,
    LoginIn,
    TokenOut,
)

from ..security import (
    create_access_token,
    hash_secret,
    new_token,
    slugify,
    verify_google_credential,
    verify_secret,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token(row, *, provider: str, is_new_user: bool = False) -> TokenOut:
    email = str(row["email"]).strip().lower()

    token = create_access_token(
        str(row["id"]),
        str(row["org_id"]),
        row["role"],
    )

    return TokenOut(
        access_token=token,
        org_id=row["org_id"],
        role=row["role"],
        name=row["name"],
        email=email,
        avatar_url=row.get("avatar_url"),
        auth_provider=provider,
        is_new_user=is_new_user,
        platform_admin=email in get_settings().platform_admin_list,
        must_change_password=bool(
            row.get("must_change_password", False)
        ),
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def change_password(
    body: ChangePasswordIn,
    user: CurrentUser = Depends(current_user),
) -> Response:
    row = await db.pool().fetchrow(
        """
        SELECT password_hash
        FROM users
        WHERE id=$1 AND org_id=$2 AND is_active
        """,
        user.id,
        user.org_id,
    )

    if row is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Usuario no encontrado",
        )

    if not verify_secret(
        body.current_password,
        row["password_hash"],
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "La contraseña actual es incorrecta",
        )

    if verify_secret(
        body.new_password,
        row["password_hash"],
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "La contraseña nueva debe ser diferente",
        )

    await db.pool().execute(
        """
        UPDATE users
        SET password_hash=$3,
            must_change_password=false,
            password_changed_at=now()
        WHERE id=$1 AND org_id=$2
        """,
        user.id,
        user.org_id,
        hash_secret(body.new_password),
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
    )
    return _token(row, provider="password")


async def _unique_org_slug(base_name: str) -> str:
    base = slugify(base_name)
    candidate = base
    suffix = 2
    while await db.pool().fetchval(
        "SELECT EXISTS(SELECT 1 FROM organizations WHERE slug=$1)", candidate
    ):
        candidate = f"{base[:42]}-{suffix}"
        suffix += 1
    return candidate


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register_email(body: EmailRegisterIn, request: Request) -> TokenOut:
    """Crea una organizacion y su primer administrador usando email/password.

    Google es opcional. Esta ruta permite el onboarding local y productivo sin
    depender de un proveedor de identidad externo.
    """
    await enforce_rate_limit(
        request, bucket="auth-register", limit=6, window_seconds=60 * 60
    )
    if not body.terms_accepted:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Debes aceptar los Términos y la Política de Privacidad.",
        )

    p = db.pool()
    email = str(body.email).strip().lower()
    existing = await p.fetchval(
        "SELECT EXISTS(SELECT 1 FROM users WHERE lower(email)=lower($1))", email
    )
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya existe una cuenta con ese email. Ingresá con tu contraseña.",
        )

    slug = await _unique_org_slug(body.organization_name)
    try:
        async with p.acquire() as conn:
            async with conn.transaction():
                org_id = await conn.fetchval(
                    """
                    INSERT INTO organizations (
                        name, slug, vertical, province, department, municipality, territory_scope
                    )
                    VALUES ($1,$2,$3::org_vertical,'Misiones',$4,$5,
                            CASE WHEN NULLIF($5,'') IS NOT NULL THEN 'municipal'
                                 WHEN NULLIF($4,'') IS NOT NULL THEN 'departamental'
                                 ELSE 'provincial' END)
                    RETURNING id
                    """,
                    body.organization_name,
                    slug,
                    body.vertical,
                    body.department,
                    body.municipality,
                )
                row = await conn.fetchrow(
                    """
                    INSERT INTO users (
                        org_id, email, name, role, password_hash,
                        auth_provider, email_verified, terms_accepted_at,
                        legal_version, last_login_at
                    )
                    VALUES (
                        $1,$2,$3,'admin',$4,
                        'password',false,now(),$5,now()
                    )
                    RETURNING id, org_id, role, name, email, avatar_url
                    """,
                    org_id,
                    email,
                    body.name,
                    hash_secret(body.password),
                    body.legal_version,
                )
                await conn.execute(
                    """
                    INSERT INTO audit_events (
                        org_id, user_id, action, resource, resource_id, metadata
                    ) VALUES (
                        $1,$2,'create','organization',$1,
                        jsonb_build_object('source','email_registration','vertical',$3::text)
                    )
                    """,
                    org_id,
                    row["id"],
                    body.vertical,
                )
                await ensure_subscription(org_id, row["id"], plan_key="sandbox", conn=conn)
                await create_notification(
                    org_id=org_id, kind="organization_registered", visibility="both", severity="success",
                    title="Nueva organización registrada",
                    message=f"{body.organization_name} creó su espacio institucional en EcoNexo.",
                    actor_user_id=row["id"], actor_email=email,
                    metadata={**request_context(request), "provider": "password", "plan": "sandbox"},
                    conn=conn,
                )
    except asyncpg.UniqueViolationError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El email o identificador de organización ya está registrado.",
        ) from exc

    await sync_modules(row["org_id"], row["id"])
    return _token(row, provider="password", is_new_user=True)


@router.post("/google", response_model=TokenOut)
async def google_auth(body: GoogleAuthIn, request: Request) -> TokenOut:
    """Inicia sesion o crea una organizacion con un ID token de Google.

    El navegador obtiene la credencial con Google Identity Services. El backend
    vuelve a verificar firma, audience, issuer, expiracion y email verificado.
    """
    await enforce_rate_limit(
        request, bucket="auth-google", limit=20, window_seconds=15 * 60
    )
    try:
        identity = verify_google_credential(body.credential)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Credencial de Google inválida"
        ) from exc

    p = db.pool()
    row = await p.fetchrow(
        """
        SELECT id, org_id, role, name, email, avatar_url
        FROM users
        WHERE (google_sub=$1 OR lower(email)=lower($2)) AND is_active
        ORDER BY (google_sub=$1) DESC
        LIMIT 1
        """,
        identity["sub"], identity["email"],
    )
    if row is not None:
        row = await p.fetchrow(
            """
            UPDATE users
            SET google_sub=$2,
                auth_provider='google',
                email_verified=true,
                avatar_url=NULLIF($3, ''),
                name=COALESCE(NULLIF(name, ''), $4),
                last_login_at=now()
            WHERE id=$1
            RETURNING id, org_id, role, name, email, avatar_url
            """,
            row["id"], identity["sub"], identity["picture"], identity["name"],
        )
        await ensure_subscription(row["org_id"], row["id"])
        await create_notification(
            org_id=row["org_id"], kind="login_success", visibility="both", severity="info",
            title="Nuevo ingreso con Google",
            message=f"{row['name']} ingresó al centro de comando mediante Google.",
            actor_user_id=row["id"], actor_email=row["email"],
            metadata={**request_context(request), "provider": "google"},
        )
        return _token(row, provider="google")

    if body.mode != "register":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No existe una cuenta asociada. Seleccioná 'Crear organización'.",
        )
    if not body.organization_name or not body.vertical:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Nombre y vertical de la organización son obligatorios.",
        )
    if not body.terms_accepted:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Debes aceptar Términos y Política de Privacidad.",
        )

    slug = await _unique_org_slug(body.organization_name)
    async with p.acquire() as conn:
        async with conn.transaction():
            org_id = await conn.fetchval(
                """
                INSERT INTO organizations (
                    name, slug, vertical, province, department, municipality, territory_scope
                )
                VALUES ($1,$2,$3::org_vertical,'Misiones',$4,$5,
                        CASE WHEN NULLIF($5,'') IS NOT NULL THEN 'municipal'
                             WHEN NULLIF($4,'') IS NOT NULL THEN 'departamental'
                             ELSE 'provincial' END)
                RETURNING id
                """,
                body.organization_name.strip(), slug, body.vertical, body.department, body.municipality,
            )
            row = await conn.fetchrow(
                """
                INSERT INTO users (
                    org_id, email, name, role, password_hash, google_sub,
                    auth_provider, email_verified, avatar_url, terms_accepted_at,
                    legal_version, last_login_at
                )
                VALUES (
                    $1,$2,$3,'admin',$4,$5,'google',true,NULLIF($6,''),now(),$7,now()
                )
                RETURNING id, org_id, role, name, email, avatar_url
                """,
                org_id,
                identity["email"],
                identity["name"],
                hash_secret(new_token(32)),
                identity["sub"],
                identity["picture"],
                body.legal_version,
            )
            await conn.execute(
                """
                INSERT INTO audit_events (
                    org_id, user_id, action, resource, resource_id, metadata
                ) VALUES (
                    $1,$2,'create','organization',$1,
                    jsonb_build_object('source','google_registration','vertical',$3::text)
                )
                """,
                org_id,
                row["id"],
                body.vertical,
            )
            await ensure_subscription(org_id, row["id"], plan_key="sandbox", conn=conn)
            await create_notification(
                org_id=org_id, kind="organization_registered", visibility="both", severity="success",
                title="Nueva organización registrada con Google",
                message=f"{body.organization_name} creó su espacio institucional en EcoNexo.",
                actor_user_id=row["id"], actor_email=row["email"],
                metadata={**request_context(request), "provider": "google", "plan": "sandbox"},
                conn=conn,
            )
    await sync_modules(row["org_id"], row["id"])
    return _token(row, provider="google", is_new_user=True)
