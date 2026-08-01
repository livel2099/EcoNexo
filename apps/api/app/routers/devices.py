"""Gestion de dispositivos y nodos de telemetria."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from .. import db
from ..audit import record_audit
from ..deps import CurrentUser, current_user, require_role
from ..schemas import (
    DeviceCreatedOut,
    DeviceIn,
    DeviceOut,
    DeviceReadingsIn,
    DeviceTypeIn,
    DeviceTypeOut,
    DeviceUpdateIn,
)
from ..security import hash_secret, new_token
from ..subscriptions import enforce_resource_limit
from ..ws import publish

router = APIRouter(prefix="/devices", tags=["devices"])

_DEVICE_SELECT = """
SELECT d.id,d.name,d.external_id,
       ST_Y(d.location::geometry) AS lat,
       ST_X(d.location::geometry) AS lon,
       d.status,d.battery,d.rssi,d.tags,d.last_seen,
       d.marker_shape,d.telemetry_mode,d.zone_id,z.name AS zone_name,
       d.pipeline_enabled,d.telemetry_config,d.last_pipeline_at,
       d.last_pipeline_status,
       COALESCE((
         SELECT jsonb_object_agg(latest.variable, latest.value)
         FROM (
           SELECT DISTINCT ON (r.variable) r.variable,r.value
           FROM readings r
           WHERE r.device_id=d.id
           ORDER BY r.variable,r.ts DESC
         ) latest
       ), '{}'::jsonb) AS latest_readings
FROM devices d
LEFT JOIN risk_zones z ON z.id=d.zone_id
"""


def _decode(value):
    return json.loads(value) if isinstance(value, str) else value


def _device_out(row) -> DeviceOut:
    data = dict(row)
    data["telemetry_config"] = _decode(data.get("telemetry_config")) or {}
    data["latest_readings"] = _decode(data.get("latest_readings")) or {}
    return DeviceOut(**data)


async def _zone_allowed(org_id: UUID, zone_id: UUID | None) -> None:
    if zone_id is None:
        return
    allowed = await db.pool().fetchval(
        "SELECT EXISTS(SELECT 1 FROM risk_zones WHERE id=$1 AND org_id=$2)",
        zone_id,
        org_id,
    )
    if not allowed:
        raise HTTPException(422, "La zona seleccionada no pertenece a la organización")


@router.get("", response_model=list[DeviceOut])
async def list_devices(user: CurrentUser = Depends(current_user)) -> list[DeviceOut]:
    rows = await db.pool().fetch(
        _DEVICE_SELECT
        + " WHERE d.org_id=$1 AND econexo_inside_misiones(d.location) "
          "ORDER BY d.pipeline_enabled DESC,d.name",
        user.org_id,
    )
    return [_device_out(row) for row in rows]


@router.get("/types", response_model=list[DeviceTypeOut])
async def list_device_types(
    user: CurrentUser = Depends(current_user),
) -> list[DeviceTypeOut]:
    rows = await db.pool().fetch(
        "SELECT id,name,variables FROM device_types WHERE org_id=$1 ORDER BY name",
        user.org_id,
    )
    result: list[DeviceTypeOut] = []
    for row in rows:
        data = dict(row)
        data["variables"] = _decode(data.get("variables")) or []
        result.append(DeviceTypeOut(**data))
    return result


@router.post("", response_model=DeviceCreatedOut, status_code=201)
async def create_device(
    body: DeviceIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> DeviceCreatedOut:
    await enforce_resource_limit(user.org_id, "max_devices")
    await _zone_allowed(user.org_id, body.zone_id)
    mqtt_user = f"dev-{body.external_id}"
    mqtt_pass = new_token()
    try:
        row = await db.pool().fetchrow(
            """
            INSERT INTO devices (
              org_id,device_type_id,name,external_id,location,tags,
              mqtt_username,mqtt_password_hash,status,marker_shape,
              telemetry_mode,zone_id,pipeline_enabled,telemetry_config
            ) VALUES (
              $1,$2,$3,$4,ST_MakePoint($6,$5)::geography,$7,$8,$9,'offline',
              $10,$11,$12,$13,$14::jsonb
            ) RETURNING id
            """,
            user.org_id,
            body.device_type_id,
            body.name.strip(),
            body.external_id,
            body.lat,
            body.lon,
            body.tags,
            mqtt_user,
            hash_secret(mqtt_pass),
            body.marker_shape,
            body.telemetry_mode,
            body.zone_id,
            body.pipeline_enabled,
            json.dumps(body.telemetry_config, ensure_ascii=False),
        )
    except Exception as exc:
        if "devices_org_id_external_id_key" in str(exc) or "unique" in str(exc).lower():
            raise HTTPException(status.HTTP_409_CONFLICT, "El identificador externo ya existe") from exc
        raise
    created = await db.pool().fetchrow(
        _DEVICE_SELECT + " WHERE d.id=$1 AND d.org_id=$2",
        row["id"],
        user.org_id,
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="create",
        resource="device",
        resource_id=row["id"],
        metadata={
            "external_id": body.external_id,
            "telemetry_mode": body.telemetry_mode,
            "marker_shape": body.marker_shape,
            "zone_id": str(body.zone_id) if body.zone_id else None,
        },
    )
    return DeviceCreatedOut(
        **_device_out(created).model_dump(),
        mqtt_username=mqtt_user,
        mqtt_password=mqtt_pass,
    )


@router.patch("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: UUID,
    body: DeviceUpdateIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> DeviceOut:
    if not body.model_fields_set:
        raise HTTPException(422, "No se recibieron cambios")
    current = await db.pool().fetchrow(
        _DEVICE_SELECT + " WHERE d.id=$1 AND d.org_id=$2",
        device_id,
        user.org_id,
    )
    if current is None:
        raise HTTPException(404, "Dispositivo no encontrado")
    current_data = dict(current)
    zone_id = body.zone_id if "zone_id" in body.model_fields_set else current_data["zone_id"]
    await _zone_allowed(user.org_id, zone_id)
    lat = body.lat if body.lat is not None else float(current_data["lat"])
    lon = body.lon if body.lon is not None else float(current_data["lon"])
    tags = body.tags if body.tags is not None else list(current_data["tags"] or [])
    telemetry_config = (
        body.telemetry_config
        if body.telemetry_config is not None
        else (_decode(current_data.get("telemetry_config")) or {})
    )
    await db.pool().execute(
        """
        UPDATE devices SET
          name=$3,location=ST_MakePoint($5,$4)::geography,tags=$6,
          marker_shape=$7,telemetry_mode=$8,zone_id=$9,
          pipeline_enabled=$10,telemetry_config=$11::jsonb,updated_at=now()
        WHERE id=$1 AND org_id=$2
        """,
        device_id,
        user.org_id,
        body.name.strip() if body.name else current_data["name"],
        lat,
        lon,
        tags,
        body.marker_shape or current_data["marker_shape"],
        body.telemetry_mode or current_data["telemetry_mode"],
        zone_id,
        current_data["pipeline_enabled"] if body.pipeline_enabled is None else body.pipeline_enabled,
        json.dumps(telemetry_config, ensure_ascii=False),
    )
    updated = await db.pool().fetchrow(
        _DEVICE_SELECT + " WHERE d.id=$1 AND d.org_id=$2",
        device_id,
        user.org_id,
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="update",
        resource="device",
        resource_id=device_id,
        metadata=body.model_dump(exclude_none=True, mode="json"),
    )
    return _device_out(updated)


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: UUID,
    user: CurrentUser = Depends(require_role("admin")),
) -> Response:
    result = await db.pool().execute(
        "DELETE FROM devices WHERE id=$1 AND org_id=$2",
        device_id,
        user.org_id,
    )
    if result.endswith("0"):
        raise HTTPException(404, "Dispositivo no encontrado")
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="delete",
        resource="device",
        resource_id=device_id,
    )
    return Response(status_code=204)


@router.post("/{device_id}/readings", status_code=201)
async def create_device_readings(
    device_id: UUID,
    body: DeviceReadingsIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> dict[str, object]:
    device = await db.pool().fetchrow(
        "SELECT id,external_id,name FROM devices WHERE id=$1 AND org_id=$2",
        device_id,
        user.org_id,
    )
    if device is None:
        raise HTTPException(404, "Dispositivo no encontrado")
    observed_at = body.observed_at or datetime.now(timezone.utc)
    records = [
        (user.org_id, device_id, variable, value, observed_at)
        for variable, value in body.values.items()
    ]
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            await conn.copy_records_to_table(
                "readings",
                records=records,
                columns=["org_id", "device_id", "variable", "value", "ts"],
            )
            await conn.execute(
                """
                UPDATE devices SET status='online',last_seen=$2,last_pipeline_at=$2,
                    last_pipeline_status='manual_ingest',updated_at=now()
                WHERE id=$1
                """,
                device_id,
                observed_at,
            )
    await publish(
        f"econexo/internal/{user.org_id}/readings",
        {
            "device_id": str(device_id),
            "external_id": device["external_id"],
            "name": device["name"],
            "telemetry_mode": "manual",
            "values": body.values,
            "ts": observed_at.isoformat(),
        },
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="create",
        resource="device_readings",
        resource_id=device_id,
        metadata={"variables": sorted(body.values), "count": len(records)},
    )
    return {"status": "ok", "inserted": len(records), "observed_at": observed_at}


@router.get("/{device_id}/readings")
async def device_readings(
    device_id: UUID,
    variable: str,
    hours: int = 24,
    user: CurrentUser = Depends(current_user),
) -> list[dict]:
    rows = await db.pool().fetch(
        """
        SELECT ts,value FROM readings
        WHERE device_id=$1 AND org_id=$2 AND variable=$3
          AND ts > now() - make_interval(hours => $4)
        ORDER BY ts
        """,
        device_id,
        user.org_id,
        variable,
        max(1, min(hours, 24 * 90)),
    )
    return [{"ts": str(row["ts"]), "value": row["value"]} for row in rows]


@router.post("/types", response_model=DeviceTypeOut, status_code=201)
async def create_device_type(
    body: DeviceTypeIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> DeviceTypeOut:
    row = await db.pool().fetchrow(
        """
        INSERT INTO device_types(org_id,name,variables)
        VALUES ($1,$2,$3::jsonb)
        RETURNING id,name,variables
        """,
        user.org_id,
        body.name.strip(),
        json.dumps(body.variables, ensure_ascii=False),
    )
    data = dict(row)
    data["variables"] = _decode(data["variables"]) or []
    return DeviceTypeOut(**data)
