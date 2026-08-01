"""Ingesta de detecciones satelitales (FIRMS/Copernicus) y capa de mapa."""
from __future__ import annotations

from datetime import datetime
import hashlib
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
        dedup_source = f"{d.source}|{d.lat:.5f}|{d.lon:.5f}|{d.acquired_at.isoformat()}"
        dedup_key = hashlib.sha256(dedup_source.encode("utf-8")).hexdigest()
        inserted = await p.fetchrow(
            """
            INSERT INTO satellite_detections
                (org_id,source,location,brightness,confidence,frp,acquired_at,raw,dedup_key)
            VALUES ($1,$2,ST_MakePoint($4,$3)::geography,$5,$6,$7,$8,$9::jsonb,$10)
            ON CONFLICT (dedup_key) DO UPDATE SET
              brightness=EXCLUDED.brightness, confidence=EXCLUDED.confidence,
              frp=EXCLUDED.frp, raw=EXCLUDED.raw
            RETURNING id, (xmax = 0) AS inserted
            """,
            d.org_id,d.source,d.lat,d.lon,d.brightness,d.confidence,d.frp,
            d.acquired_at,"{}",dedup_key,
        )
        if inserted is None:
            continue
        if inserted["inserted"]:
            created += 1
        # correlacion con zona de riesgo de incendio
        zones = await p.fetch(
            """
            SELECT org_id FROM risk_zones
            WHERE kind IN ('incendio','general')
              AND ($3::uuid IS NULL OR org_id=$3)
              AND ST_Covers(area::geometry, ST_SetSRID(ST_MakePoint($2,$1),4326))
            """,
            d.lat,d.lon,d.org_id,
        )
        if (d.confidence or 0) >= 0.6:
            for zone in zones:
                duplicate = await p.fetchval(
                    """
                    SELECT EXISTS(
                      SELECT 1 FROM alerts
                      WHERE org_id=$1 AND type='incendio'
                        AND detected_at > now() - interval '6 hours'
                        AND ST_DWithin(location,ST_MakePoint($3,$2)::geography,1500)
                    )
                    """,
                    zone["org_id"],d.lat,d.lon,
                )
                if duplicate:
                    continue
                await create_alert(
                    org_id=zone["org_id"],alert_type="incendio",
                    severity="critica" if (d.confidence or 0) >= 0.85 else "alta",
                    lat=d.lat,lon=d.lon,title="Foco de calor detectado por satelite",
                    sensor_source=Source("satelite",d.lat,d.lon,d.confidence or 0.7),
                    radius_m=5000,
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
