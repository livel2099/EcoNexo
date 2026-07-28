"""Integracion segura con Copernicus Data Space Ecosystem.

El modo predeterminado usa Sentinel Hub Process API con OAuth2 client credentials,
por lo que no necesita una configuracion WMS por organizacion. WMS permanece como
fallback compatible para organizaciones que ya tengan un INSTANCE_ID propio.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Mapping
from urllib.parse import urlparse, urlunparse

import httpx

from .config import Settings, get_settings

CopernicusLayer = Literal["TRUE_COLOR", "NDVI", "MOISTURE_INDEX", "NBR_RAW"]
CopernicusProvider = Literal["process_api", "wms", "none"]

MISIONES_BBOX = (-56.10, -28.20, -53.55, -25.45)  # west, south, east, north
WMS_PREFIX = "/ogc/wms/"
ALLOWED_WMS_HOST = "sh.dataspace.copernicus.eu"


class CopernicusError(RuntimeError):
    """Error operacional de Copernicus que puede mostrarse sin filtrar secretos."""


@dataclass(frozen=True)
class CopernicusResolution:
    provider: CopernicusProvider
    configured: bool
    process_configured: bool
    wms_configured: bool
    effective_wms_url: str | None
    system_default: bool


@dataclass
class _TokenState:
    token: str = ""
    client_id: str = ""
    expires_at: float = 0.0


_token_state = _TokenState()
_token_lock = asyncio.Lock()
_image_cache: dict[str, tuple[float, bytes]] = {}
_image_cache_lock = asyncio.Lock()


def canonical_wms_url(raw: str | None) -> str | None:
    """Normaliza una URL oficial WMS y elimina query/fragment.

    Solo se acepta el host oficial y un INSTANCE_ID simple para evitar SSRF.
    """
    value = (raw or "").strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_WMS_HOST:
        raise ValueError(
            "La URL WMS debe usar HTTPS y el dominio oficial sh.dataspace.copernicus.eu"
        )
    if not parsed.path.startswith(WMS_PREFIX):
        raise ValueError(
            "Usá la URL https://sh.dataspace.copernicus.eu/ogc/wms/INSTANCE_ID"
        )
    instance_id = parsed.path.removeprefix(WMS_PREFIX).strip("/")
    if (
        not instance_id
        or instance_id.upper() == "INSTANCE_ID"
        or any(char in instance_id for char in "<>/?#")
    ):
        raise ValueError("Reemplazá INSTANCE_ID por el identificador real de tu instancia")
    return urlunparse(("https", ALLOWED_WMS_HOST, f"{WMS_PREFIX}{instance_id}", "", "", ""))


def system_wms_url(settings: Settings | None = None) -> str | None:
    settings = settings or get_settings()
    explicit = canonical_wms_url(settings.copernicus_wms_url)
    if explicit:
        return explicit
    instance_id = settings.copernicus_instance_id.strip()
    if not instance_id:
        return None
    return canonical_wms_url(f"https://{ALLOWED_WMS_HOST}{WMS_PREFIX}{instance_id}")


def resolve_provider(
    row: Mapping[str, Any] | None,
    settings: Settings | None = None,
) -> CopernicusResolution:
    """Resuelve proveedor efectivo sin exponer credenciales."""
    settings = settings or get_settings()
    enabled = bool((row or {}).get("copernicus_enabled", settings.copernicus_enabled_by_default))
    use_system = bool((row or {}).get("copernicus_use_system_default", True))
    org_wms = canonical_wms_url((row or {}).get("copernicus_wms_url"))
    global_wms = system_wms_url(settings)
    process_configured = settings.copernicus_process_configured
    wms_configured = bool(org_wms or global_wms)

    if not enabled:
        return CopernicusResolution(
            provider="none",
            configured=False,
            process_configured=process_configured,
            wms_configured=wms_configured,
            effective_wms_url=None,
            system_default=use_system,
        )

    requested_mode = settings.copernicus_mode_normalized
    if use_system:
        if requested_mode == "process_api" and process_configured:
            return CopernicusResolution(
                provider="process_api",
                configured=True,
                process_configured=True,
                wms_configured=wms_configured,
                effective_wms_url=None,
                system_default=True,
            )
        if requested_mode == "wms" and global_wms:
            return CopernicusResolution(
                provider="wms",
                configured=True,
                process_configured=process_configured,
                wms_configured=True,
                effective_wms_url=global_wms,
                system_default=True,
            )

    if org_wms:
        return CopernicusResolution(
            provider="wms",
            configured=True,
            process_configured=process_configured,
            wms_configured=True,
            effective_wms_url=org_wms,
            system_default=False,
        )

    # Fallback tolerante: si el modo pedido no tiene credenciales, usar el otro.
    if process_configured:
        return CopernicusResolution(
            provider="process_api",
            configured=True,
            process_configured=True,
            wms_configured=wms_configured,
            effective_wms_url=None,
            system_default=True,
        )
    if global_wms:
        return CopernicusResolution(
            provider="wms",
            configured=True,
            process_configured=False,
            wms_configured=True,
            effective_wms_url=global_wms,
            system_default=True,
        )

    return CopernicusResolution(
        provider="none",
        configured=False,
        process_configured=False,
        wms_configured=False,
        effective_wms_url=None,
        system_default=use_system,
    )


def _rgba_setup(bands: list[str]) -> str:
    band_list = ", ".join(json.dumps(band) for band in [*bands, "dataMask"])
    return f"""//VERSION=3
function setup() {{
  return {{
    input: [{{ bands: [{band_list}], units: \"REFLECTANCE\" }}],
    output: {{ bands: 4, sampleType: \"AUTO\" }}
  }};
}}
function clamp01(value) {{ return Math.max(0, Math.min(1, value)); }}
"""


EVALSCRIPTS: dict[CopernicusLayer, str] = {
    "TRUE_COLOR": _rgba_setup(["B02", "B03", "B04"]) + """
function evaluatePixel(sample) {
  const gain = 2.5;
  return [clamp01(gain * sample.B04), clamp01(gain * sample.B03), clamp01(gain * sample.B02), sample.dataMask];
}
""",
    "NDVI": _rgba_setup(["B04", "B08"]) + """
function evaluatePixel(sample) {
  const denominator = sample.B08 + sample.B04;
  const value = denominator === 0 ? 0 : (sample.B08 - sample.B04) / denominator;
  let rgb;
  if (value < -0.1) rgb = [0.12, 0.20, 0.55];
  else if (value < 0.1) rgb = [0.75, 0.66, 0.45];
  else if (value < 0.3) rgb = [0.86, 0.84, 0.36];
  else if (value < 0.5) rgb = [0.48, 0.73, 0.30];
  else if (value < 0.7) rgb = [0.18, 0.55, 0.20];
  else rgb = [0.04, 0.31, 0.13];
  return [rgb[0], rgb[1], rgb[2], sample.dataMask];
}
""",
    # NDMI = (NIR - SWIR1) / (NIR + SWIR1), indicador de humedad vegetal/superficial.
    "MOISTURE_INDEX": _rgba_setup(["B08", "B11"]) + """
function evaluatePixel(sample) {
  const denominator = sample.B08 + sample.B11;
  const value = denominator === 0 ? 0 : (sample.B08 - sample.B11) / denominator;
  let rgb;
  if (value < -0.4) rgb = [0.55, 0.25, 0.10];
  else if (value < -0.1) rgb = [0.78, 0.52, 0.22];
  else if (value < 0.1) rgb = [0.88, 0.80, 0.48];
  else if (value < 0.3) rgb = [0.45, 0.78, 0.72];
  else if (value < 0.5) rgb = [0.16, 0.58, 0.80];
  else rgb = [0.05, 0.26, 0.62];
  return [rgb[0], rgb[1], rgb[2], sample.dataMask];
}
""",
    # NBR = (NIR - SWIR2) / (NIR + SWIR2), indicador de severidad/huella de quema.
    "NBR_RAW": _rgba_setup(["B08", "B12"]) + """
function evaluatePixel(sample) {
  const denominator = sample.B08 + sample.B12;
  const value = denominator === 0 ? 0 : (sample.B08 - sample.B12) / denominator;
  let rgb;
  if (value < -0.2) rgb = [0.35, 0.00, 0.00];
  else if (value < 0.0) rgb = [0.68, 0.08, 0.04];
  else if (value < 0.2) rgb = [0.92, 0.35, 0.10];
  else if (value < 0.4) rgb = [0.96, 0.72, 0.30];
  else if (value < 0.6) rgb = [0.48, 0.72, 0.26];
  else rgb = [0.10, 0.42, 0.18];
  return [rgb[0], rgb[1], rgb[2], sample.dataMask];
}
""",
}


def validate_layer(value: str) -> CopernicusLayer:
    normalized = value.strip().upper()
    aliases = {"NDMI": "MOISTURE_INDEX", "NBR": "NBR_RAW"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in EVALSCRIPTS:
        raise ValueError("Capa Copernicus no admitida")
    return normalized  # type: ignore[return-value]


def validate_bbox(
    west: float,
    south: float,
    east: float,
    north: float,
) -> tuple[float, float, float, float]:
    values = (west, south, east, north)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("El BBOX contiene valores no finitos")
    if west >= east or south >= north:
        raise ValueError("El BBOX debe respetar west < east y south < north")
    if west < -180 or east > 180 or south < -90 or north > 90:
        raise ValueError("El BBOX está fuera de EPSG:4326")

    min_west, min_south, max_east, max_north = MISIONES_BBOX
    clipped = (
        max(west, min_west),
        max(south, min_south),
        min(east, max_east),
        min(north, max_north),
    )
    if clipped[0] >= clipped[2] or clipped[1] >= clipped[3]:
        raise ValueError("El BBOX no intersecta el territorio operativo de Misiones")
    return tuple(round(value, 6) for value in clipped)  # type: ignore[return-value]


def build_process_request(
    *,
    layer: CopernicusLayer,
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    max_dimension = settings.copernicus_max_dimension
    if not (64 <= width <= max_dimension and 64 <= height <= max_dimension):
        raise ValueError(f"Las dimensiones deben estar entre 64 y {max_dimension} píxeles")
    west, south, east, north = validate_bbox(*bbox)
    to_date = now or datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=settings.copernicus_time_range_days)
    return {
        "input": {
            "bounds": {
                "bbox": [west, south, east, north],
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                },
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": from_date.isoformat().replace("+00:00", "Z"),
                            "to": to_date.isoformat().replace("+00:00", "Z"),
                        },
                        "mosaickingOrder": "leastCC",
                        "maxCloudCoverage": settings.copernicus_max_cloud_coverage,
                    },
                }
            ],
        },
        "output": {
            "width": width,
            "height": height,
            "responses": [
                {
                    "identifier": "default",
                    "format": {"type": "image/png"},
                }
            ],
        },
        "evalscript": EVALSCRIPTS[layer],
    }


async def access_token(
    settings: Settings | None = None,
    *,
    client: httpx.AsyncClient | None = None,
    force_refresh: bool = False,
) -> str:
    settings = settings or get_settings()
    if not settings.copernicus_process_configured:
        raise CopernicusError(
            "Copernicus Process API requiere COPERNICUS_CLIENT_ID y COPERNICUS_CLIENT_SECRET"
        )
    now = time.monotonic()
    if (
        not force_refresh
        and _token_state.token
        and _token_state.client_id == settings.copernicus_client_id
        and _token_state.expires_at > now + 30
    ):
        return _token_state.token

    async with _token_lock:
        now = time.monotonic()
        if (
            not force_refresh
            and _token_state.token
            and _token_state.client_id == settings.copernicus_client_id
            and _token_state.expires_at > now + 30
        ):
            return _token_state.token
        own_client = client is None
        http_client = client or httpx.AsyncClient(
            timeout=settings.copernicus_http_timeout_seconds,
            follow_redirects=True,
        )
        try:
            response = await http_client.post(
                settings.copernicus_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.copernicus_client_id,
                    "client_secret": settings.copernicus_client_secret,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
            token = str(payload.get("access_token") or "")
            expires_in = max(60, int(payload.get("expires_in") or 3600))
            if not token:
                raise CopernicusError("Copernicus no devolvió access_token")
            _token_state.token = token
            _token_state.client_id = settings.copernicus_client_id
            _token_state.expires_at = time.monotonic() + expires_in
            return token
        except httpx.HTTPStatusError as exc:
            detail = "credenciales rechazadas"
            if exc.response.status_code == 429:
                detail = "límite temporal de autenticación alcanzado"
            raise CopernicusError(
                f"Copernicus OAuth respondió HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise CopernicusError(
                f"No se pudo autenticar con Copernicus: {type(exc).__name__}"
            ) from exc
        finally:
            if own_client:
                await http_client.aclose()


def _cache_key(
    layer: CopernicusLayer,
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    settings: Settings,
) -> str:
    rounded = [round(value, 3) for value in bbox]
    raw = json.dumps(
        [layer, rounded, width, height, settings.copernicus_time_range_days, settings.copernicus_max_cloud_coverage],
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def process_image(
    *,
    layer: CopernicusLayer,
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> bytes:
    settings = settings or get_settings()
    clipped_bbox = validate_bbox(*bbox)
    key = _cache_key(layer, clipped_bbox, width, height, settings)
    now = time.monotonic()
    async with _image_cache_lock:
        cached = _image_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

    own_client = client is None
    http_client = client or httpx.AsyncClient(
        timeout=settings.copernicus_http_timeout_seconds,
        follow_redirects=True,
    )
    try:
        token = await access_token(settings, client=http_client)
        request_body = build_process_request(
            layer=layer,
            bbox=clipped_bbox,
            width=width,
            height=height,
            settings=settings,
        )
        response = await http_client.post(
            settings.copernicus_process_url,
            json=request_body,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "image/png",
                "Content-Type": "application/json",
                "User-Agent": f"EcoNexo/{settings.release_version}",
            },
        )
        if response.status_code == 401:
            token = await access_token(settings, client=http_client, force_refresh=True)
            response = await http_client.post(
                settings.copernicus_process_url,
                json=request_body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "image/png",
                    "Content-Type": "application/json",
                    "User-Agent": f"EcoNexo/{settings.release_version}",
                },
            )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "image/png" not in content_type or not response.content.startswith(b"\x89PNG"):
            raise CopernicusError("Copernicus respondió un formato inesperado; se esperaba PNG")
        image = bytes(response.content)
        async with _image_cache_lock:
            _image_cache[key] = (time.monotonic() + settings.copernicus_cache_seconds, image)
            if len(_image_cache) > 32:
                expired_or_oldest = sorted(_image_cache, key=lambda item: _image_cache[item][0])[:8]
                for item in expired_or_oldest:
                    _image_cache.pop(item, None)
        return image
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            payload = exc.response.json()
            detail = str(payload.get("error", {}).get("message") or payload.get("message") or "")
        except Exception:
            detail = ""
        suffix = f": {detail[:240]}" if detail else ""
        raise CopernicusError(
            f"Copernicus Process API respondió HTTP {exc.response.status_code}{suffix}"
        ) from exc
    except httpx.HTTPError as exc:
        raise CopernicusError(
            f"No se pudo consultar Copernicus Process API: {type(exc).__name__}"
        ) from exc
    finally:
        if own_client:
            await http_client.aclose()


def parse_wms_capabilities(content: bytes) -> tuple[str | None, list[str]]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise CopernicusError("GetCapabilities devolvió XML inválido") from exc

    root_tag = root.tag.rsplit("}", 1)[-1].lower()
    if "exception" in root_tag:
        message = " ".join(
            text.strip() for text in root.itertext() if text and text.strip()
        )
        raise CopernicusError(f"Copernicus WMS rechazó la solicitud: {message[:300]}")

    title: str | None = None
    layers: list[str] = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "ServiceException":
            message = (element.text or "Error OGC").strip()
            raise CopernicusError(f"Copernicus WMS: {message[:300]}")
        if tag == "Title" and title is None and element.text:
            title = element.text.strip()
        elif tag == "Name" and element.text:
            value = element.text.strip()
            if value and value.upper() != "WMS" and value not in layers:
                layers.append(value)
    if not layers:
        raise CopernicusError(
            "La instancia WMS respondió, pero no informó capas. Revisá Configuration Utility."
        )
    return title, layers


async def test_wms(
    url: str,
    settings: Settings | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> tuple[str | None, list[str]]:
    settings = settings or get_settings()
    canonical = canonical_wms_url(url)
    if canonical is None:
        raise CopernicusError("No hay URL WMS configurada")
    own_client = client is None
    http_client = client or httpx.AsyncClient(
        timeout=settings.copernicus_http_timeout_seconds,
        follow_redirects=True,
    )
    try:
        response = await http_client.get(
            canonical,
            params={"SERVICE": "WMS", "REQUEST": "GetCapabilities", "VERSION": "1.3.0"},
            headers={
                "User-Agent": f"EcoNexo/{settings.release_version}",
                "Accept": "application/xml,text/xml,*/*",
            },
        )
        response.raise_for_status()
        return parse_wms_capabilities(response.content)
    except httpx.HTTPStatusError as exc:
        raise CopernicusError(
            f"Copernicus WMS respondió HTTP {exc.response.status_code}; verificá INSTANCE_ID y permisos"
        ) from exc
    except httpx.HTTPError as exc:
        raise CopernicusError(
            f"No se pudo consultar Copernicus WMS: {type(exc).__name__}"
        ) from exc
    finally:
        if own_client:
            await http_client.aclose()


async def test_process_api(
    settings: Settings | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> int:
    settings = settings or get_settings()
    image = await process_image(
        layer="TRUE_COLOR",
        bbox=(-55.05, -27.05, -54.75, -26.75),
        width=64,
        height=64,
        settings=settings,
        client=client,
    )
    return len(image)


def public_status(
    row: Mapping[str, Any] | None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    resolution = resolve_provider(row, settings)
    raw_layers = (row or {}).get("copernicus_available_layers") or []
    if isinstance(raw_layers, str):
        try:
            raw_layers = json.loads(raw_layers)
        except json.JSONDecodeError:
            raw_layers = []
    available_layers = [str(value) for value in raw_layers] if isinstance(raw_layers, list) else []
    return {
        "enabled": bool((row or {}).get("copernicus_enabled", settings.copernicus_enabled_by_default)),
        "provider": resolution.provider,
        "configured": resolution.configured,
        "process_configured": resolution.process_configured,
        "wms_configured": resolution.wms_configured,
        "system_default": resolution.system_default,
        "effective_wms_url": resolution.effective_wms_url,
        "supported_layers": list(EVALSCRIPTS),
        "collection": "sentinel-2-l2a",
        "last_test_at": (row or {}).get("copernicus_last_test_at"),
        "last_test_ok": (row or {}).get("copernicus_last_test_ok"),
        "last_error": (row or {}).get("copernicus_last_error"),
        "available_layers": available_layers,
    }


def reset_caches_for_tests() -> None:
    _token_state.token = ""
    _token_state.client_id = ""
    _token_state.expires_at = 0.0
    _image_cache.clear()
