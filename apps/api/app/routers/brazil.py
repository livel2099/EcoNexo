"""Consulta autenticada de fuentes satelitales para Mato Grosso."""
import asyncio
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, Request

from ..brazil_alerts import fire_features, deforestation_features
from ..config import get_settings
from ..deps import CurrentUser, current_user
from ..rate_limit import enforce_rate_limit

router = APIRouter(prefix="/brasil/mato-grosso", tags=["brasil"])
_cache = None
_cached_at = 0.0
_lock = asyncio.Lock()


async def fires(client):
    settings = get_settings()
    key = settings.nasa_firms_key.strip()
    source = "NASA FIRMS"
    if not key or not settings.firms_inline_enabled:
        return {"source": source, "status": "not_configured", "message": "Configurar NASA_FIRMS_KEY y habilitar FIRMS_INLINE_ENABLED en el servidor.", "features": []}
    try:
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{settings.firms_source}/-61,-18.1,-50,-7.2/2"
        response = await client.get(url)
        response.raise_for_status()
        features, skipped = fire_features(response.text, settings.firms_source)
        return {"source": source, "status": "partial" if skipped else "ok", "features": features,
                "message": f"Últimos 2 días · {skipped} filas inválidas omitidas. Recorte con malla municipal simplificada IBGE."}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        # No propagar URLs ni excepciones que puedan revelar la MAP_KEY.
        return {"source": source, "status": "unavailable", "message": "No se pudo consultar FIRMS. Revisar conexión, cuota y credencial.", "features": []}


async def deter(client, layer, label, since):
    try:
        response = await client.get("https://terrabrasilis.dpi.inpe.br/geoserver/ows", params={
            "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": layer,
            "outputFormat": "application/json", "srsName": "EPSG:4326", "count": 1000,
            "sortBy": "view_date D",
            "CQL_FILTER": f"uf='MT' AND view_date >= '{since}' AND classname IN ('DESMATAMENTO_CR','DESMATAMENTO_VEG')",
        })
        response.raise_for_status()
        data = response.json()
        if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
            raise ValueError()
        features, skipped = deforestation_features(data["features"], label)
        matched = data.get("numberMatched", data.get("totalFeatures"))
        truncated = len(data["features"]) >= 1000 or (str(matched).isdigit() and int(matched) > len(data["features"]))
        return {"source": label, "status": "partial" if truncated or skipped else "ok", "features": features,
                "message": f"Desde {since} · fecha de observación, con demora de publicación." + (" Se alcanzó el límite de 1000 avisos; cobertura parcial." if truncated else "") + (f" {skipped} registros inválidos omitidos." if skipped else "")}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return {"source": label, "status": "unavailable", "message": "INPE no disponible. Reintentar más tarde.", "features": []}


@router.get("/alerts")
async def alerts(request: Request, user: CurrentUser = Depends(current_user)):
    await enforce_rate_limit(request, bucket="brasil-alerts", limit=12, window_seconds=60)
    global _cache, _cached_at
    async with _lock:
        if _cache is not None and time.monotonic() - _cached_at < 300:
            return _cache
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=30)).date().isoformat()
        async with httpx.AsyncClient(timeout=20) as client:
            sources = await asyncio.gather(fires(client),
                deter(client, "deter-amz:deter_amz", "INPE DETER · Amazonia", since),
                deter(client, "deter-cerrado-nb:deter_cerrado", "INPE DETER · Cerrado", since))
        _cache = {"queried_at": now.isoformat(), "sources": sources}
        _cached_at = time.monotonic()
        return _cache
