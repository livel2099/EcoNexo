from __future__ import annotations

import json

from app.config import Settings
from app.territory import decode_geojson_geometry
from app.schemas import CopernicusWmsTestIn, EnvironmentalSourceSettingsIn


def test_cors_always_includes_public_render_frontend(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    settings = Settings(
        environment="production",
        public_app_url="https://econexo-web.onrender.com",
        cors_origins="https://otro.example",
    )
    assert "https://econexo-web.onrender.com" in settings.cors_list
    assert "https://otro.example" in settings.cors_list


def test_cors_accepts_the_explicit_static_web_origin():
    settings = Settings(
        public_app_url="https://app.econexo.com.ar",
        cors_origins="https://app.econexo.com.ar",
        econexo_web_origin="https://econexo-web.onrender.com/",
    )
    assert "https://econexo-web.onrender.com" in settings.cors_list


def test_geojson_jsonb_string_is_decoded():
    raw = json.dumps({
        "type": "MultiPolygon",
        "coordinates": [[[[-55.0, -27.0], [-54.9, -27.0], [-55.0, -27.0]]]],
    })
    geometry = decode_geojson_geometry(raw)
    assert geometry is not None
    assert geometry["type"] == "MultiPolygon"


def test_geojson_rejects_empty_or_invalid_geometry():
    assert decode_geojson_geometry("not-json") is None
    assert decode_geojson_geometry({"type": "Polygon", "coordinates": []}) is None


def test_copernicus_get_capabilities_url_is_canonicalized():
    body = CopernicusWmsTestIn(
        url="https://sh.dataspace.copernicus.eu/ogc/wms/abc-123/?SERVICE=WMS&REQUEST=GetCapabilities"
    )
    assert body.url == "https://sh.dataspace.copernicus.eu/ogc/wms/abc-123"


def test_source_settings_use_system_copernicus_without_wms_url():
    body = EnvironmentalSourceSettingsIn(copernicus_enabled=True, copernicus_wms_url=None)
    assert body.copernicus_enabled is True
    assert body.copernicus_use_system_default is True
    assert body.copernicus_wms_url is None


def test_fastapi_has_one_effective_global_exception_handler():
    from app.main import app

    handler = app.exception_handlers.get(Exception)
    assert handler is not None
    assert handler.__name__ == "unhandled_exception"


def test_copernicus_secrets_are_not_referenced_by_frontend():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    web = root / "apps/web"
    forbidden = ("NEXT_PUBLIC_COPERNICUS_CLIENT_SECRET", "NEXT_PUBLIC_COPERNICUS_CLIENT_ID", "process.env.COPERNICUS_CLIENT_SECRET", "process.env.COPERNICUS_CLIENT_ID")
    matches = []
    for path in web.rglob("*"):
        if not path.is_file() or any(part in {"node_modules", ".next", "out"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token in forbidden:
            if token in text:
                matches.append((path.relative_to(root).as_posix(), token))
    assert matches == []
