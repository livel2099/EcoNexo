"""Pipeline operativo de telemetria, reglas y fuentes satelitales.

Funciona en el mismo servicio API para que la beta de Render no dependa de
MQTT ni de workers pagos. Los nodos fisicos siguen pudiendo usar MQTT; los
nodos virtuales usan Open-Meteo como contexto modelado y quedan rotulados como
tales en la interfaz.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
import httpx

from . import db
from .config import get_settings
from .correlation import Source
from .pipeline import anomaly_score, create_alert
from .rules_engine import Condition, Rule, evaluate_rule
from .ws import publish

log = logging.getLogger("econexo.telemetry_pipeline")

MISIONES_BBOX = "-56.10,-28.20,-53.55,-25.45"
OPEN_METEO_VARIABLES: dict[str, str] = {
    "temperature_2m": "temp",
    "relative_humidity_2m": "humidity",
    "precipitation": "precipitation",
    "wind_speed_10m": "wind_speed",
    "wind_gusts_10m": "wind_gust",
    "soil_moisture_0_to_1cm": "soil_moisture",
    "vapour_pressure_deficit": "vpd",
}


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _confidence(raw: str) -> float:
    value = (raw or "").strip().lower()
    if value in {"h", "high"}:
        return 0.9
    if value in {"n", "nominal"}:
        return 0.7
    if value in {"l", "low"}:
        return 0.4
    try:
        number = float(value)
        return max(0.0, min(1.0, number / 100 if number > 1 else number))
    except ValueError:
        return 0.7


async def pipeline_settings(org_id: UUID, user_id: UUID | None = None) -> Any:
    row = await db.pool().fetchrow(
        """
        INSERT INTO telemetry_pipeline_settings(org_id, updated_by)
        VALUES ($1,$2)
        ON CONFLICT (org_id) DO UPDATE SET
          updated_by=COALESCE(telemetry_pipeline_settings.updated_by, EXCLUDED.updated_by)
        RETURNING *
        """,
        org_id,
        user_id,
    )
    return row


async def fetch_open_meteo_current(lat: float, lon: float) -> dict[str, float]:
    settings = get_settings()
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "current": ",".join(OPEN_METEO_VARIABLES),
        "timezone": "UTC",
    }
    async with httpx.AsyncClient(timeout=settings.pipeline_http_timeout_seconds) as client:
        response = await client.get(settings.open_meteo_forecast_url, params=params)
        response.raise_for_status()
        payload = response.json()
    current = payload.get("current") or {}
    result: dict[str, float] = {}
    for source_key, target_key in OPEN_METEO_VARIABLES.items():
        value = _number(current.get(source_key))
        if value is not None:
            if target_key == "soil_moisture":
                value *= 100.0
            result[target_key] = round(value, 4)
    return result


async def refresh_open_meteo_device(device: Any) -> tuple[int, dict[str, float]]:
    readings = await fetch_open_meteo_current(float(device["lat"]), float(device["lon"]))
    if not readings:
        raise RuntimeError("Open-Meteo no devolvio variables actuales")
    now = datetime.now(timezone.utc)
    records = [
        (device["org_id"], device["id"], variable, value, now)
        for variable, value in readings.items()
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
                UPDATE devices SET status='online', last_seen=$2,
                    last_pipeline_at=$2, last_pipeline_status='ok', updated_at=now()
                WHERE id=$1
                """,
                device["id"],
                now,
            )
    await publish(
        f"econexo/internal/{device['org_id']}/readings",
        {
            "device_id": str(device["id"]),
            "external_id": device["external_id"],
            "name": device["name"],
            "telemetry_mode": "open_meteo",
            "values": readings,
            "ts": now.isoformat(),
        },
    )
    return len(records), readings


async def mark_stale_devices(org_id: UUID, stale_minutes: int) -> int:
    result = await db.pool().execute(
        """
        UPDATE devices SET status='offline', updated_at=now()
        WHERE org_id=$1 AND telemetry_mode IN ('mqtt','manual')
          AND status <> 'offline'
          AND (last_seen IS NULL OR last_seen < now() - make_interval(mins => $2))
        """,
        org_id,
        stale_minutes,
    )
    try:
        return int(result.rsplit(" ", 1)[-1])
    except (ValueError, IndexError):
        return 0


async def _inside_misiones(lat: float, lon: float) -> bool:
    return bool(
        await db.pool().fetchval(
            "SELECT econexo_inside_misiones(ST_MakePoint($2,$1)::geography)",
            lat,
            lon,
        )
    )


async def refresh_firms(org_id: UUID) -> tuple[int, int]:
    settings = get_settings()
    key = settings.nasa_firms_key.strip()
    if not settings.firms_inline_enabled or not key:
        return 0, 0
    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{key}/{settings.firms_source}/{MISIONES_BBOX}/1"
    )
    async with httpx.AsyncClient(timeout=settings.pipeline_http_timeout_seconds) as client:
        response = await client.get(url)
        response.raise_for_status()
    reader = csv.DictReader(io.StringIO(response.text))
    inserted = 0
    alerts_created = 0
    for raw in reader:
        try:
            lat = float(raw["latitude"])
            lon = float(raw["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if not await _inside_misiones(lat, lon):
            continue
        date = raw.get("acq_date") or datetime.now(timezone.utc).date().isoformat()
        time_value = str(raw.get("acq_time") or "0000").zfill(4)
        try:
            acquired_at = datetime.fromisoformat(
                f"{date}T{time_value[:2]}:{time_value[2:]}:00+00:00"
            )
        except (TypeError, ValueError):
            log.warning("FIRMS omitió una fila con fecha/hora inválida: %s %s", date, time_value)
            continue
        confidence = _confidence(str(raw.get("confidence") or "n"))
        dedup_source = (
            f"{settings.firms_source}|{lat:.5f}|{lon:.5f}|{acquired_at.isoformat()}"
        )
        dedup_key = hashlib.sha256(dedup_source.encode("utf-8")).hexdigest()
        row = await db.pool().fetchrow(
            """
            INSERT INTO satellite_detections
              (org_id,source,location,brightness,confidence,frp,acquired_at,raw,dedup_key)
            VALUES (
              NULL,$1,ST_MakePoint($3,$2)::geography,$4,$5,$6,$7,$8::jsonb,$9
            )
            ON CONFLICT (dedup_key) DO UPDATE SET
              brightness=EXCLUDED.brightness, confidence=EXCLUDED.confidence,
              frp=EXCLUDED.frp, raw=EXCLUDED.raw
            RETURNING id, (xmax = 0) AS inserted
            """,
            settings.firms_source,
            lat,
            lon,
            _number(raw.get("bright_ti4") or raw.get("brightness")),
            confidence,
            _number(raw.get("frp")),
            acquired_at,
            json.dumps(raw, ensure_ascii=False),
            dedup_key,
        )
        if row and row["inserted"]:
            inserted += 1
        zone = await db.pool().fetchrow(
            """
            SELECT id FROM risk_zones
            WHERE org_id=$1 AND kind IN ('incendio','general')
              AND ST_Covers(area::geometry, ST_SetSRID(ST_MakePoint($3,$2),4326))
            LIMIT 1
            """,
            org_id,
            lat,
            lon,
        )
        if zone and confidence >= 0.6:
            duplicate = await db.pool().fetchval(
                """
                SELECT EXISTS(
                  SELECT 1 FROM alerts
                  WHERE org_id=$1 AND type='incendio'
                    AND detected_at > now() - interval '6 hours'
                    AND ST_DWithin(location, ST_MakePoint($3,$2)::geography, 1500)
                )
                """,
                org_id,
                lat,
                lon,
            )
            if not duplicate:
                await create_alert(
                    org_id=org_id,
                    alert_type="incendio",
                    severity="alta" if confidence < 0.85 else "critica",
                    lat=lat,
                    lon=lon,
                    title="Foco de calor detectado por NASA FIRMS",
                    sensor_source=Source("satelite", lat, lon, confidence),
                    radius_m=5000,
                )
                alerts_created += 1
    return inserted, alerts_created


async def _rule_values(device_id: UUID, conditions: list[dict[str, Any]], window_seconds: int) -> dict[str, float]:
    values: dict[str, float] = {}
    for condition in conditions:
        variable = str(condition.get("variable") or "").strip()
        if not variable:
            continue
        value = await db.pool().fetchval(
            """
            SELECT avg(value)::double precision FROM readings
            WHERE device_id=$1 AND variable=$2
              AND ts > now() - make_interval(secs => $3)
            """,
            device_id,
            variable,
            max(1, window_seconds),
        )
        if value is not None:
            values[variable] = float(value)
    return values


async def evaluate_device_rules(device: Any) -> int:
    rules = await db.pool().fetch(
        """
        SELECT r.id,r.alert_type,r.conditions,r.condition_logic,r.window_seconds,
               r.zone_id,r.device_tags,r.severity,r.require_satellite,r.name
        FROM rules r
        WHERE r.org_id=$1 AND r.enabled
          AND (cardinality(r.device_tags)=0 OR r.device_tags && $2::text[])
          AND (r.zone_id IS NULL OR EXISTS(
            SELECT 1 FROM risk_zones z
            WHERE z.id=r.zone_id
              AND ST_Covers(z.area::geometry, ST_SetSRID(ST_MakePoint($4,$3),4326))
          ))
        """,
        device["org_id"],
        list(device["tags"] or []),
        float(device["lat"]),
        float(device["lon"]),
    )
    created = 0
    for row in rules:
        conditions_raw = row["conditions"]
        conditions = json.loads(conditions_raw) if isinstance(conditions_raw, str) else list(conditions_raw or [])
        values = await _rule_values(device["id"], conditions, int(row["window_seconds"]))
        satellite_confirmed = False
        if row["require_satellite"]:
            satellite_confirmed = bool(
                await db.pool().fetchval(
                    """
                    SELECT EXISTS(
                      SELECT 1 FROM satellite_detections
                      WHERE acquired_at > now() - interval '6 hours'
                        AND (org_id=$1 OR org_id IS NULL)
                        AND ST_DWithin(location, ST_MakePoint($3,$2)::geography, 5000)
                    )
                    """,
                    device["org_id"],
                    float(device["lat"]),
                    float(device["lon"]),
                )
            )
        evaluation = evaluate_rule(
            Rule(
                conditions=[
                    Condition(
                        variable=str(item["variable"]),
                        operator=str(item["operator"]),
                        threshold=float(item["threshold"]),
                    )
                    for item in conditions
                ],
                logic=str(row["condition_logic"]),
                require_satellite=bool(row["require_satellite"]),
            ),
            values,
            satellite_confirmed=satellite_confirmed,
        )
        if not evaluation.fired:
            continue
        duplicate = await db.pool().fetchval(
            """
            SELECT EXISTS(
              SELECT 1 FROM alerts
              WHERE org_id=$1 AND rule_id=$2 AND device_id=$3
                AND status IN ('nueva','confirmada','escalada','asignada')
                AND detected_at > now() - make_interval(secs => GREATEST($4,300))
            )
            """,
            device["org_id"],
            row["id"],
            device["id"],
            int(row["window_seconds"]),
        )
        if duplicate:
            continue
        matched_scores: list[float] = []
        for condition in evaluation.matched_conditions:
            if condition.variable in values:
                matched_scores.append(
                    await anomaly_score(str(device["id"]), condition.variable, values[condition.variable])
                )
        sensor_score = max(matched_scores, default=0.65)
        await create_alert(
            org_id=device["org_id"],
            alert_type=str(row["alert_type"]),
            severity=str(row["severity"]),
            lat=float(device["lat"]),
            lon=float(device["lon"]),
            title=str(row["name"]),
            sensor_source=Source(
                "sensor",
                float(device["lat"]),
                float(device["lon"]),
                sensor_score,
            ),
            device_id=str(device["id"]),
            rule_id=str(row["id"]),
            radius_m=5000,
        )
        created += 1
    return created


async def run_org_pipeline(
    org_id: UUID,
    actor_user_id: UUID | None,
    *,
    source: str = "command_core",
) -> dict[str, Any]:
    settings = await pipeline_settings(org_id, actor_user_id)
    if not settings["enabled"]:
        raise RuntimeError("El pipeline esta deshabilitado en Admin Core")
    # Cierra una corrida huérfana y deja que la restricción única de la base
    # sea la autoridad final ante ejecuciones concurrentes o varias réplicas.
    await db.pool().execute(
        """
        UPDATE pipeline_runs SET status='failed', finished_at=now(),
          errors=COALESCE(errors,'[]'::jsonb) ||
            jsonb_build_array(jsonb_build_object(
              'stage','pipeline_guard',
              'detail','Ejecución huérfana cerrada antes de una nueva corrida'
            ))
        WHERE org_id=$1 AND status='running'
          AND started_at < now() - interval '30 minutes'
        """,
        org_id,
    )
    try:
        run_id = await db.pool().fetchval(
            """
            INSERT INTO pipeline_runs(org_id,started_by,source)
            VALUES ($1,$2,$3) RETURNING id
            """,
            org_id,
            actor_user_id,
            source,
        )
    except asyncpg.UniqueViolationError as exc:
        raise RuntimeError("Ya existe una ejecución del pipeline en curso") from exc
    errors: list[dict[str, str]] = []
    devices_updated = 0
    readings_inserted = 0
    alerts_created = 0
    detections_ingested = 0
    devices = await db.pool().fetch(
        """
        SELECT id,org_id,name,external_id,tags,telemetry_mode,pipeline_enabled,
               ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon
        FROM devices
        WHERE org_id=$1 AND pipeline_enabled AND econexo_inside_misiones(location)
        ORDER BY name
        LIMIT $2
        """,
        org_id,
        get_settings().pipeline_max_devices_per_run,
    )
    try:
        await mark_stale_devices(org_id, int(settings["stale_minutes"]))
        if settings["refresh_firms"]:
            try:
                detections_ingested, firms_alerts = await refresh_firms(org_id)
                alerts_created += firms_alerts
            except Exception as exc:  # pragma: no cover - depende de fuente externa
                errors.append({"stage": "firms", "error": str(exc)[:300]})
                log.warning("FIRMS inline fallo: %s", exc)
        for device in devices:
            try:
                if device["telemetry_mode"] == "open_meteo":
                    inserted, _ = await refresh_open_meteo_device(device)
                    readings_inserted += inserted
                    devices_updated += 1
                if settings["evaluate_rules"]:
                    alerts_created += await evaluate_device_rules(device)
            except Exception as exc:  # pragma: no cover - depende de fuentes externas
                errors.append({"device": str(device["id"]), "error": str(exc)[:300]})
                await db.pool().execute(
                    """
                    UPDATE devices SET last_pipeline_at=now(), last_pipeline_status=$2,
                        updated_at=now() WHERE id=$1
                    """,
                    device["id"],
                    f"error:{exc.__class__.__name__}",
                )
        status = "completed" if not errors else "partial"
        summary = {
            "message": "Pipeline operativo actualizado",
            "virtual_sources": sum(1 for item in devices if item["telemetry_mode"] == "open_meteo"),
            "mqtt_sources": sum(1 for item in devices if item["telemetry_mode"] == "mqtt"),
            "manual_sources": sum(1 for item in devices if item["telemetry_mode"] == "manual"),
            "firms_configured": bool(get_settings().nasa_firms_key.strip()),
        }
        await db.pool().execute(
            """
            UPDATE pipeline_runs SET status=$2, finished_at=now(), devices_total=$3,
                devices_updated=$4, readings_inserted=$5, detections_ingested=$6,
                alerts_created=$7, errors=$8::jsonb, summary=$9::jsonb
            WHERE id=$1
            """,
            run_id,
            status,
            len(devices),
            devices_updated,
            readings_inserted,
            detections_ingested,
            alerts_created,
            json.dumps(errors, ensure_ascii=False),
            json.dumps(summary, ensure_ascii=False),
        )
        payload = {
            "id": str(run_id),
            "status": status,
            "devices_total": len(devices),
            "devices_updated": devices_updated,
            "readings_inserted": readings_inserted,
            "detections_ingested": detections_ingested,
            "alerts_created": alerts_created,
            "errors": errors,
            "summary": summary,
        }
        await publish(f"econexo/internal/{org_id}/pipeline", payload)
        return payload
    except Exception as exc:
        await db.pool().execute(
            """
            UPDATE pipeline_runs SET status='failed', finished_at=now(),
                devices_total=$2, errors=$3::jsonb WHERE id=$1
            """,
            run_id,
            len(devices),
            json.dumps([{"stage": "pipeline", "error": str(exc)[:300]}], ensure_ascii=False),
        )
        raise


async def pipeline_scheduler(stop) -> None:
    """Planificador liviano para Render; solo ejecuta organizaciones opt-in."""
    import asyncio

    while not stop.is_set():
        try:
            rows = await db.pool().fetch(
                """
                SELECT s.org_id
                FROM telemetry_pipeline_settings s
                JOIN organizations o ON o.id=s.org_id AND o.is_active
                WHERE s.enabled AND s.auto_run
                  AND NOT EXISTS (
                    SELECT 1 FROM pipeline_runs r
                    WHERE r.org_id=s.org_id
                      AND r.status IN ('running','completed','partial')
                      AND r.started_at > now() - make_interval(mins => s.interval_minutes)
                  )
                ORDER BY s.updated_at
                LIMIT 10
                """
            )
            for row in rows:
                try:
                    await run_org_pipeline(row["org_id"], None, source="scheduler")
                except Exception as exc:  # pragma: no cover - runtime externo
                    log.warning("Pipeline automatico %s fallo: %s", row["org_id"], exc)
        except Exception as exc:  # pragma: no cover
            log.warning("Scheduler de pipeline reintentando: %s", exc)
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except TimeoutError:
            pass
