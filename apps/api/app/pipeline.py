"""Pipeline de creacion de alertas con correlacion multi-fuente.

Dado un evento disparador (regla sobre sensor, deteccion satelital o reporte
ciudadano), reune las fuentes cercanas via PostGIS (ST_DWithin), calcula la
confianza real combinando el score de anomalia (anomaly-service) con la
correlacion espacial y la reputacion ciudadana, persiste la alerta y sus
fuentes, y publica en el bus MQTT para el feed WebSocket y notify-service.
"""
from __future__ import annotations

import logging
from uuid import UUID

import httpx

from . import db
from .config import get_settings
from .correlation import Source, correlate
from .ws import publish

log = logging.getLogger("econexo.pipeline")


async def anomaly_score(device_id: str, variable: str, value: float) -> float:
    """Consulta el anomaly-service (PyTorch). Si no responde, degrada a 0.5."""
    url = get_settings().anomaly_service_url
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.post(f"{url}/score", json={
                "device_id": device_id, "variable": variable, "value": value,
            })
            r.raise_for_status()
            return float(r.json()["score"])
    except Exception as exc:
        log.warning("anomaly-service no disponible: %s", exc)
        return 0.5


async def gather_sources(org_id: UUID, lat: float, lon: float, radius_m: float) -> list[Source]:
    """Reune sensores anomalos, detecciones satelitales y reportes ciudadanos
    dentro del radio, como fuentes ponderables para la correlacion."""
    p = db.pool()
    sources: list[Source] = []

    # detecciones satelitales recientes (< 6h)
    sat = await p.fetch(
        """
        SELECT ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon,
               COALESCE(confidence, 0.7) AS score
        FROM satellite_detections
        WHERE ST_DWithin(location, ST_MakePoint($2,$1)::geography, $3)
          AND acquired_at > now() - interval '6 hours'
          AND (org_id = $4 OR org_id IS NULL)
        """,
        lat, lon, radius_m, org_id,
    )
    sources += [Source("satelite", r["lat"], r["lon"], float(r["score"])) for r in sat]

    # reportes ciudadanos pendientes/verificados recientes (< 12h)
    rep = await p.fetch(
        """
        SELECT ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon,
               COALESCE(reputation_score, 0.5) AS score
        FROM citizen_reports
        WHERE org_id = $4 AND status <> 'rechazado'
          AND ST_DWithin(location, ST_MakePoint($2,$1)::geography, $3)
          AND created_at > now() - interval '12 hours'
        """,
        lat, lon, radius_m, org_id,
    )
    sources += [Source("ciudadano", r["lat"], r["lon"], float(r["score"])) for r in rep]
    return sources


async def create_alert(
    org_id: UUID,
    alert_type: str,
    severity: str,
    lat: float,
    lon: float,
    title: str,
    sensor_source: Source | None = None,
    device_id: str | None = None,
    rule_id: str | None = None,
    radius_m: float = 2000.0,
) -> dict:
    """Crea una alerta correlacionada y la publica en el bus."""
    p = db.pool()
    sources = await gather_sources(org_id, lat, lon, radius_m)
    if sensor_source is not None:
        sources.append(sensor_source)

    result = correlate(lat, lon, sources, radius_m)

    row = await p.fetchrow(
        """
        INSERT INTO alerts (org_id, type, severity, location, confidence, title, rule_id, device_id)
        VALUES ($1,$2,$3, ST_MakePoint($5,$4)::geography, $6, $7, $8, $9)
        RETURNING id, detected_at
        """,
        org_id, alert_type, severity, lat, lon, result.confidence, title,
        rule_id, device_id,
    )
    alert_id = row["id"]

    for src in result.contributing:
        await p.execute(
            "INSERT INTO alert_sources (alert_id, source_type, weight, detail) "
            "VALUES ($1,$2,$3,$4::jsonb)",
            alert_id, src.source_type, result.weights.get(src.source_type, 0.0),
            f'{{"lat": {src.lat}, "lon": {src.lon}, "score": {src.score}}}',
        )
    await p.execute(
        "INSERT INTO alert_events (alert_id, action, payload) VALUES ($1,'crear',$2::jsonb)",
        alert_id, f'{{"confidence": {result.confidence}}}',
    )

    payload = {
        "id": str(alert_id), "type": alert_type, "severity": severity,
        "lat": lat, "lon": lon, "confidence": result.confidence, "title": title,
        "detected_at": str(row["detected_at"]),
        "source_types": sorted({s.source_type for s in result.contributing}),
    }
    await publish(f"econexo/internal/{org_id}/alerts", payload)
    log.info("Alerta %s creada (conf=%.2f, fuentes=%s)", alert_id, result.confidence, payload["source_types"])
    return payload
