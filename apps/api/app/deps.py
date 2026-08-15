"""Dependencias de auth y scoping por organizacion."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from .security import decode_token


@dataclass
class CurrentUser:
    id: UUID
    org_id: UUID
    role: str


async def current_user(authorization: str = Header(default="")) -> CurrentUser:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta token Bearer")
    payload = decode_token(authorization.split(" ", 1)[1])
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido o expirado")
    return CurrentUser(
        id=UUID(payload["sub"]),
        org_id=UUID(payload["org_id"]),
        role=payload["role"],
    )


def require_role(*roles: str):
    async def _guard(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permisos insuficientes")
        return user

    return _guard
