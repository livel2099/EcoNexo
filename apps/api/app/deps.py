"""Dependencias de auth y scoping por organizacion."""
from __future__ import annotations

from dataclasses import dataclass
from hmac import compare_digest
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status

from . import db
from .config import get_settings
from .security import decode_token


@dataclass
class CurrentUser:
    id: UUID
    org_id: UUID
    role: str
    email: str = ""
    account_type: str = "institutional"
    platform_admin: bool = False


async def current_user(authorization: str = Header(default=""), request: Request = None) -> CurrentUser:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta token Bearer")
    payload = decode_token(authorization.split(" ", 1)[1])
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido o expirado")
    # Un token ciudadano esta firmado con la misma clave pero no trae org_id ni
    # un sub UUID: sin esta guarda el endpoint respondia 500 en vez de 401.
    try:
        user_id = UUID(str(payload["sub"]))
        org_id = UUID(str(payload["org_id"]))
        role = str(payload["role"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Token invalido para esta operacion"
        ) from exc
    row = await db.pool().fetchrow(
        """
        SELECT u.org_id, u.role::text AS role, u.email, u.account_type,
               u.is_active, u.must_change_password, u.token_version,
               o.is_active AS organization_active, o.access_status
        FROM users u JOIN organizations o ON o.id=u.org_id WHERE u.id=$1
        """, user_id,
    )
    if row is None or row["org_id"] != org_id or not row["is_active"]:
        raise HTTPException(401, "La cuenta ya no está habilitada")
    if not row["organization_active"] or row["access_status"] != "approved":
        raise HTTPException(403, "La organización no tiene el acceso habilitado")
    if payload.get("token_version", 0) != row["token_version"]:
        raise HTTPException(401, "Los datos de acceso cambiaron. Iniciá sesión nuevamente")
    path = request.url.path if request is not None else ""
    if row["must_change_password"] and path not in {"/auth/change-password", "/auth/me"}:
        raise HTTPException(403, "Debés cambiar la contraseña temporal antes de continuar")
    email = str(row["email"]).lower()
    platform_admin = row["role"] == "admin" and email in get_settings().platform_admin_list
    # La administración y renovación siguen accesibles tras dar de baja la licencia.
    management = path.startswith(("/auth/", "/admin/", "/subscriptions/", "/platform/")) or path in {
        "/orgs/me", "/zones", "/modules/me", "/territory/boundary-status", "/environment/source-settings",
    }
    if request is not None and row["account_type"] != "community" and not platform_admin and not management:
        from .subscriptions import is_active
        license_row = await db.pool().fetchrow(
            "SELECT status, expires_at, now() AS database_now FROM organization_subscriptions WHERE org_id=$1", org_id,
        )
        if license_row is None or not is_active(license_row):
            raise HTTPException(402, "La licencia no está activa. Revisá Admin Core → Suscripción")
    return CurrentUser(
        id=user_id,
        org_id=org_id,
        role=row["role"],
        email=email,
        account_type=row["account_type"],
        platform_admin=platform_admin,
    )


async def require_internal_service(
    x_internal_service_token: str = Header(default=""),
) -> None:
    """Autoriza publicadores internos sin exponer la ingesta al público."""
    expected = get_settings().internal_service_token.strip()
    if not expected or not compare_digest(x_internal_service_token, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credencial de servicio interno inválida")


def require_role(*roles: str):
    async def _guard(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permisos insuficientes")
        return user

    return _guard


def require_platform_admin(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if not user.platform_admin or user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso reservado al administrador general")
    return user
