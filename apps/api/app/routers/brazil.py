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
_last_good = {}


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


def source_failure(exc):
    if isinstance(exc, httpx.TimeoutException):
        return "INPE agotó el tiempo de espera."
    if isinstance(exc, httpx.HTTPStatusError):
        return f"INPE respondió HTTP {exc.response.status_code}."
    if isinstance(exc, httpx.ConnectError):
        return "No se pudo conectar con INPE (red, DNS o certificado)."
    return "INPE devolvió una respuesta inválida."


async def deter(client, layer, label, since):
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": layer,
        "outputFormat": "application/json", "srsName": "EPSG:4326", "count": 1000,
        "sortBy": "view_date D",
        "CQL_FILTER": f"uf='MT' AND view_date >= '{since}' AND classname IN ('DESMATAMENTO_CR','DESMATAMENTO_VEG','CICATRIZ_DE_QUEIMADA')",
    }
    reason = ""
    # Endpoint alternativo del mismo proveedor y menor respuesta si falla el primero.
    for endpoint, count in [
        ("https://terrabrasilis.dpi.inpe.br/geoserver/ows", 1000),
        (f"https://terrabrasilis.dpi.inpe.br/geoserver/{layer.split(':')[0]}/wfs", 250),
    ]:
        try:
            response = await client.get(endpoint, params={**params, "count": count},
                                        timeout=12, follow_redirects=True)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
                raise ValueError()
            features, skipped = deforestation_features(data["features"], label)
            matched = data.get("numberMatched", data.get("totalFeatures"))
            truncated = len(data["features"]) >= count or (str(matched).isdigit() and int(matched) > len(data["features"]))
            return {"source": label, "status": "partial" if truncated or skipped else "ok", "features": features,
                    "queried_at": datetime.now(timezone.utc).isoformat(),
                    "message": f"Desde {since} · deforestación y cicatrices de quema; fecha de observación, con demora de publicación."
                    + (f" Se muestran hasta {count} avisos recientes; cobertura parcial." if truncated else "")
                    + (f" {skipped} registros inválidos omitidos." if skipped else "")}
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            reason = source_failure(exc)
    return {"source": label, "status": "unavailable", "message": reason + " Reintentar la actualización.", "features": []}


def preserve_last_good(sources, now):
    result = []
    for source in sources:
        name = source["source"]
        if source["status"] in {"ok", "partial"}:
            source = {**source, "queried_at": source.get("queried_at", now.isoformat())}
            _last_good[name] = (now, source)
        elif source["status"] == "unavailable" and name in _last_good:
            stamp, previous = _last_good[name]
            if now - stamp < timedelta(hours=24):
                source = {**previous, "status": "stale",
                          "message": source["message"] + " Se conserva la consulta anterior, desactualizada. " + previous["message"]}
        result.append(source)
    return result


@router.get("/alerts")
async def alerts(request: Request, refresh: bool = False, user: CurrentUser = Depends(current_user)):
    await enforce_rate_limit(request, bucket="brasil-alerts", limit=12, window_seconds=60)
    global _cache, _cached_at
    async with _lock:
        ttl = 300 if _cache and all(s["status"] in {"ok", "partial"} for s in _cache["sources"]) else 30
        if _cache is not None and time.monotonic() - _cached_at < (min(ttl, 30) if refresh else ttl):
            return _cache
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=30)).date().isoformat()
        async with httpx.AsyncClient(timeout=20) as client:
            sources = await asyncio.gather(fires(client),
                deter(client, "deter-amz:deter_amz", "INPE DETER · Amazonia", since),
                deter(client, "deter-cerrado-nb:deter_cerrado", "INPE DETER · Cerrado", since))
        _cache = {"queried_at": now.isoformat(), "sources": preserve_last_good(sources, now)}
        _cached_at = time.monotonic()
        return _cache
