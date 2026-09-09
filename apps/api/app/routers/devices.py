"""Gestión de nodos físicos y virtuales, aislados por organización."""
from __future__ import annotations

import json
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from .. import db
from ..audit import record_audit
from ..deps import CurrentUser, current_user, require_role
from ..schemas import DeviceCreatedOut, DeviceIn, DeviceOut, DeviceTypeIn, DeviceUpdateIn
from ..security import hash_secret, new_token
from ..subscriptions import enforce_resource_limit

router = APIRouter(prefix="/devices", tags=["devices"])

_DEVICE_SELECT = """
SELECT d.id, d.name, d.external_id, ST_Y(d.location::geometry) AS lat,
       ST_X(d.location::geometry) AS lon, d.status, d.battery, d.rssi,
       d.tags, d.last_seen, d.marker_shape, d.telemetry_mode, d.zone_id,
       z.name AS zone_name, d.pipeline_enabled, d.telemetry_config,
       d.last_pipeline_at, d.last_pipeline_status,
       COALESCE((
         SELECT jsonb_object_agg(latest.variable, latest.value)
         FROM (
           SELECT DISTINCT ON (r.variable) r.variable, r.value
           FROM readings r WHERE r.device_id=d.id AND r.org_id=d.org_id
           ORDER BY r.variable, r.ts DESC, r.id DESC
         ) latest
       ), '{}'::jsonb) AS latest_readings
FROM devices d
LEFT JOIN risk_zones z ON z.id=d.zone_id AND z.org_id=d.org_id
"""


def _device_out(row) -> DeviceOut:
    data = dict(row)
    for key in ("telemetry_config", "latest_readings"):
        value = data.get(key)
        data[key] = json.loads(value) if isinstance(value, str) else value or {}
    return DeviceOut(**data)


async def _validate_references(org_id: UUID, *, zone_id: UUID | None = None,
                               device_type_id: UUID | None = None) -> None:
    if zone_id is not None and not await db.pool().fetchval(
        "SELECT EXISTS(SELECT 1 FROM risk_zones WHERE id=$1 AND org_id=$2)", zone_id, org_id,
    ):
        raise HTTPException(404, "Zona no encontrada en tu organización")
    if device_type_id is not None and not await db.pool().fetchval(
        "SELECT EXISTS(SELECT 1 FROM device_types WHERE id=$1 AND org_id=$2)", device_type_id, org_id,
    ):
        raise HTTPException(404, "Tipo de dispositivo no encontrado en tu organización")


@router.get("", response_model=list[DeviceOut])
async def list_devices(user: CurrentUser = Depends(current_user)) -> list[DeviceOut]:
    rows = await db.pool().fetch(_DEVICE_SELECT + " WHERE d.org_id=$1 ORDER BY d.name", user.org_id)
    return [_device_out(row) for row in rows]


@router.post("", response_model=DeviceCreatedOut, status_code=201)
async def create_device(
    body: DeviceIn, user: CurrentUser = Depends(require_role("admin", "operador")),
) -> DeviceCreatedOut:
    await _validate_references(user.org_id, zone_id=body.zone_id, device_type_id=body.device_type_id)
    await enforce_resource_limit(user.org_id, "max_devices")
    mqtt_user = f"dev-{body.external_id}"
    mqtt_pass = new_token()
    # Argon2 es costoso: no bloquear el loop de la API durante el alta.
    password_hash = await run_in_threadpool(hash_secret, mqtt_pass)
    try:
        device_id = await db.pool().fetchval(
            """
            INSERT INTO devices
              (org_id, device_type_id, name, external_id, location, tags,
               mqtt_username, mqtt_password_hash, status, marker_shape,
               telemetry_mode, zone_id, pipeline_enabled, telemetry_config)
            VALUES ($1,$2,$3,$4,ST_MakePoint($6,$5)::geography,$7,$8,$9,'offline',
                    $10,$11,$12,$13,$14::jsonb)
            RETURNING id
            """,
            user.org_id, body.device_type_id, body.name.strip(), body.external_id,
            body.lat, body.lon, body.tags, mqtt_user, password_hash,
            body.marker_shape, body.telemetry_mode, body.zone_id,
            body.pipeline_enabled, json.dumps(body.telemetry_config),
        )
    except asyncpg.UniqueViolationError as exc:
        raise HTTPException(409, "Ya existe un nodo con ese identificador externo") from exc
    row = await db.pool().fetchrow(_DEVICE_SELECT + " WHERE d.id=$1 AND d.org_id=$2", device_id, user.org_id)
    return DeviceCreatedOut(**_device_out(row).model_dump(), mqtt_username=mqtt_user, mqtt_password=mqtt_pass)


@router.patch("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: UUID, body: DeviceUpdateIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> DeviceOut:
    existing = await db.pool().fetchrow(_DEVICE_SELECT + " WHERE d.id=$1 AND d.org_id=$2", device_id, user.org_id)
    if existing is None:
        raise HTTPException(404, "Nodo no encontrado")
    changes = body.model_dump(exclude_unset=True)
    if any(value is None for key, value in changes.items() if key != "zone_id"):
        raise HTTPException(422, "Solo la zona puede quedar vacía")
    await _validate_references(user.org_id, zone_id=body.zone_id)
    assignments = []
    args = [device_id, user.org_id]
    # Los nombres provienen exclusivamente del esquema validado, nunca del SQL del cliente.
    for key, value in changes.items():
        if key in {"lat", "lon"}:
            continue
        args.append(json.dumps(value) if key == "telemetry_config" else value)
        cast = "::jsonb" if key == "telemetry_config" else ""
        assignments.append(f"{key}=${len(args)}{cast}")
    if body.lat is not None:
        args.extend([body.lon, body.lat])
        assignments.append(f"location=ST_MakePoint(${len(args)-1},${len(args)})::geography")
    if assignments:
        await db.pool().execute(
            "UPDATE devices SET " + ", ".join(assignments) + ", updated_at=now() WHERE id=$1 AND org_id=$2", *args,
        )
        await record_audit(org_id=user.org_id, user_id=user.id, action="update",
                           resource="device", resource_id=device_id, metadata=body.model_dump(mode="json", exclude_unset=True))
    row = await db.pool().fetchrow(_DEVICE_SELECT + " WHERE d.id=$1 AND d.org_id=$2", device_id, user.org_id)
    return _device_out(row)


@router.get("/{device_id}/readings")
async def device_readings(
    device_id: UUID, variable: str, hours: int = 24,
    user: CurrentUser = Depends(current_user),
) -> list[dict]:
    rows = await db.pool().fetch(
        """
        SELECT ts, value FROM readings
        WHERE device_id=$1 AND org_id=$2 AND variable=$3
          AND ts > now() - ($4 || ' hours')::interval ORDER BY ts
        """, device_id, user.org_id, variable, str(hours),
    )
    return [{"ts": str(r["ts"]), "value": r["value"]} for r in rows]


@router.post("/types", status_code=201)
async def create_device_type(
    body: DeviceTypeIn, user: CurrentUser = Depends(require_role("admin", "operador")),
) -> dict:
    row = await db.pool().fetchrow(
        "INSERT INTO device_types (org_id, name, variables) VALUES ($1,$2,$3::jsonb) RETURNING id",
        user.org_id, body.name, json.dumps(body.variables),
    )
    return {"id": str(row["id"])}
