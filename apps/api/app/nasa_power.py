"""NASA POWER daily histories, with locally estimated FAO-56 reference ET0.

References: power.larc.nasa.gov/docs/services/api/temporal/daily/
and FAO Irrigation and Drainage Paper 56, equations 6, 11, 13, 21-25, 35-40.
Daily means use NASA local solar time (LST), not Argentina civil time.
"""
from __future__ import annotations
import asyncio
import calendar
import hashlib
import math
from datetime import date, datetime, timedelta, timezone

import httpx
from . import weather_cache
from .open_meteo_http import retry_seconds

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = "T2M_MAX,T2M_MIN,RH2M,WS2M,PS,ALLSKY_SFC_SW_DWN,PRECTOTCORR"
_lock = asyncio.Lock()


class NasaPowerError(RuntimeError):
    pass


def et0_fao56(day: date, lat: float, elevation: float, tmax: float, tmin: float,
              rh: float, wind: float, pressure: float, solar: float) -> float:
    """mm/day; C, % RHmean (FAO eq.19), m/s at 2 m, kPa, MJ/m2/day; G=0."""
    temp = (tmax + tmin) / 2
    def saturation(t):
        return 0.6108 * math.exp(17.27 * t / (t + 237.3))
    es = (saturation(tmax) + saturation(tmin)) / 2
    ea = rh / 100 * es
    delta = 4098 * saturation(temp) / (temp + 237.3) ** 2
    gamma = 0.000665 * pressure
    j = day.timetuple().tm_yday
    phi = math.radians(lat)
    dr = 1 + 0.033 * math.cos(2 * math.pi * j / 365)
    declination = 0.409 * math.sin(2 * math.pi * j / 365 - 1.39)
    sunset = math.acos(max(-1, min(1, -math.tan(phi) * math.tan(declination))))
    ra = 24 * 60 / math.pi * 0.0820 * dr * (
        sunset * math.sin(phi) * math.sin(declination)
        + math.cos(phi) * math.cos(declination) * math.sin(sunset))
    clear_sky = (0.75 + 0.00002 * elevation) * ra
    if clear_sky <= 0:
        raise ValueError("Radiacion de cielo despejado no positiva")
    # Bound cloud factor to avoid negative outgoing radiation on very cloudy days.
    ratio = max(0.3, min(1.0, solar / clear_sky))
    longwave = 4.903e-9 * ((tmax + 273.16)**4 + (tmin + 273.16)**4) / 2 * (
        0.34 - 0.14 * math.sqrt(ea)) * (1.35 * ratio - 0.35)
    net = 0.77 * solar - longwave
    return max(0.0, (0.408 * delta * net + gamma * 900 / (temp + 273) * wind * (es - ea))
               / (delta + gamma * (1 + 0.34 * wind)))


def parse_daily(payload: dict, lat: float) -> list[dict]:
    data = payload.get("properties", {}).get("parameter", {})
    metadata = payload.get("parameters", {})
    expected = {"T2M_MAX": {"C"}, "T2M_MIN": {"C"}, "RH2M": {"%"},
                "WS2M": {"m/s"}, "PS": {"kPa"}, "PRECTOTCORR": {"mm/day"},
                "ALLSKY_SFC_SW_DWN": {"MJ/m^2/day", "kW-hr/m^2/day", "kWh/m^2/day"}}
    if any(metadata.get(key, {}).get("units") not in units for key, units in expected.items()):
        raise NasaPowerError("NASA POWER devolvio unidades ausentes o no compatibles")
    coordinates = payload.get("geometry", {}).get("coordinates", [])
    if len(coordinates) < 3 or not isinstance(coordinates[2], (int, float)) or not math.isfinite(coordinates[2]):
        raise NasaPowerError("NASA POWER no devolvio elevacion valida")
    elevation = coordinates[2]
    fill = payload.get("header", {}).get("fill_value", -999)
    if elevation == fill:
        raise NasaPowerError("NASA POWER no devolvio elevacion valida")
    rows = []
    for stamp in sorted(data.get("T2M_MAX", {})):
        values = [data.get(key, {}).get(stamp) for key in PARAMETERS.split(",")]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v == fill or v == -999 for v in values):
            continue
        tmax, tmin, rh, wind, pressure, solar, rain = values
        if not (-90 <= tmin <= tmax <= 65 and 0 <= rh <= 100 and wind >= 0 and 0 < pressure < 120 and solar >= 0 and rain >= 0):
            continue
        if metadata["ALLSKY_SFC_SW_DWN"]["units"] != "MJ/m^2/day":
            solar *= 3.6
        day = datetime.strptime(stamp, "%Y%m%d").date()
        rows.append({"day": day, "tmax": tmax, "tmin": tmin, "precipitation_mm": rain,
                     "et0_mm": round(et0_fao56(day, lat, elevation, tmax, tmin, rh, wind, pressure, solar), 3),
                     "source": "nasa-power", "et0_method": "FAO-56 Penman-Monteith, RH media", "time_standard": "LST"})
    return rows


async def fetch_history(lat: float, lon: float, start: date, end: date) -> list[dict]:
    if start > end:
        return []
    result = []
    month = start.replace(day=1)
    async with _lock:
        async with httpx.AsyncClient(timeout=45) as client:
            while month <= end:
                last = date(month.year, month.month, calendar.monthrange(month.year, month.month)[1])
                params = {"parameters": PARAMETERS, "community": "AG", "latitude": f"{lat:.4f}",
                          "longitude": f"{lon:.4f}", "start": month.strftime("%Y%m%d"),
                          "end": min(last, end).strftime("%Y%m%d"), "format": "JSON", "time-standard": "LST"}
                key = "nasa:" + hashlib.sha256(repr(sorted(params.items())).encode()).hexdigest()
                payload = await weather_cache.read(key)
                if payload is None:
                    paused = await weather_cache.read("nasa:cooldown")
                    if paused is not None:
                        raise NasaPowerError("NASA POWER limita temporalmente las consultas; reintenta mas tarde")
                    try:
                        response = await client.get(URL, params=params)
                        if response.status_code == 429:
                            await weather_cache.write("nasa:cooldown", {"paused": True}, retry_seconds(response.headers.get("retry-after")))
                        if response.status_code != 200:
                            raise NasaPowerError(f"NASA POWER respondio HTTP {response.status_code}")
                        payload = response.json()
                        rows = parse_daily(payload, lat)
                    except (httpx.HTTPError, ValueError) as exc:
                        raise NasaPowerError(f"No se pudo consultar NASA POWER ({type(exc).__name__})") from exc
                    complete = len(rows) == (min(last, end) - month).days + 1
                    await weather_cache.write(key, payload, 30 * 86400 if complete and last < end else 3600)
                else:
                    rows = parse_daily(payload, lat)
                result.extend(row for row in rows if start <= row["day"] <= end)
                month = last + timedelta(days=1)
    if not result:
        raise NasaPowerError("NASA POWER no devolvio dias completos para el periodo solicitado")
    return result
