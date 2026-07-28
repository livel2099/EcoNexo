"""Dependencias de autenticacion, roles y trafico interno."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status

from . import db
from .config import get_settings
from .security import constant_time_match, decode_token


@dataclass
class CurrentUser:
    id: UUID
    org_id: UUID
    role: str
    email: str = ""
    platform_admin: bool = False
    must_change_password: bool = False


async def current_user(
    request: Request,
    authorization: str = Header(default=""),
) -> CurrentUser:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta token Bearer")
    payload = decode_token(authorization.split(" ", 1)[1])
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido o expirado")
    user_id = UUID(payload["sub"])
    org_id = UUID(payload["org_id"])
    row = await db.pool().fetchrow(
        """
        SELECT u.email, u.role, u.is_active, u.must_change_password,
               o.is_active AS organization_active
        FROM users u
        JOIN organizations o ON o.id=u.org_id
        WHERE u.id=$1 AND u.org_id=$2
        """,
        user_id,
        org_id,
    )
    if row is None or not row["is_active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "La cuenta no esta activa")
    if not row["organization_active"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La organización está suspendida")

    email = str(row["email"]).lower()
    user = CurrentUser(
        id=user_id,
        org_id=org_id,
        role=str(row["role"]),
        email=email,
        platform_admin=email in get_settings().platform_admin_list,
        must_change_password=bool(row["must_change_password"]),
    )
    if user.must_change_password and request.url.path not in {
        "/auth/change-password",
        "/auth/me",
    }:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Debes cambiar la contraseña temporal antes de continuar",
        )
    return user


def require_role(*roles: str):
    async def _guard(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permisos insuficientes")
        return user

    return _guard


async def require_platform_admin(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if not user.platform_admin or user.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Se requiere administrador general de EcoNexo",
        )
    return user


async def internal_service(x_service_token: str = Header(default="")) -> None:
    expected = get_settings().internal_service_token
    if not constant_time_match(x_service_token, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credencial interna invalida")
