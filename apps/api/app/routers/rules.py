"""Motor de reglas — CRUD sin tocar codigo."""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..deps import CurrentUser, current_user, require_role
from ..schemas import RuleIn, RuleOut

router = APIRouter(prefix="/rules", tags=["rules"])


def _to_out(r) -> RuleOut:
    return RuleOut(
        id=r["id"], name=r["name"], alert_type=r["alert_type"],
        conditions=json.loads(r["conditions"]), condition_logic=r["condition_logic"],
        window_seconds=r["window_seconds"], zone_id=r["zone_id"],
        device_tags=list(r["device_tags"]), severity=r["severity"],
        require_satellite=r["require_satellite"], actions=json.loads(r["actions"]),
        enabled=r["enabled"],
    )


@router.get("", response_model=list[RuleOut])
async def list_rules(user: CurrentUser = Depends(current_user)) -> list[RuleOut]:
    rows = await db.pool().fetch(
        "SELECT * FROM rules WHERE org_id=$1 ORDER BY created_at DESC", user.org_id
    )
    return [_to_out(r) for r in rows]


@router.post("", response_model=RuleOut, status_code=201)
async def create_rule(
    body: RuleIn, user: CurrentUser = Depends(require_role("admin", "operador"))
) -> RuleOut:
    row = await db.pool().fetchrow(
        """
        INSERT INTO rules (org_id, name, alert_type, conditions, condition_logic,
            window_seconds, zone_id, device_tags, severity, require_satellite, actions, enabled)
        VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7,$8,$9,$10,$11::jsonb,$12)
        RETURNING *
        """,
        user.org_id, body.name, body.alert_type,
        json.dumps([c.model_dump() for c in body.conditions]), body.condition_logic,
        body.window_seconds, body.zone_id, body.device_tags, body.severity,
        body.require_satellite, json.dumps(body.actions), body.enabled,
    )
    return _to_out(row)


@router.patch("/{rule_id}/toggle", response_model=RuleOut)
async def toggle_rule(
    rule_id: UUID, user: CurrentUser = Depends(require_role("admin", "operador"))
) -> RuleOut:
    row = await db.pool().fetchrow(
        "UPDATE rules SET enabled = NOT enabled WHERE id=$1 AND org_id=$2 RETURNING *",
        rule_id, user.org_id,
    )
    if row is None:
        raise HTTPException(404, "Regla no encontrada")
    return _to_out(row)


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: UUID, user: CurrentUser = Depends(require_role("admin"))
) -> dict:
    await db.pool().execute("DELETE FROM rules WHERE id=$1 AND org_id=$2", rule_id, user.org_id)
    return {"deleted": True}
