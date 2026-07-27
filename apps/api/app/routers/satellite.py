"""Ingesta de detecciones satelitales (FIRMS/Copernicus) y capa de mapa."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import db
from ..correlation import Source
from ..deps import CurrentUser, current_user, internal_service
from ..pipeline import create_alert

router = APIRouter(prefix="/satellite", tags=["satellite"])


class Detection(BaseModel):
    source: str
    lat: float
    lon: float
    brightness: float | None = None
    confidence: float | None = None
    frp: float | None = None
    acquired_at: datetime
    org_id: UUID | None = None


class IngestIn(BaseModel):
    detections: list[Detection]


@router.post("/ingest", dependencies=[Depends(internal_service)])
async def ingest(body: IngestIn) -> dict:
    """Interno: satellite-service publica detecciones. Las de alta confianza
    dentro de una zona de riesgo disparan el pipeline de alertas (incendio)."""
    p = db.pool()
    created = 0
    alerts = 0
    ignored_external = 0
    for d in body.detections:
        inside_misiones = await p.fetchval(
            "SELECT econexo_inside_misiones(ST_MakePoint($2,$1)::geography)",
            d.lat,
            d.lon,
        )
        if not inside_misiones:
            ignored_external += 1
            continue
        await p.execute(
            """
            INSERT INTO satellite_detections
                (org_id, source, location, brightness, confidence, frp, acquired_at, raw)
            VALUES ($1,$2, ST_MakePoint($4,$3)::geography, $5,$6,$7,$8,$9::jsonb)
            """,
            d.org_id, d.source, d.lat, d.lon, d.brightness, d.confidence, d.frp,
            d.acquired_at, "{}",
        )
        created += 1
        # correlacion con zona de riesgo de incendio
        zone = await p.fetchrow(
            """
            SELECT org_id FROM risk_zones
            WHERE kind='incendio' AND ST_Contains(area::geometry, ST_SetSRID(ST_MakePoint($2,$1), 4326))
            LIMIT 1
            """,
            d.lat, d.lon,
        )
        if zone and (d.confidence or 0) >= 0.6:
            await create_alert(
                org_id=zone["org_id"], alert_type="incendio", severity="alta",
                lat=d.lat, lon=d.lon, title="Foco de calor detectado por satelite",
                sensor_source=Source("satelite", d.lat, d.lon, d.confidence or 0.7),
            )
            alerts += 1
    return {"ingested": created, "alerts_triggered": alerts, "ignored_outside_misiones": ignored_external}


@router.get("/detections")
async def detections(hours: int = 24, user: CurrentUser = Depends(current_user)) -> list[dict]:
    rows = await db.pool().fetch(
        """
        SELECT id, source, ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon,
               brightness, confidence, frp, acquired_at
        FROM satellite_detections
        WHERE (org_id=$1 OR org_id IS NULL)
          AND acquired_at > now() - ($2 || ' hours')::interval
          AND econexo_inside_misiones(location)
        ORDER BY acquired_at DESC
        """,
        user.org_id, str(hours),
    )
    return [dict(r) | {"lat": r["lat"], "lon": r["lon"], "acquired_at": str(r["acquired_at"])} for r in rows]
