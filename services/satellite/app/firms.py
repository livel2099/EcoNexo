"""Cliente NASA FIRMS (focos de calor). API real gratuita (key por email):
https://firms.modaps.eosdis.nasa.gov/api/  ->  MAP_KEY

Sin NASA_FIRMS_KEY devuelve una lista vacia. El fixture solo se usa cuando ALLOW_DEMO_SATELLITE_FIXTURES=true en desarrollo o demo.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

log = logging.getLogger("econexo.firms")

# BBox operacional de Misiones: min_lon,min_lat,max_lon,max_lat
MISIONES_BBOX = "-56.10,-28.20,-53.55,-25.45"
MISIONES_LIMITS = (-28.20, -56.10, -25.45, -53.55)
FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{bbox}/{days}"
FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "firms_sample.json"


MISIONES_POLYGON = [
    (-25.50, -54.64), (-25.70, -54.24), (-25.95, -53.92),
    (-26.25, -53.63), (-26.62, -53.70), (-27.02, -53.88),
    (-27.36, -54.20), (-27.62, -54.64), (-27.93, -55.12),
    (-28.18, -55.66), (-27.84, -55.86), (-27.37, -55.96),
    (-27.06, -55.72), (-26.70, -55.42), (-26.35, -55.08),
    (-25.98, -54.82), (-25.66, -54.68), (-25.50, -54.64),
]


def _inside_misiones(lat: float, lon: float) -> bool:
    south, west, north, east = MISIONES_LIMITS
    if not (south <= lat <= north and west <= lon <= east):
        return False
    inside = False
    j = len(MISIONES_POLYGON) - 1
    for i, (lat_i, lon_i) in enumerate(MISIONES_POLYGON):
        lat_j, lon_j = MISIONES_POLYGON[j]
        intersects = ((lon_i > lon) != (lon_j > lon)) and (
            lat < (lat_j - lat_i) * (lon - lon_i) / ((lon_j - lon_i) or 1e-12) + lat_i
        )
        if intersects:
            inside = not inside
        j = i
    return inside

def _conf_to_float(raw: str) -> float:
    raw = (raw or "").strip().lower()
    if raw in ("h", "high"):
        return 0.9
    if raw in ("n", "nominal"):
        return 0.7
    if raw in ("l", "low"):
        return 0.4
    try:
        return max(0.0, min(1.0, float(raw) / 100.0))
    except ValueError:
        return 0.7


def _normalize(row: dict) -> dict:
    date = row.get("acq_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    t = str(row.get("acq_time", "0000")).zfill(4)
    acquired = f"{date}T{t[:2]}:{t[2:]}:00+00:00"
    return {
        "source": "FIRMS_VIIRS",
        "lat": float(row["latitude"]),
        "lon": float(row["longitude"]),
        "brightness": float(row.get("bright_ti4") or row.get("brightness") or 0) or None,
        "confidence": _conf_to_float(str(row.get("confidence", "n"))),
        "frp": float(row.get("frp") or 0) or None,
        "acquired_at": acquired,
    }



def _load_fixture_recent() -> list[dict]:
    """Carga el fixture y sella acquired_at a minutos recientes (el fixture
    grabado representa detecciones en vivo, no datos historicos de 2024)."""
    from datetime import datetime, timedelta, timezone
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    out = []
    now = datetime.now(timezone.utc)
    for i, d in enumerate(data["detections"]):
        n = _normalize(d)
        n["acquired_at"] = (now - timedelta(minutes=5 + i * 7)).isoformat()
        if _inside_misiones(n["lat"], n["lon"]):
            out.append(n)
    return out

async def fetch_detections(days: int = 1) -> list[dict]:
    key = os.getenv("NASA_FIRMS_KEY", "").strip()
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    fixtures_enabled = os.getenv(
        "ALLOW_DEMO_SATELLITE_FIXTURES",
        "false" if environment in {"production", "prod"} else "true",
    ).strip().lower() in {"1", "true", "yes", "on"}
    if not key:
        if fixtures_enabled:
            log.warning("Sin NASA_FIRMS_KEY: usando fixture DEMO limitado a Misiones")
            return _load_fixture_recent()
        log.error("Sin NASA_FIRMS_KEY en producción: no se publican detecciones simuladas")
        return []

    url = FIRMS_URL.format(key=key, bbox=MISIONES_BBOX, days=days)
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(url)
            r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        detections = [_normalize(row) for row in reader]
        return [item for item in detections if _inside_misiones(item["lat"], item["lon"])]
    except Exception as exc:
        if fixtures_enabled:
            log.warning("FIRMS API falló (%s); se usa fixture DEMO", exc)
            return _load_fixture_recent()
        log.error("FIRMS API falló (%s); producción queda sin detecciones hasta recuperar la fuente", exc)
        return []
