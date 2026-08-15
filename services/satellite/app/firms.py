"""Cliente NASA FIRMS (focos de calor). API real gratuita (key por email):
https://firms.modaps.eosdis.nasa.gov/api/  ->  MAP_KEY

Si NASA_FIRMS_KEY no esta seteada, usa el fixture grabado (fixtures/firms_sample.json).
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

# BBox aproximado de Argentina: min_lon,min_lat,max_lon,max_lat
ARGENTINA_BBOX = "-73.6,-55.1,-53.6,-21.8"
FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{bbox}/{days}"
FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "firms_sample.json"


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
        out.append(n)
    return out

async def fetch_detections(days: int = 1) -> list[dict]:
    key = os.getenv("NASA_FIRMS_KEY", "").strip()
    if not key:
        log.info("Sin NASA_FIRMS_KEY: usando fixture grabado")
        return _load_fixture_recent()

    url = FIRMS_URL.format(key=key, bbox=ARGENTINA_BBOX, days=days)
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(url)
            r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        return [_normalize(row) for row in reader]
    except Exception as exc:
        log.warning("FIRMS API fallo (%s), usando fixture", exc)
        return _load_fixture_recent()
