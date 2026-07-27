"""Registro centralizado de auditoria por organizacion."""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from . import db


async def record_audit(
    *,
    org_id: UUID,
    user_id: UUID | None,
    action: str,
    resource: str,
    resource_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persiste una accion sensible sin interrumpir silenciosamente el flujo.

    El esquema usa JSONB para conservar contexto estructurado. Las credenciales,
    tokens y secretos no deben incluirse en ``metadata``.
    """
    await db.pool().execute(
        """
        INSERT INTO audit_events (org_id, user_id, action, resource, resource_id, metadata)
        VALUES ($1,$2,$3,$4,$5,$6::jsonb)
        """,
        org_id,
        user_id,
        action[:120],
        resource[:120],
        resource_id,
        json.dumps(metadata or {}, ensure_ascii=False, default=str),
    )
