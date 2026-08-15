"""Alertas — panel priorizado y acciones del operador."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..deps import CurrentUser, current_user, require_role
from ..schemas import AlertActionIn, AlertOut, AlertSourceOut

router = APIRouter(prefix="/alerts", tags=["alerts"])

# Orden de prioridad: severidad x recencia.
_SEVERITY_RANK = "CASE severity WHEN 'critica' THEN 4 WHEN 'alta' THEN 3 WHEN 'media' THEN 2 ELSE 1 END"


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    status: str | None = None, user: CurrentUser = Depends(current_user)
) -> list[AlertOut]:
    rows = await db.pool().fetch(
        f"""
        SELECT id, type, severity, status, ST_Y(location::geometry) AS lat,
               ST_X(location::geometry) AS lon, confidence, title,
               detected_at, acknowledged_at, resolved_at
        FROM alerts
        WHERE org_id=$1 AND ($2::text IS NULL OR status = $2::alert_status)
        ORDER BY {_SEVERITY_RANK} DESC, detected_at DESC
        """,
        user.org_id, status,
    )
    out: list[AlertOut] = []
    for r in rows:
        srcs = await db.pool().fetch(
            "SELECT source_type, ref_id, weight, detail FROM alert_sources WHERE alert_id=$1",
            r["id"],
        )
        out.append(AlertOut(
            **dict(r),
            sources=[AlertSourceOut(
                source_type=s["source_type"], ref_id=s["ref_id"],
                weight=float(s["weight"]),
                detail=__import__("json").loads(s["detail"]) if s["detail"] else None,
            ) for s in srcs],
        ))
    return out


@router.post("/{alert_id}/action", response_model=AlertOut)
async def act_on_alert(
    alert_id: UUID, body: AlertActionIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> AlertOut:
    status_map = {
        "confirmar": "confirmada", "descartar": "descartada",
        "escalar": "escalada", "asignar": "asignada",
    }
    new_status = status_map[body.action]
    row = await db.pool().fetchrow(
        """
        UPDATE alerts
        SET status=$3::alert_status,
            assigned_to = COALESCE($4, assigned_to),
            acknowledged_at = COALESCE(acknowledged_at, now()),
            resolved_at = CASE WHEN $3 IN ('confirmada','descartada') THEN now() ELSE resolved_at END
        WHERE id=$1 AND org_id=$2
        RETURNING id, type, severity, status, ST_Y(location::geometry) AS lat,
                  ST_X(location::geometry) AS lon, confidence, title,
                  detected_at, acknowledged_at, resolved_at
        """,
        alert_id, user.org_id, new_status, body.assigned_to,
    )
    if row is None:
        raise HTTPException(404, "Alerta no encontrada")
    await db.pool().execute(
        "INSERT INTO alert_events (alert_id, user_id, action) VALUES ($1,$2,$3)",
        alert_id, user.id, body.action,
    )
    return AlertOut(**dict(row), sources=[])
