"""ABM de zonas de riesgo circulares para geofencing de reglas."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from .. import db
from ..audit import record_audit
from ..deps import CurrentUser, current_user, require_role
from ..schemas import RiskZoneIn, RiskZoneOut
from ..subscriptions import enforce_resource_limit

router = APIRouter(prefix="/zones", tags=["zones"])

_ZONE_SELECT = """
SELECT id, name, kind,
       COALESCE(ST_Y(center::geometry), ST_Y(ST_Centroid(area::geometry))) AS lat,
       COALESCE(ST_X(center::geometry), ST_X(ST_Centroid(area::geometry))) AS lon,
       COALESCE(radius_m, sqrt(GREATEST(ST_Area(area), 1) / pi())) AS radius_m,
       created_at, updated_at
FROM risk_zones
"""


def _zone_out(row) -> RiskZoneOut:
    return RiskZoneOut(**dict(row))


@router.get("", response_model=list[RiskZoneOut])
async def list_zones(user: CurrentUser = Depends(current_user)) -> list[RiskZoneOut]:
    rows = await db.pool().fetch(
        _ZONE_SELECT + " WHERE org_id=$1 AND econexo_inside_misiones(center) ORDER BY name",
        user.org_id,
    )
    return [_zone_out(row) for row in rows]


@router.post("", response_model=RiskZoneOut, status_code=201)
async def create_zone(
    body: RiskZoneIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> RiskZoneOut:
    await enforce_resource_limit(user.org_id, "max_zones")
    row = await db.pool().fetchrow(
        """
        INSERT INTO risk_zones (org_id, name, kind, center, radius_m, area)
        VALUES (
          $1,$2,$3::zone_kind,
          ST_MakePoint($5,$4)::geography,$6,
          ST_Buffer(ST_MakePoint($5,$4)::geography,$6)
        )
        RETURNING id
        """,
        user.org_id,
        body.name.strip(),
        body.kind,
        body.lat,
        body.lon,
        body.radius_m,
    )
    created = await db.pool().fetchrow(_ZONE_SELECT + " WHERE id=$1 AND org_id=$2", row["id"], user.org_id)
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="create",
        resource="risk_zone",
        resource_id=row["id"],
        metadata={"name": body.name, "kind": body.kind, "radius_m": body.radius_m},
    )
    return _zone_out(created)


@router.patch("/{zone_id}", response_model=RiskZoneOut)
async def update_zone(
    zone_id: UUID,
    body: RiskZoneIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> RiskZoneOut:
    row = await db.pool().fetchrow(
        """
        UPDATE risk_zones SET
          name=$3,
          kind=$4::zone_kind,
          center=ST_MakePoint($6,$5)::geography,
          radius_m=$7,
          area=ST_Buffer(ST_MakePoint($6,$5)::geography,$7)
        WHERE id=$1 AND org_id=$2
        RETURNING id
        """,
        zone_id,
        user.org_id,
        body.name.strip(),
        body.kind,
        body.lat,
        body.lon,
        body.radius_m,
    )
    if row is None:
        raise HTTPException(404, "Zona no encontrada")
    updated = await db.pool().fetchrow(_ZONE_SELECT + " WHERE id=$1 AND org_id=$2", zone_id, user.org_id)
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="update",
        resource="risk_zone",
        resource_id=zone_id,
        metadata=body.model_dump(mode="json"),
    )
    return _zone_out(updated)


@router.delete("/{zone_id}", status_code=204)
async def delete_zone(
    zone_id: UUID,
    user: CurrentUser = Depends(require_role("admin")),
) -> Response:
    result = await db.pool().execute(
        "DELETE FROM risk_zones WHERE id=$1 AND org_id=$2",
        zone_id,
        user.org_id,
    )
    if result.endswith("0"):
        raise HTTPException(404, "Zona no encontrada")
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="delete",
        resource="risk_zone",
        resource_id=zone_id,
    )
    return Response(status_code=204)
