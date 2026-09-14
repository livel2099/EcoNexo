"""Respaldo MET Norway: unidades, variables ausentes y uso desde el pipeline."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app import met_no, weather_cache


def payload(**cambios):
    detalles = {"air_temperature": 19.4, "relative_humidity": 62.3, "wind_speed": 3.7,
                "wind_speed_of_gust": 7.2}
    detalles.update(cambios)
    return {"properties": {
        "meta": {"units": {"air_temperature": "celsius", "relative_humidity": "%",
                           "wind_speed": "m/s", "wind_speed_of_gust": "m/s"}},
        "timeseries": [{"time": "2026-09-14T21:00:00Z",
                        "data": {"instant": {"details": detalles},
                                 "next_1_hours": {"details": {"precipitation_amount": 0.0}}}}],
    }}


def test_wind_is_converted_to_the_unit_the_pipeline_already_stores():
    lecturas = met_no.parse_current(payload())
    assert lecturas["temp"] == 19.4
    assert lecturas["humidity"] == 62.3
    assert lecturas["wind_speed"] == pytest.approx(13.32)  # 3,7 m/s -> km/h
    assert lecturas["wind_gust"] == pytest.approx(25.92)


def test_vpd_is_derived_from_temperature_and_humidity():
    # FAO-56: es(19,4 C) = 2,2536 kPa; con 62,3 % de humedad el deficit es 0,8496.
    assert met_no.vapour_pressure_deficit_kpa(19.4, 62.3) == pytest.approx(0.8496, abs=0.002)
    assert met_no.parse_current(payload())["vpd"] == pytest.approx(0.8496, abs=0.002)


def test_variables_that_met_norway_does_not_publish_are_left_out():
    """La lluvia de MET Norway es la esperada, no la caida: no reemplaza la otra."""
    lecturas = met_no.parse_current(payload())
    assert "precipitation" not in lecturas and "soil_moisture" not in lecturas


def test_absent_gust_does_not_become_zero():
    datos = payload()
    del datos["properties"]["timeseries"][0]["data"]["instant"]["details"]["wind_speed_of_gust"]
    assert "wind_gust" not in met_no.parse_current(datos)


def test_unexpected_units_are_rejected():
    datos = payload()
    datos["properties"]["meta"]["units"]["wind_speed"] = "km/h"
    with pytest.raises(met_no.MetNoError, match="unidades"):
        met_no.parse_current(datos)


def test_cache_respects_the_expires_header_within_bounds():
    assert met_no.cache_ttl(None) == met_no.MIN_TTL_SECONDS
    assert met_no.cache_ttl("no es una fecha") == met_no.MIN_TTL_SECONDS
    assert met_no.cache_ttl("Mon, 14 Sep 2020 21:39:47 GMT") == met_no.MIN_TTL_SECONDS
    lejano = met_no.cache_ttl("Mon, 14 Sep 2099 21:39:47 GMT")
    assert lejano == met_no.MAX_TTL_SECONDS


@pytest.mark.asyncio
async def test_request_identifies_itself_and_truncates_coordinates(monkeypatch):
    """Su ToS bloquea sin User-Agent y rechaza coordenadas de 5 decimales."""
    async def sin_cache(key):
        return None

    monkeypatch.setattr(weather_cache, "read", sin_cache)
    monkeypatch.setattr(weather_cache, "write", AsyncMock())
    monkeypatch.setattr(met_no, "get_settings", lambda: SimpleNamespace(
        met_no_user_agent="EcoNexo/1.0 contacto@example.test", pipeline_http_timeout_seconds=10))
    pedidos = []
    real_client = httpx.AsyncClient

    def handler(request):
        pedidos.append(request)
        return httpx.Response(200, json=payload(), headers={"expires": "Mon, 14 Sep 2099 21:39:47 GMT"})

    monkeypatch.setattr(met_no.httpx, "AsyncClient",
                        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    lecturas = await met_no.fetch_current_batch([(-27.367123, -55.896987)])
    assert lecturas[0]["temp"] == 19.4
    assert pedidos[0].url.params["lat"] == "-27.3671"
    assert pedidos[0].url.params["lon"] == "-55.8970"
    assert "EcoNexo/1.0 contacto@example.test" == pedidos[0].headers["user-agent"]


@pytest.mark.asyncio
async def test_missing_user_agent_stops_the_request(monkeypatch):
    monkeypatch.setattr(met_no, "get_settings", lambda: SimpleNamespace(
        met_no_user_agent="   ", pipeline_http_timeout_seconds=10))
    with pytest.raises(met_no.MetNoError, match="MET_NO_USER_AGENT"):
        await met_no.fetch_current_batch([(-27.3671, -55.8961)])
