"""Respaldo gratuito de lecturas actuales: MET Norway Locationforecast 2.0.

Open-Meteo limita por IP de salida y en Render esa IP es compartida, asi que el
429 llega sin que EcoNexo consulte de mas. MET Norway publica el mismo tipo de
dato modelado sin clave, con otra infraestructura y otro cupo.

Datos del Instituto Meteorologico de Noruega bajo CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/). Su ToS
(https://api.met.no/doc/TermsOfService) exige identificarse con User-Agent,
truncar las coordenadas a 4 decimales y no repetir la consulta antes del
Expires que devuelve la respuesta.

No cubre todas las variables de Open-Meteo: no hay humedad de suelo, y la
lluvia que publica es la esperada en la proxima hora, no la caida en la ultima,
asi que no se guarda en lugar de una medicion con otro significado.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from collections.abc import Sequence
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from . import weather_cache
from .config import get_settings

URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"
ATTRIBUTION = "MET Norway (api.met.no), CC BY 4.0"
# Su modelo publica valores horarios: repreguntar antes no trae nada nuevo.
MIN_TTL_SECONDS = 900.0
MAX_TTL_SECONDS = 3600.0
# Unidades que espera el resto del pipeline, en los nombres de MET Norway.
EXPECTED_UNITS = {"air_temperature": "celsius", "relative_humidity": "%", "wind_speed": "m/s"}


class MetNoError(RuntimeError):
    pass


def vapour_pressure_deficit_kpa(temp_c: float, humidity: float) -> float:
    """VPD en kPa (FAO-56 ec. 11 y 17), la unidad que publica Open-Meteo."""
    saturation = 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))
    return round(max(0.0, saturation * (1 - humidity / 100)), 4)


def _numero(valor: Any) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return float(valor) if math.isfinite(valor) else None


def parse_current(payload: Any) -> dict[str, float]:
    """Primera hora de la serie: es la que corresponde al momento actual."""
    propiedades = payload.get("properties") if isinstance(payload, dict) else None
    if not isinstance(propiedades, dict):
        raise MetNoError("MET Norway devolvio una respuesta sin propiedades")
    unidades = (propiedades.get("meta") or {}).get("units") or {}
    if any(unidades.get(nombre) != unidad for nombre, unidad in EXPECTED_UNITS.items()):
        raise MetNoError("MET Norway devolvio unidades ausentes o no compatibles")
    serie = propiedades.get("timeseries") or []
    if not serie:
        raise MetNoError("MET Norway no devolvio horas para la coordenada")
    detalles = ((serie[0].get("data") or {}).get("instant") or {}).get("details") or {}

    lecturas: dict[str, float] = {}
    temp = _numero(detalles.get("air_temperature"))
    humedad = _numero(detalles.get("relative_humidity"))
    viento = _numero(detalles.get("wind_speed"))
    rafaga = _numero(detalles.get("wind_speed_of_gust"))
    if temp is not None:
        lecturas["temp"] = round(temp, 4)
    if humedad is not None and 0 <= humedad <= 100:
        lecturas["humidity"] = round(humedad, 4)
    # Open-Meteo publica el viento en km/h; MET Norway en m/s.
    if viento is not None and viento >= 0:
        lecturas["wind_speed"] = round(viento * 3.6, 4)
    if rafaga is not None and rafaga >= 0 and unidades.get("wind_speed_of_gust") == "m/s":
        lecturas["wind_gust"] = round(rafaga * 3.6, 4)
    if temp is not None and "humidity" in lecturas:
        lecturas["vpd"] = vapour_pressure_deficit_kpa(temp, lecturas["humidity"])
    if not lecturas:
        raise MetNoError("MET Norway no devolvio variables utilizables")
    return lecturas


def cache_ttl(expires: str | None) -> float:
    """Su ToS pide no repetir la consulta antes del Expires de la respuesta."""
    try:
        restante = (parsedate_to_datetime(expires) - datetime.now(timezone.utc)).total_seconds()
    except (TypeError, ValueError, OverflowError):
        return MIN_TTL_SECONDS
    if not math.isfinite(restante):
        return MIN_TTL_SECONDS
    return min(MAX_TTL_SECONDS, max(MIN_TTL_SECONDS, restante))


async def fetch_current_batch(points: Sequence[tuple[float, float]]) -> list[dict[str, float]]:
    """Una consulta por coordenada: la API no acepta listas de ubicaciones."""
    if not points:
        return []
    settings = get_settings()
    agente = settings.met_no_user_agent.strip()
    if not agente:
        # Su ToS bloquea sin identificacion, y prohibe cadenas inventadas.
        raise MetNoError("Falta MET_NO_USER_AGENT con nombre y contacto del servicio")
    cabeceras = {"User-Agent": agente, "Accept": "application/json"}
    resultado: list[dict[str, float]] = []
    async with httpx.AsyncClient(timeout=settings.pipeline_http_timeout_seconds,
                                 headers=cabeceras, follow_redirects=True) as client:
        for lat, lon in points:
            # Su ToS rechaza con 403 las coordenadas de 5 o mas decimales.
            params = {"lat": f"{lat:.4f}", "lon": f"{lon:.4f}"}
            clave = "metno:" + hashlib.sha256(repr(sorted(params.items())).encode()).hexdigest()
            payload = await weather_cache.read(clave)
            if payload is not None:
                resultado.append(parse_current(payload))
                continue
            try:
                response = await client.get(URL, params=params)
            except httpx.HTTPError as exc:
                raise MetNoError(f"No se pudo consultar MET Norway ({type(exc).__name__})") from exc
            if response.status_code != 200:
                raise MetNoError(f"MET Norway respondio HTTP {response.status_code}")
            try:
                payload = response.json()
            except ValueError as exc:
                raise MetNoError("MET Norway devolvio un cuerpo que no es JSON") from exc
            lecturas = parse_current(payload)  # No cachear un cuerpo que no sirve.
            await weather_cache.write(clave, payload, cache_ttl(response.headers.get("expires")))
            resultado.append(lecturas)
    return resultado
