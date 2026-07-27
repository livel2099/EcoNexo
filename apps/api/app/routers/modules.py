"""Licencias modulares y trazabilidad de comunicaciones de Alerta IA."""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from .. import db
from ..audit import record_audit
from ..deps import CurrentUser, current_user, require_role
from ..schemas import AlertShareIn, AlertShareOut, ModuleEntitlementOut
from ..subscriptions import ensure_subscription, require_active_subscription, sync_modules

router = APIRouter(prefix="/modules", tags=["modules"])

_DEFAULT_CONFIG = {
    "core": {"plain_language": False, "human_approval_required": True},
    "fire_smoke": {
        "plain_language": True,
        "human_approval_required": True,
        "emergency_numbers": ["911", "100", "103", "105"],
    },
    "forestry_pests": {
        "plain_language": True,
        "human_approval_required": True,
        "focus_area": "San Antonio - General Manuel Belgrano",
        "priority_pests": ["Sirex noctilio", "escolitidos", "anomalias sanitarias en Pinus y Eucalyptus"],
    },
}


def _json(value):
    return json.loads(value) if isinstance(value, str) else (value or {})


async def _ensure_defaults(org_id: UUID, user_id: UUID | None = None) -> None:
    await ensure_subscription(org_id, user_id)
    p = db.pool()
    await p.execute(
        """
        INSERT INTO organization_modules
            (org_id, module_key, status, plan_name, expires_at, config, created_by)
        VALUES
            ($1,'core','active','Plataforma EcoNexo',NULL,$2::jsonb,$5),
            ($1,'fire_smoke','suspended','Focos de incendio forestal y humo',NULL,$3::jsonb,$5),
            ($1,'forestry_pests','suspended','Vigilancia de plagas forestales',NULL,$4::jsonb,$5)
        ON CONFLICT (org_id, module_key) DO UPDATE SET
          config=CASE WHEN organization_modules.config='{}'::jsonb THEN EXCLUDED.config ELSE organization_modules.config END,
          updated_at=now()
        """,
        org_id,
        json.dumps(_DEFAULT_CONFIG["core"], ensure_ascii=False),
        json.dumps(_DEFAULT_CONFIG["fire_smoke"], ensure_ascii=False),
        json.dumps(_DEFAULT_CONFIG["forestry_pests"], ensure_ascii=False),
        user_id,
    )
    await sync_modules(org_id, user_id)


def _out(row) -> ModuleEntitlementOut:
    data = dict(row)
    data["config"] = _json(data.get("config"))
    now_available = bool(data.get("subscription_available", True)) and data["status"] in {"active", "trial"} and (
        data.get("expires_at") is None or data["expires_at"] > data["database_now"]
    )
    data["available"] = now_available
    data.pop("database_now", None)
    data.pop("subscription_available", None)
    return ModuleEntitlementOut(**data)


@router.get("/me", response_model=list[ModuleEntitlementOut])
async def my_modules(user: CurrentUser = Depends(current_user)) -> list[ModuleEntitlementOut]:
    await _ensure_defaults(user.org_id, user.id)
    rows = await db.pool().fetch(
        """
        SELECT om.module_key, om.status, om.plan_name, om.starts_at, om.expires_at,
               om.config, now() AS database_now,
               (os.status IN ('active','trial') AND (os.expires_at IS NULL OR os.expires_at > now())) AS subscription_available
        FROM organization_modules om
        JOIN organization_subscriptions os ON os.org_id=om.org_id
        WHERE om.org_id=$1
        ORDER BY CASE module_key WHEN 'core' THEN 0 ELSE 1 END, module_key
        """,
        user.org_id,
    )
    return [_out(row) for row in rows]


@router.post("/alert-share", response_model=AlertShareOut, status_code=201)
async def create_alert_share(
    body: AlertShareIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> AlertShareOut:
    await require_active_subscription(user.org_id)
    await _ensure_defaults(user.org_id, user.id)
    entitlement = await db.pool().fetchrow(
        """
        SELECT status, expires_at
        FROM organization_modules
        WHERE org_id=$1 AND module_key=$2
        """,
        user.org_id,
        body.module_key,
    )
    if entitlement is None:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Modulo no habilitado")
    if entitlement["status"] not in {"active", "trial"}:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "La licencia del modulo no esta activa")
    if entitlement["expires_at"] is not None:
        expired = await db.pool().fetchval("SELECT $1::timestamptz <= now()", entitlement["expires_at"])
        if expired:
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "La licencia del modulo esta vencida")

    # Las referencias opcionales deben pertenecer a la misma organizacion.
    if body.snapshot_id is not None and not await db.pool().fetchval(
        "SELECT EXISTS(SELECT 1 FROM environmental_snapshots WHERE id=$1 AND org_id=$2)",
        body.snapshot_id,
        user.org_id,
    ):
        raise HTTPException(404, "Snapshot no encontrado")
    if body.alert_id is not None and not await db.pool().fetchval(
        "SELECT EXISTS(SELECT 1 FROM alerts WHERE id=$1 AND org_id=$2)",
        body.alert_id,
        user.org_id,
    ):
        raise HTTPException(404, "Alerta no encontrada")

    row = await db.pool().fetchrow(
        """
        INSERT INTO alert_shares
            (org_id, user_id, channel, audience, title, message, module_key,
             snapshot_id, alert_id, metadata)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
        RETURNING id, created_at
        """,
        user.org_id,
        user.id,
        body.channel,
        body.audience,
        body.title.strip(),
        body.message.strip(),
        body.module_key,
        body.snapshot_id,
        body.alert_id,
        json.dumps(body.metadata, ensure_ascii=False, default=str),
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="alerta_ia_compartida",
        resource="alert_share",
        resource_id=row["id"],
        metadata={
            "channel": body.channel,
            "audience": body.audience,
            "module_key": body.module_key,
            "snapshot_id": str(body.snapshot_id) if body.snapshot_id else None,
            "alert_id": str(body.alert_id) if body.alert_id else None,
        },
    )
    return AlertShareOut(**dict(row))
