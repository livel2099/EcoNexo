"""Autenticacion (login por email + password, JWT)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .. import db
from ..schemas import LoginIn, TokenOut
from ..security import create_access_token, verify_secret

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn) -> TokenOut:
    row = await db.pool().fetchrow(
        "SELECT id, org_id, role, name, password_hash FROM users WHERE email=$1",
        body.email,
    )
    if row is None or not verify_secret(body.password, row["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales invalidas")
    token = create_access_token(str(row["id"]), str(row["org_id"]), row["role"])
    return TokenOut(
        access_token=token, org_id=row["org_id"], role=row["role"], name=row["name"]
    )
