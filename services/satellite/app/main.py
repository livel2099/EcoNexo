"""satellite-service — ingesta programada de FIRMS + procesamiento OpenCV.

Cada FIRMS_POLL_SECONDS:
  1. Trae focos de calor de NASA FIRMS (o fixture) para Argentina.
  2. Procesa un raster satelital con OpenCV (deteccion de zonas de calor).
  3. Envia las detecciones al API core (/satellite/ingest) para correlacion.
"""
from __future__ import annotations

import asyncio
import logging
import os

import httpx

from .firms import fetch_detections
from .vision import analyze

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("econexo.satellite")

API_URL = os.getenv("API_URL", "http://localhost:8000")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
POLL = int(os.getenv("FIRMS_POLL_SECONDS", "900"))


async def cycle() -> None:
    detections = await fetch_detections(days=1)
    log.info("FIRMS: %d focos de calor", len(detections))

    vision = analyze()  # OpenCV sobre raster de muestra
    log.info("OpenCV: %d zonas de calor detectadas en el raster", len(vision["heat_zones"]))

    if not INTERNAL_SERVICE_TOKEN:
        log.error("INTERNAL_SERVICE_TOKEN no está configurado; se omite la ingesta")
        return

    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                f"{API_URL}/satellite/ingest",
                json={"detections": detections},
                headers={"X-Internal-Service-Token": INTERNAL_SERVICE_TOKEN},
            )
            r.raise_for_status()
            log.info("Ingesta al API: %s", r.json())
    except Exception as exc:
        log.warning("No se pudo ingestar al API: %s", exc)


async def main() -> None:
    log.info("satellite-service iniciado (poll cada %ds)", POLL)
    while True:
        try:
            await cycle()
        except Exception as exc:
            log.exception("cycle fallo: %s", exc)
        await asyncio.sleep(POLL)


if __name__ == "__main__":
    asyncio.run(main())
