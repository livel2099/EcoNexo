"""Persistencia, ejecución y aprendizaje del ciclo predictivo por organización."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from uuid import UUID

import httpx
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from . import db
from .config import get_settings
from .open_meteo_http import customer_url, get_response
from .predictive_engine import (BASELINE_VERSION, baseline_version, baseline, drift, evaluation, future_features,
                               label_forecast, probability, train_model)


def decode(row) -> dict:
    result = dict(row)
    for key in ("features", "provenance", "explanation", "artifact", "evaluation"):
        if key in result and isinstance(result[key], str):
            result[key] = json.loads(result[key])
    return result


async def forecasts_for_points(devices: list[dict], hazard: str = "fire") -> list[dict]:
    """Solo se invoca tras verificar la habilitación explícita de la organización."""
    settings = get_settings()
    key = settings.open_meteo_api_key.strip()
    url = customer_url(settings.open_meteo_air_quality_url if hazard == "health_air" else settings.open_meteo_forecast_url, key)
    results = []
    async with httpx.AsyncClient(timeout=settings.pipeline_http_timeout_seconds) as client:
        for offset in range(0, len(devices), 50):
            group = devices[offset:offset + 50]
            params = dict(latitude=",".join(f"{d['lat']:.5f}" for d in group),
                          longitude=",".join(f"{d['lon']:.5f}" for d in group),
                          hourly={"fire": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation", "hydric": "precipitation", "health_heat": "apparent_temperature", "health_air": "pm2_5"}[hazard],
                          timezone="UTC", temperature_unit="celsius", wind_speed_unit="kmh",
                          precipitation_unit="mm", forecast_days="4")
            if hazard == "health_air":
                for option in ("temperature_unit", "wind_speed_unit", "precipitation_unit"):
                    params.pop(option)
            if key:
                params["apikey"] = key
            response = await get_response(client, url, params, ttl=300)
            if response.status_code != 200:
                raise RuntimeError(f"Fuente meteorológica no disponible (HTTP {response.status_code})")
            payload = response.json()
            items = payload if isinstance(payload, list) else [payload]
            if len(items) != len(group):
                raise RuntimeError("La fuente no devolvió todos los territorios solicitados")
            results.extend(items)
    return results


async def issue_forecasts(org_id: UUID, actor_id: UUID | None, hazard: str | None = None, horizon: int | None = None) -> dict:
    """Emite solo horizontes habilitados mediante consentimiento administrativo."""
    # La consulta externa ocurre sin reservar una conexión: el cache compartido
    # también usa Postgres y una transacción abierta agotaría pools pequeños.
    settings_rows = await db.pool().fetch("SELECT s.*,m.version,m.artifact FROM predictive_settings s LEFT JOIN predictive_models m ON m.id=s.active_model_id WHERE s.org_id=$1 AND s.enabled", org_id)
    settings_rows = [row for row in settings_rows if (hazard is None or row.get("hazard", "fire") == hazard)
                     and (horizon is None or row["horizon_hours"] == horizon)]
    if not settings_rows:
        return dict(created=0, skipped=0, errors=[], message="Pronósticos deshabilitados; requieren habilitación de la organización")
    horizon_settings = {(row.get("hazard", "fire"), row["horizon_hours"]): decode(row) for row in settings_rows}
    clock = await db.pool().fetchval("SELECT clock_timestamp()")
    targets = await db.pool().fetch("""
        SELECT d.id,d.name,d.tags,ST_Y(d.location::geometry) AS lat,ST_X(d.location::geometry) AS lon
        FROM devices d WHERE d.org_id=$1 AND d.pipeline_enabled
          AND econexo_inside_misiones(d.location)
          AND NOT (d.tags && ARRAY['demo','simulator','fixture','simulated']::text[])
        ORDER BY d.id LIMIT $2
    """, org_id, get_settings().pipeline_max_devices_per_run)
    if not targets:
        return dict(created=0, skipped=0, errors=[], message="No hay nodos aptos para pronosticar. Activá el pipeline de un nodo dentro de Misiones, sin etiquetas de simulación.")
    existing = await db.pool().fetch("SELECT device_id,horizon_hours,model_version,hazard FROM predictions WHERE org_id=$1 AND issuance_day=$2", org_id, clock.date())
    existing_keys = {(row["device_id"], row["horizon_hours"], row["model_version"], row.get("hazard", "fire")) for row in existing}
    todo = []
    for device in targets:
        for (risk, hours), hs in horizon_settings.items():
            versions = [(baseline_version(risk), None, None)]
            if hs.get("active_model_id"):
                versions.append((hs["version"], hs["active_model_id"], hs["artifact"]))
            for version, model_id, artifact in versions:
                if (device["id"], hours, version, risk) not in existing_keys:
                    todo.append((device, hours, version, model_id, artifact, risk))
    if not todo:
        return dict(created=0, skipped=len(existing), errors=[], message="Sin emisiones nuevas pendientes")
    payloads_by_risk = {}
    errors = []
    for risk in sorted({item[5] for item in todo}):
        unique = list({item[0]["id"]: dict(item[0]) for item in todo if item[5] == risk}.values())
        try:
            payloads = await forecasts_for_points(unique) if risk == "fire" else await forecasts_for_points(unique, risk)
            payloads_by_risk.update({(risk, d["id"]): payload for d, payload in zip(unique, payloads)})
        except (RuntimeError, TimeoutError, httpx.HTTPError):
            errors.append(dict(hazard=risk, detail="Fuente externa no disponible; no se emitió un índice sustituto"))
    available = [item for item in todo if (item[5], item[0]["id"]) in payloads_by_risk]
    result = await _archive_forecasts(org_id, actor_id, available, payloads_by_risk, len(existing))
    result["errors"].extend(errors)
    return result


async def _archive_forecasts(org_id: UUID, actor_id: UUID | None, todo: list, by_device: dict, skipped: int) -> dict:
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            locked = await conn.fetchval("SELECT pg_try_advisory_xact_lock(hashtextextended($1,0))", "predictive:" + str(org_id))
            if not locked:
                return dict(created=0, skipped=0, errors=[], message="Otra emisión está en curso")
            # Revalidar consentimiento/modelo después de la llamada externa.
            current = await conn.fetch("SELECT horizon_hours,active_model_id,hazard FROM predictive_settings WHERE org_id=$1 AND enabled FOR SHARE", org_id)
            active = {(row.get("hazard", "fire"), row["horizon_hours"]): row["active_model_id"] for row in current}
            issued_at = await conn.fetchval("SELECT clock_timestamp()")
            created, errors = 0, []
            for device, hours, version, model_id, artifact, risk in todo:
                if (risk, hours) not in active or (model_id is not None and active[(risk, hours)] != model_id):
                    continue
                try:
                    payload = by_device[(risk, device["id"])]
                    features, start, end, series = future_features(payload, issued_at, hours, risk)
                    index, reasons = baseline(features, risk)
                    prob = probability(features, artifact) if artifact else None
                    threshold = artifact["threshold"] if artifact else 0.65
                    warning = (prob if prob is not None else index) >= threshold
                    action = "Preparar vigilancia y recursos; verificar combustible, fuentes de ignición y condiciones locales." if warning else "Mantener monitoreo y revisar cambios en el próximo pronóstico."
                    if warning and risk != "fire":
                        action = {"hydric": "Verificar drenajes, puntos anegables y mediciones locales; revisar protocolo hídrico con responsables.", "health_heat": "Revisar el protocolo de calor con responsables sanitarios y contrastar condiciones locales.", "health_air": "Contrastar con estaciones locales y revisar el protocolo de calidad del aire con responsables sanitarios."}[risk]
                    provenance = dict(provider="open-meteo", data_kind="external_air_quality_forecast" if risk == "health_air" else "external_weather_forecast", hazard=risk, source_endpoint="air-quality" if risk == "health_air" else "forecast", received_at=issued_at.isoformat(),
                                      provider_issued_at=None, provider_issue_time_known=False, max_cache_age_seconds=300,
                                      grid_latitude=payload.get("latitude"), grid_longitude=payload.get("longitude"),
                                      hourly_time_convention="accumulation_start" if risk == "hydric" else "provider_timestamp",
                                      units=payload["hourly_units"], hourly=series, simulated=False,
                                      payload_sha256=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                                      scope="Área de vigilancia de 5 km del nodo; confirmar cobertura en campo",
                                      spatial_limit="CAMS global: grilla aproximada de 45 km, no medición local" if risk == "health_air" else "Pronóstico de grilla, no medición local",
                                      attribution="Copernicus CAMS global vía Open-Meteo" if risk == "health_air" else "Open-Meteo")
                    inserted = await conn.fetchval("""
                        INSERT INTO predictions(org_id,device_id,device_name,latitude,longitude,horizon_hours,
                          issued_at,valid_from,valid_to,issuance_day,model_id,model_version,risk_index,
                          probability,threshold,warning,features,provenance,explanation,action,recorded_at,hazard)
                        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17::jsonb,$18::jsonb,$19::jsonb,$20,clock_timestamp(),$21)
                        ON CONFLICT(org_id,device_id,horizon_hours,issuance_day,model_version,hazard) DO NOTHING RETURNING id
                    """, org_id, device["id"], device["name"], device["lat"], device["lon"], hours,
                        issued_at, start, end, issued_at.date(), model_id, version, index, prob, threshold, warning,
                        json.dumps(features), json.dumps(provenance), json.dumps(reasons), action, risk)
                    created += int(inserted is not None)
                except ValueError as exc:
                    errors.append(dict(device_id=str(device["id"]), hazard=risk, horizon_hours=hours, detail=str(exc)))
            if created:
                await conn.execute("INSERT INTO audit_events(org_id,user_id,action,resource,metadata) VALUES($1,$2,'predictive_issue','prediction',$3::jsonb)",
                                   org_id, actor_id, json.dumps(dict(created=created, failed=len(errors))))
            return dict(created=created, skipped=skipped, errors=errors, message="Pronósticos archivados; sin activar respuestas automáticas")


async def dataset(org_id: UUID, days: int = 90, horizon: int | None = None, hazard: str = "fire") -> tuple[list[dict], list[dict], datetime]:
    now = await db.pool().fetchval("SELECT clock_timestamp()")
    since = now - timedelta(days=days)
    rows = await db.pool().fetch("""SELECT * FROM predictions WHERE org_id=$1 AND issued_at >= $2
        AND ($3::int IS NULL OR horizon_hours=$3) AND hazard=$4 ORDER BY issued_at LIMIT 10001""", org_id, since, horizon, hazard)
    observations = await db.pool().fetch("""SELECT * FROM predictive_observations WHERE org_id=$1
        AND end_at >= $2 AND start_at <= $3 AND hazard=$4 ORDER BY start_at LIMIT 10001""", org_id, since, now, hazard)
    if len(rows) > 10000 or len(observations) > 10000:
        raise HTTPException(413, "El período supera 10.000 registros; reducí los días de evaluación")
    return [decode(row) for row in rows], [dict(row) for row in observations], now


async def evaluate_org(org_id: UUID, days: int, horizon: int, hazard: str = "fire") -> dict:
    predictions, observations, now = await dataset(org_id, days, horizon, hazard)
    groups = {}
    for prediction in predictions:
        groups.setdefault(prediction["model_version"], []).append(prediction)
    if not groups:
        groups[baseline_version(hazard)] = []
    metrics = []
    for version, rows in groups.items():
        scope_start = min(row["issued_at"] for row in rows) if rows else now - timedelta(days=days)
        scoped = [obs for obs in observations if obs["outcome"] != "event" or obs["start_at"] >= scope_start]
        computed = await run_in_threadpool(evaluation, rows, scoped, now)
        metrics.append({"model_version": version, "scope_start": scope_start, **computed})
    models = await db.pool().fetch("SELECT * FROM predictive_models WHERE org_id=$1 AND horizon_hours=$2 AND hazard=$3 ORDER BY created_at DESC LIMIT 50", org_id, horizon, hazard)
    recent_features = [p["features"] for p in predictions if p["model_version"] == baseline_version(hazard) and p["issued_at"] >= now - timedelta(days=7)]
    return dict(generated_at=now, since=now - timedelta(days=days), horizon_hours=horizon, hazard=hazard, metrics=metrics,
                models=[{**decode(row), "drift": drift(recent_features, decode(row)["artifact"])} for row in models],
                labels_policy="Sin cobertura verificada no se asigna resultado negativo. Los eventos se registran independientemente de alertas.")


async def train_org(org_id: UUID, actor_id: UUID, days: int, horizon: int, hazard: str = "fire") -> dict:
    predictions, observations, now = await dataset(org_id, days, horizon, hazard)
    rows = []
    by_device = {}
    for obs in observations:
        by_device.setdefault(obs["device_id"], []).append(obs)
    for prediction in predictions:
        if prediction["model_version"] != baseline_version(hazard) or prediction["valid_to"] > now:
            continue
        label, _ = label_forecast(prediction, by_device.get(prediction["device_id"], []))
        if label is not None:
            rows.append({**prediction, "label": label})
    try:
        artifact, metrics = await run_in_threadpool(train_model, rows, horizon, hazard)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    version = f"{hazard}-logistic-v1-" + hashlib.sha256(json.dumps([artifact, metrics], sort_keys=True).encode()).hexdigest()[:16]
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("""INSERT INTO predictive_models(org_id,horizon_hours,version,artifact,evaluation,eligible,created_by,hazard)
              VALUES($1,$2,$3,$4::jsonb,$5::jsonb,$6,$7,$8) ON CONFLICT(org_id,version) DO NOTHING RETURNING *""",
              org_id, horizon, version, json.dumps(artifact), json.dumps(metrics), metrics["eligible"], actor_id, hazard)
            if row is None:
                row = await conn.fetchrow("SELECT * FROM predictive_models WHERE org_id=$1 AND version=$2", org_id, version)
            await conn.execute("INSERT INTO audit_events(org_id,user_id,action,resource,resource_id,metadata) VALUES($1,$2,'predictive_train','predictive_model',$3,$4::jsonb)",
                               org_id, actor_id, row["id"], json.dumps(dict(version=version, hazard=hazard, eligible=metrics["eligible"])))
    return decode(row)
