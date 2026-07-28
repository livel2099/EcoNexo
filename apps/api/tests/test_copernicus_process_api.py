from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.copernicus import (
    EVALSCRIPTS,
    CopernicusError,
    access_token,
    build_process_request,
    canonical_wms_url,
    parse_wms_capabilities,
    process_image,
    public_status,
    reset_caches_for_tests,
    resolve_provider,
    validate_bbox,
    validate_layer,
)
from app.main import app


@pytest.fixture(autouse=True)
def reset_cache():
    reset_caches_for_tests()
    yield
    reset_caches_for_tests()


def configured_settings(**overrides) -> Settings:
    values = {
        "copernicus_client_id": "client-id",
        "copernicus_client_secret": "client-secret",
        "copernicus_mode": "process_api",
        "copernicus_max_dimension": 1024,
        "copernicus_time_range_days": 90,
        "copernicus_max_cloud_coverage": 80,
    }
    values.update(overrides)
    return Settings(**values)


def test_process_api_is_default_when_credentials_are_configured():
    settings = configured_settings()
    row = {
        "copernicus_enabled": True,
        "copernicus_use_system_default": True,
        "copernicus_wms_url": None,
    }
    result = resolve_provider(row, settings)
    assert result.provider == "process_api"
    assert result.configured is True
    assert result.effective_wms_url is None


def test_wms_remains_supported_as_explicit_override():
    settings = configured_settings()
    row = {
        "copernicus_enabled": True,
        "copernicus_use_system_default": False,
        "copernicus_wms_url": "https://sh.dataspace.copernicus.eu/ogc/wms/abc-123",
    }
    result = resolve_provider(row, settings)
    assert result.provider == "wms"
    assert result.effective_wms_url.endswith("/abc-123")


def test_public_status_never_exposes_oauth_secret():
    settings = configured_settings(copernicus_client_secret="ultra-secret-value")
    status = public_status({"copernicus_enabled": True, "copernicus_use_system_default": True}, settings)
    serialized = json.dumps(status, default=str)
    assert "ultra-secret-value" not in serialized
    assert status["provider"] == "process_api"
    assert status["supported_layers"] == ["TRUE_COLOR", "NDVI", "MOISTURE_INDEX", "NBR_RAW"]


def test_evalscript_contracts_cover_required_sentinel_bands():
    assert '"B02"' in EVALSCRIPTS["TRUE_COLOR"]
    assert '"B04"' in EVALSCRIPTS["TRUE_COLOR"]
    assert '"B08"' in EVALSCRIPTS["NDVI"]
    assert '"B11"' in EVALSCRIPTS["MOISTURE_INDEX"]
    assert '"B12"' in EVALSCRIPTS["NBR_RAW"]
    assert "dataMask" in EVALSCRIPTS["TRUE_COLOR"]


def test_process_request_uses_sentinel_2_l2a_and_clips_to_misiones():
    settings = configured_settings()
    bbox = validate_bbox(-60, -30, -50, -24)
    request = build_process_request(
        layer="NDVI",
        bbox=bbox,
        width=512,
        height=384,
        settings=settings,
    )
    assert request["input"]["data"][0]["type"] == "sentinel-2-l2a"
    assert request["input"]["data"][0]["dataFilter"]["mosaickingOrder"] == "leastCC"
    assert request["input"]["bounds"]["bbox"] == [-56.1, -28.2, -53.55, -25.45]
    assert request["output"]["responses"][0]["format"]["type"] == "image/png"


def test_layer_aliases_are_normalized():
    assert validate_layer("ndmi") == "MOISTURE_INDEX"
    assert validate_layer("nbr") == "NBR_RAW"
    with pytest.raises(ValueError):
        validate_layer("unknown")


@pytest.mark.asyncio
async def test_oauth_token_is_cached_until_expiry():
    settings = configured_settings()
    calls = {"token": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL(settings.copernicus_token_url)
        calls["token"] += 1
        return httpx.Response(200, json={"access_token": "token-123", "expires_in": 3600})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        first = await access_token(settings, client=client)
        second = await access_token(settings, client=client)
    assert first == second == "token-123"
    assert calls["token"] == 1


@pytest.mark.asyncio
async def test_process_image_uses_bearer_and_returns_png():
    settings = configured_settings(copernicus_cache_seconds=60)
    calls = {"token": 0, "process": 0}
    png = b"\x89PNG\r\n\x1a\nmock-image"

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url == httpx.URL(settings.copernicus_token_url):
            calls["token"] += 1
            return httpx.Response(200, json={"access_token": "token-xyz", "expires_in": 3600})
        assert request.url == httpx.URL(settings.copernicus_process_url)
        calls["process"] += 1
        assert request.headers["authorization"] == "Bearer token-xyz"
        payload = json.loads(request.content)
        assert payload["input"]["data"][0]["type"] == "sentinel-2-l2a"
        return httpx.Response(200, content=png, headers={"content-type": "image/png"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        first = await process_image(
            layer="TRUE_COLOR",
            bbox=(-55.2, -27.2, -54.7, -26.7),
            width=256,
            height=256,
            settings=settings,
            client=client,
        )
        second = await process_image(
            layer="TRUE_COLOR",
            bbox=(-55.2, -27.2, -54.7, -26.7),
            width=256,
            height=256,
            settings=settings,
            client=client,
        )
    assert first == second == png
    assert calls == {"token": 1, "process": 1}


def test_wms_capabilities_parser_detects_layers_and_service_errors():
    title, layers = parse_wms_capabilities(
        b"""<?xml version='1.0'?><WMS_Capabilities><Service><Title>EcoNexo</Title></Service><Capability><Layer><Name>TRUE_COLOR</Name><Layer><Name>NDVI</Name></Layer></Layer></Capability></WMS_Capabilities>"""
    )
    assert title == "EcoNexo"
    assert layers == ["TRUE_COLOR", "NDVI"]
    with pytest.raises(CopernicusError):
        parse_wms_capabilities(b"<ServiceExceptionReport><ServiceException>Invalid instance</ServiceException></ServiceExceptionReport>")
    with pytest.raises(CopernicusError):
        parse_wms_capabilities(b"<WMS_Capabilities><Service><Title>Empty</Title></Service></WMS_Capabilities>")


def test_wms_url_is_restricted_to_official_host():
    assert canonical_wms_url("https://sh.dataspace.copernicus.eu/ogc/wms/abc?REQUEST=GetCapabilities") == "https://sh.dataspace.copernicus.eu/ogc/wms/abc"
    with pytest.raises(ValueError):
        canonical_wms_url("https://example.com/ogc/wms/abc")


def test_copernicus_routes_are_registered():
    paths = {getattr(route, "path", "") for route in app.routes}
    assert {"/copernicus/status", "/copernicus/test", "/copernicus/image"} <= paths


def test_migration_15_is_synced_and_guards_pipeline_concurrency():
    root = Path(__file__).resolve().parents[3]
    api_file = root / "apps/api/migrations/15_copernicus_process_defaults_and_pipeline_guards.sql"
    infra_file = root / "infra/db/migrations/15_copernicus_process_defaults_and_pipeline_guards.sql"
    assert api_file.read_bytes() == infra_file.read_bytes()
    sql = api_file.read_text(encoding="utf-8")
    assert "copernicus_use_system_default" in sql
    assert "ALTER COLUMN copernicus_enabled SET DEFAULT true" in sql
    assert "uq_pipeline_runs_one_running_per_org" in sql


def test_production_config_rejects_partial_copernicus_credentials():
    settings = Settings(
        environment="production",
        database_url="postgresql://user:password@example.internal/econexo",
        jwt_secret="a" * 64,
        internal_service_token="b" * 64,
        public_app_url="https://econexo-web.onrender.com",
        cors_origins="https://econexo-web.onrender.com",
        forwarded_allow_ips="127.0.0.1",
        platform_admin_emails="admin@example.com",
        sales_email="sales@example.com",
        mqtt_enabled=False,
        s3_enabled=False,
        anomaly_enabled=False,
        copernicus_client_id="client-only",
        copernicus_client_secret="",
    )
    assert "COPERNICUS_CLIENT_ID/COPERNICUS_CLIENT_SECRET" in settings.insecure_production_values()
