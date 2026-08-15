"""Gestion de dispositivos (red de hardware)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..deps import CurrentUser, current_user, require_role
from ..schemas import DeviceCreatedOut, DeviceIn, DeviceOut, DeviceTypeIn
from ..security import hash_secret, new_token

router = APIRouter(prefix="/devices", tags=["devices"])

_DEVICE_COLS = (
    "id, name, external_id, ST_Y(location::geometry) AS lat, "
    "ST_X(location::geometry) AS lon, status, battery, rssi, tags, last_seen"
)


@router.get("", response_model=list[DeviceOut])
async def list_devices(user: CurrentUser = Depends(current_user)) -> list[DeviceOut]:
    rows = await db.pool().fetch(
        f"SELECT {_DEVICE_COLS} FROM devices WHERE org_id=$1 ORDER BY name", user.org_id
    )
    return [DeviceOut(**dict(r)) for r in rows]


@router.post("", response_model=DeviceCreatedOut, status_code=201)
async def create_device(
    body: DeviceIn, user: CurrentUser = Depends(require_role("admin", "operador"))
) -> DeviceCreatedOut:
    mqtt_user = f"dev-{body.external_id}"
    mqtt_pass = new_token()  # se muestra una sola vez
    row = await db.pool().fetchrow(
        f"""
        INSERT INTO devices
            (org_id, device_type_id, name, external_id, location, tags,
             mqtt_username, mqtt_password_hash, status)
        VALUES ($1,$2,$3,$4, ST_MakePoint($6,$5)::geography, $7, $8, $9, 'offline')
        RETURNING {_DEVICE_COLS}, mqtt_username
        """,
        user.org_id, body.device_type_id, body.name, body.external_id,
        body.lat, body.lon, body.tags, mqtt_user, hash_secret(mqtt_pass),
    )
    return DeviceCreatedOut(**dict(row), mqtt_password=mqtt_pass)


@router.get("/{device_id}/readings")
async def device_readings(
    device_id: UUID, variable: str, hours: int = 24,
    user: CurrentUser = Depends(current_user),
) -> list[dict]:
    rows = await db.pool().fetch(
        """
        SELECT ts, value FROM readings
        WHERE device_id=$1 AND org_id=$2 AND variable=$3
          AND ts > now() - ($4 || ' hours')::interval
        ORDER BY ts
        """,
        device_id, user.org_id, variable, str(hours),
    )
    return [{"ts": str(r["ts"]), "value": r["value"]} for r in rows]


@router.post("/types", status_code=201)
async def create_device_type(
    body: DeviceTypeIn, user: CurrentUser = Depends(require_role("admin", "operador"))
) -> dict:
    import json
    row = await db.pool().fetchrow(
        "INSERT INTO device_types (org_id, name, variables) VALUES ($1,$2,$3::jsonb) RETURNING id",
        user.org_id, body.name, json.dumps(body.variables),
    )
    return {"id": str(row["id"])}
