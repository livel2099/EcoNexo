"""Ejecucion y configuracion del pipeline operativo desde Command Core."""
from __future__ import annotations

import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import db
from ..audit import record_audit
from ..config import get_settings
from ..deps import CurrentUser, current_user, require_role
from ..schemas import (
    BootstrapTelemetryIn,
    BootstrapTelemetryOut,
    DeviceIn,
    PipelineRunOut,
    TelemetryPipelineSettingsIn,
    TelemetryPipelineSettingsOut,
)
from ..telemetry_pipeline import pipeline_settings, run_org_pipeline
from .devices import create_device

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def _decode(value):
    return json.loads(value) if isinstance(value, str) else value


def _run_out(row) -> PipelineRunOut:
    data = dict(row)
    data["errors"] = _decode(data.get("errors")) or []
    data["summary"] = _decode(data.get("summary")) or {}
    return PipelineRunOut(**data)


def _settings_out(row) -> TelemetryPipelineSettingsOut:
    data = dict(row)
    data.pop("updated_by", None)
    data["firms_configured"] = bool(get_settings().nasa_firms_key.strip())
    return TelemetryPipelineSettingsOut(**data)


@router.get("/settings", response_model=TelemetryPipelineSettingsOut)
async def get_settings(
    user: CurrentUser = Depends(current_user),
) -> TelemetryPipelineSettingsOut:
    return _settings_out(await pipeline_settings(user.org_id))


@router.patch("/settings", response_model=TelemetryPipelineSettingsOut)
async def update_settings(
    body: TelemetryPipelineSettingsIn,
    user: CurrentUser = Depends(require_role("admin")),
) -> TelemetryPipelineSettingsOut:
    row = await db.pool().fetchrow(
        """
        INSERT INTO telemetry_pipeline_settings(
          org_id,enabled,auto_run,interval_minutes,stale_minutes,
          refresh_firms,evaluate_rules,updated_by
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        ON CONFLICT (org_id) DO UPDATE SET
          enabled=EXCLUDED.enabled,
          auto_run=EXCLUDED.auto_run,
          interval_minutes=EXCLUDED.interval_minutes,
          stale_minutes=EXCLUDED.stale_minutes,
          refresh_firms=EXCLUDED.refresh_firms,
          evaluate_rules=EXCLUDED.evaluate_rules,
          updated_by=EXCLUDED.updated_by,
          updated_at=now()
        RETURNING *
        """,
        user.org_id,
        body.enabled,
        body.auto_run,
        body.interval_minutes,
        body.stale_minutes,
        body.refresh_firms,
        body.evaluate_rules,
        user.id,
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="update",
        resource="telemetry_pipeline_settings",
        resource_id=user.org_id,
        metadata=body.model_dump(mode="json"),
    )
    return _settings_out(row)


@router.post("/run", response_model=PipelineRunOut)
async def run_pipeline(
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> PipelineRunOut:
    try:
        result = await run_org_pipeline(user.org_id, user.id, source="command_core")
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    row = await db.pool().fetchrow(
        """
        SELECT id,status,source,started_at,finished_at,devices_total,
               devices_updated,readings_inserted,detections_ingested,
               alerts_created,errors,summary
        FROM pipeline_runs WHERE id=$1
        """,
        UUID(result["id"]),
    )
    return _run_out(row)


@router.get("/runs", response_model=list[PipelineRunOut])
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    user: CurrentUser = Depends(current_user),
) -> list[PipelineRunOut]:
    rows = await db.pool().fetch(
        """
        SELECT id,status,source,started_at,finished_at,devices_total,
               devices_updated,readings_inserted,detections_ingested,
               alerts_created,errors,summary
        FROM pipeline_runs WHERE org_id=$1
        ORDER BY started_at DESC LIMIT $2
        """,
        user.org_id,
        limit,
    )
    return [_run_out(row) for row in rows]


@router.post("/bootstrap", response_model=BootstrapTelemetryOut, status_code=201)
async def bootstrap_telemetry(
    body: BootstrapTelemetryIn,
    user: CurrentUser = Depends(require_role("admin")),
) -> BootstrapTelemetryOut:
    zone = None
    if body.zone_id:
        zone = await db.pool().fetchrow(
            """
            SELECT id,ST_Y(center::geometry) AS lat,ST_X(center::geometry) AS lon
            FROM risk_zones WHERE id=$1 AND org_id=$2
            """,
            body.zone_id,
            user.org_id,
        )
        if zone is None:
            raise HTTPException(404, "Zona no encontrada")
    else:
        zone = await db.pool().fetchrow(
            """
            SELECT id,ST_Y(center::geometry) AS lat,ST_X(center::geometry) AS lon
            FROM risk_zones WHERE org_id=$1 ORDER BY created_at LIMIT 1
            """,
            user.org_id,
        )
    if zone is None:
        source = await db.pool().fetchrow(
            """
            INSERT INTO environmental_source_settings(org_id)
            VALUES ($1) ON CONFLICT (org_id) DO UPDATE SET org_id=EXCLUDED.org_id
            RETURNING default_latitude,default_longitude
            """,
            user.org_id,
        )
        zone_id = await db.pool().fetchval(
            """
            INSERT INTO risk_zones(org_id,name,kind,center,radius_m,area)
            VALUES (
              $1,'Zona operativa inicial','general',
              ST_MakePoint($3,$2)::geography,5000,
              ST_Buffer(ST_MakePoint($3,$2)::geography,5000)
            ) RETURNING id
            """,
            user.org_id,
            float(source["default_latitude"]),
            float(source["default_longitude"]),
        )
        zone = {
            "id": zone_id,
            "lat": float(source["default_latitude"]),
            "lon": float(source["default_longitude"]),
        }
    created = []
    offsets = [
        (0.0000, 0.0000),
        (0.0120, 0.0120),
        (-0.0120, 0.0100),
        (0.0100, -0.0120),
        (-0.0100, -0.0100),
        (0.0180, -0.0040),
    ]
    shapes = ["square", "triangle", "circle"]
    for index in range(body.count):
        lat_offset, lon_offset = offsets[index]
        candidate_lat = float(zone["lat"]) + lat_offset
        candidate_lon = float(zone["lon"]) + lon_offset
        inside = await db.pool().fetchval(
            "SELECT econexo_inside_misiones(ST_MakePoint($2,$1)::geography)",
            candidate_lat,
            candidate_lon,
        )
        if not inside:
            candidate_lat = float(zone["lat"])
            candidate_lon = float(zone["lon"])
        identifier = f"virtual-{str(uuid4())[:8]}"
        try:
            item = await create_device(
                DeviceIn(
                    name=f"Nodo virtual {index + 1}",
                    external_id=identifier,
                    lat=candidate_lat,
                    lon=candidate_lon,
                    tags=["virtual", "open-meteo", "pipeline"],
                    marker_shape=shapes[index % len(shapes)],
                    telemetry_mode="open_meteo",
                    zone_id=zone["id"],
                    pipeline_enabled=True,
                    telemetry_config={
                        "provider": "open-meteo",
                        "mode": "modelled_context",
                        "variables": [
                            "temp", "humidity", "precipitation", "wind_gust",
                            "soil_moisture", "vpd",
                        ],
                    },
                ),
                user,
            )
        except HTTPException as exc:
            if exc.status_code == 402 and created:
                break
            raise
        created.append(item)
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="bootstrap",
        resource="telemetry_network",
        resource_id=zone["id"],
        metadata={"count": len(created), "source": "open_meteo"},
    )
    return BootstrapTelemetryOut(
        created=created,
        zone_id=zone["id"],
        detail="Red virtual creada. Ejecutá el pipeline desde Command Core para cargar telemetría.",
    )
