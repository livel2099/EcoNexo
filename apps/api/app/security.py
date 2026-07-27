"""Hashing, JWT y verificacion de identidad externa."""
from __future__ import annotations

import hashlib
import hmac
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


def new_token(nbytes: int = 24) -> str:
    """Credencial/token aleatorio de alta entropia."""
    return secrets.token_urlsafe(nbytes)


def create_access_token(subject: str, org_id: str, role: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "org_id": org_id,
        "role": role,
        "kind": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=s.jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        if payload.get("kind") not in {None, "access"}:  # compatibilidad con JWT previos
            return None
        return payload
    except JWTError:
        return None


def create_citizen_token() -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": new_token(18),
        "kind": "citizen",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=s.citizen_token_days)).timestamp()),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_citizen_token(token: str) -> str | None:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        if payload.get("kind") != "citizen" or not payload.get("sub"):
            return None
        return str(payload["sub"])
    except JWTError:
        return None


def verify_google_credential(credential: str) -> dict[str, str]:
    """Verifica un ID token de Google del lado servidor.

    Google recomienda usar ``sub`` como identificador estable, no el email.
    La funcion valida firma, issuer, expiracion y audience mediante google-auth.
    """
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
    except ImportError as exc:
        raise RuntimeError("Falta instalar la dependencia google-auth") from exc

    audiences = get_settings().google_audiences
    if not audiences:
        raise ValueError("Google OAuth no esta configurado")
    # La firma, issuer y expiracion son validados por google-auth. La audience
    # se compara explicitamente para admitir web, Android e iOS sin relajar el
    # control a otros clientes de Google.
    claims = id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        audience=None,
    )
    token_audience = str(claims.get("aud", ""))
    if token_audience not in audiences:
        raise ValueError("Audience de Google no autorizada")
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise ValueError("Issuer de Google invalido")
    if claims.get("email_verified") is not True:
        raise ValueError("El email de Google no esta verificado")
    sub = str(claims.get("sub", ""))
    email = str(claims.get("email", "")).strip().lower()
    if not sub or not email:
        raise ValueError("Token de Google incompleto")
    return {
        "sub": sub,
        "email": email,
        "name": str(claims.get("name") or email.split("@", 1)[0]),
        "picture": str(claims.get("picture") or ""),
    }


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:48] or "organizacion"


def token_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def constant_time_match(value: str, expected: str) -> bool:
    return bool(value and expected and hmac.compare_digest(value, expected))
