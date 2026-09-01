"""Hashing (argon2id) y JWT."""
from __future__ import annotations

import hashlib
import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from .config import get_settings

_ph = PasswordHasher()


def hash_secret(raw: str) -> str:
    return _ph.hash(raw)


def verify_secret(raw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, raw)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# Hash de una contraseña que nadie conoce, con los mismos parametros de argon2
# que los reales. Se calcula una sola vez al importar el modulo.
_DECOY_HASH = _ph.hash(secrets.token_urlsafe(32))


def burn_verification_time() -> None:
    """Consume el mismo tiempo que verificar una contraseña real.

    ``/auth/login`` cortaba antes de argon2 cuando el correo no existia, asi
    que la respuesta volvia en milisegundos en vez de decenas de milisegundos.
    Esa diferencia es un oraculo: permite enumerar que correos estan
    registrados sin acertar ninguna contraseña.
    """
    verify_secret("no-importa", _DECOY_HASH)


def new_token(nbytes: int = 24) -> str:
    """Credencial/token aleatorio (p.ej. password MQTT, mostrado una sola vez)."""
    return secrets.token_urlsafe(nbytes)


def create_access_token(
    subject: str, org_id: str, role: str, *, account_type: str = "institutional",
    email: str = "", platform_admin: bool = False,
) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "org_id": org_id,
        "role": role,
        "account_type": account_type,
        "email": email,
        "platform_admin": platform_admin,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=s.jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError:
        return None

def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_citizen_token() -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": secrets.token_urlsafe(24),
        "typ": "citizen",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=365)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_citizen_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("typ") != "citizen":
        return None
    subject = payload.get("sub")
    return str(subject) if subject else None