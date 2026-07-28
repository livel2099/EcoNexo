"""Bandeja de mensajes para administradores de organización y plataforma."""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from .. import db
from ..deps import CurrentUser, require_role
from ..schemas import AdminNotificationOut

router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


def _out(row) -> AdminNotificationOut:
    data = dict(row)
    metadata = data.get("metadata")
    if isinstance(metadata, str):
        data["metadata"] = json.loads(metadata)
    data["read"] = bool(data.get("read_at"))
    data.pop("read_at", None)
    return AdminNotificationOut(**data)


@router.get("", response_model=list[AdminNotificationOut])
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=300),
    user: CurrentUser = Depends(require_role("admin")),
) -> list[AdminNotificationOut]:
    rows = await db.pool().fetch(
        """
        SELECT n.id, n.org_id, o.name AS org_name, n.kind, n.visibility,
               n.severity, n.title, n.message, n.actor_user_id, n.actor_email,
               n.metadata, n.created_at, r.read_at
        FROM admin_notifications n
        JOIN organizations o ON o.id=n.org_id
        LEFT JOIN admin_notification_reads r
          ON r.notification_id=n.id AND r.user_id=$1
        WHERE (
          (n.org_id=$2 AND n.visibility IN ('org_admins','both'))
          OR ($3::boolean AND n.visibility IN ('platform_admins','both'))
        )
        AND (NOT $4::boolean OR r.read_at IS NULL)
        ORDER BY n.created_at DESC
        LIMIT $5
        """,
        user.id,
        user.org_id,
        user.platform_admin,
        unread_only,
        limit,
    )
    return [_out(row) for row in rows]


@router.get("/unread-count")
async def unread_count(user: CurrentUser = Depends(require_role("admin"))) -> dict[str, int]:
    value = await db.pool().fetchval(
        """
        SELECT count(*)
        FROM admin_notifications n
        LEFT JOIN admin_notification_reads r
          ON r.notification_id=n.id AND r.user_id=$1
        WHERE r.read_at IS NULL AND (
          (n.org_id=$2 AND n.visibility IN ('org_admins','both'))
          OR ($3::boolean AND n.visibility IN ('platform_admins','both'))
        )
        """,
        user.id,
        user.org_id,
        user.platform_admin,
    )
    return {"unread": int(value or 0)}


@router.post(
    "/{notification_id}/read",
    status_code=204,
    response_class=Response,
)
async def mark_read(
    notification_id: UUID,
    user: CurrentUser = Depends(require_role("admin")),
) -> Response:
    allowed = await db.pool().fetchval(
        """
        SELECT EXISTS(
          SELECT 1 FROM admin_notifications n WHERE n.id=$1 AND (
            (n.org_id=$2 AND n.visibility IN ('org_admins','both'))
            OR ($3::boolean AND n.visibility IN ('platform_admins','both'))
          )
        )
        """,
        notification_id,
        user.org_id,
        user.platform_admin,
    )
    if not allowed:
        raise HTTPException(404, "Mensaje no encontrado")
    await db.pool().execute(
        """
        INSERT INTO admin_notification_reads (notification_id,user_id)
        VALUES ($1,$2) ON CONFLICT (notification_id,user_id) DO NOTHING
        """,
        notification_id,
        user.id,
    )
    return Response(status_code=204)


@router.post(
    "/read-all",
    status_code=204,
    response_class=Response,
)
async def mark_all_read(
    user: CurrentUser = Depends(require_role("admin")),
) -> Response:
    await db.pool().execute(
        """
        INSERT INTO admin_notification_reads (notification_id,user_id)
        SELECT n.id,$1 FROM admin_notifications n
        WHERE (n.org_id=$2 AND n.visibility IN ('org_admins','both'))
           OR ($3::boolean AND n.visibility IN ('platform_admins','both'))
        ON CONFLICT (notification_id,user_id) DO NOTHING
        """,
        user.id,
        user.org_id,
        user.platform_admin,
    )
    return Response(status_code=204)
