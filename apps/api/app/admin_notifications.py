"""Mensajes administrativos generados por acceso, registro y licencias."""
from __future__ import annotations

import ipaddress
import logging
from typing import Any
from uuid import UUID

from fastapi import Request

from . import db

logger = logging.getLogger(__name__)


def _masked_ip(request: Request) -> str:
    raw = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        or (request.client.host if request.client else "")
    )
    if not raw:
        return "no disponible"
    try:
        ip = ipaddress.ip_address(raw)
        if ip.version == 4:
            parts = raw.split(".")
            return ".".join(parts[:3] + ["x"])
        return f"{ip.exploded.split(':')[0]}:{ip.exploded.split(':')[1]}::/32"
    except ValueError:
        return "no disponible"


def request_context(request: Request) -> dict[str, str]:
    return {
        "ip_masked": _masked_ip(request),
        "user_agent": request.headers.get("user-agent", "desconocido")[:240],
        "origin": request.headers.get("origin", "")[:240],
    }


async def create_notification(
    *,
    org_id: UUID,
    kind: str,
    title: str,
    message: str,
    visibility: str = "org_admins",
    severity: str = "info",
    actor_user_id: UUID | None = None,
    actor_email: str | None = None,
    metadata: dict[str, Any] | None = None,
    conn: Any | None = None,
) -> None:
    executor = conn or db.pool()
    try:
        await executor.execute(
            """
            INSERT INTO admin_notifications
              (org_id, kind, visibility, severity, title, message,
               actor_user_id, actor_email, metadata)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
            """,
            org_id,
            kind,
            visibility,
            severity,
            title,
            message,
            actor_user_id,
            actor_email,
            __import__("json").dumps(metadata or {}, ensure_ascii=False, default=str),
        )
    except Exception:
        # Las notificaciones no deben impedir el acceso si una migración aún no fue aplicada.
        logger.exception("No se pudo registrar la notificación administrativa")
