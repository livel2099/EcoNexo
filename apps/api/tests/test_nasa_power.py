import copy
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app import nasa_power as nasa, weather_cache, open_meteo_http, db, agro


def payload():
    keys = nasa.PARAMETERS.split(",")
    values = [25.72, 19.72, 75.52, 2.04, 99.22, 0.86, 3.3]
    units = ["C", "C", "%", "m/s", "kPa", "MJ/m^2/day", "mm/day"]
    return {"properties": {"parameter": {k: {"20260801": v} for k, v in zip(keys, values)}},
            "parameters": {k: {"units": u} for k, u in zip(keys, units)},
            "geometry": {"coordinates": [-55.896, -27.367, 155.68]}, "header": {"fill_value": -999}}


def test_fao56_published_example_18():
    # FAO-56 chapter 4, Uccle July 6: ea=1.409, es=1.997, ET0=3.88 mm/day.
    result = nasa.et0_fao56(date(2001, 7, 6), 50.8, 100, 21.5, 12.3,
                           100 * 1.409 / 1.997, 2.078, 100.1, 22.07)
    assert result == pytest.approx(3.88, abs=0.03)


def test_units_radiation_conversion_and_source():
    first = payload()
    second = copy.deepcopy(first)
    second["parameters"]["ALLSKY_SFC_SW_DWN"]["units"] = "kW-hr/m^2/day"
    second["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]["20260801"] /= 3.6
    a, b = nasa.parse_daily(first, -27.367), nasa.parse_daily(second, -27.367)
    assert a == b
    assert a[0]["source"] == "nasa-power"
    assert a[0]["precipitation_mm"] == 3.3
    assert a[0]["et0_mm"] > 0


@pytest.mark.parametrize("bad", [-999, None, float("nan")])
def test_missing_values_do_not_become_zero(bad):
    data = payload()
    data["properties"]["parameter"]["PRECTOTCORR"]["20260801"] = bad
    assert nasa.parse_daily(data, -27.367) == []


def test_unknown_units_rejected():
    data = payload()
    data["parameters"]["PS"]["units"] = "hPa"
    with pytest.raises(nasa.NasaPowerError, match="unidades"):
        nasa.parse_daily(data, -27.367)


def test_agro_does_not_invent_water_balance():
    row = {"day": date(2026, 8, 1), "tmax": 25, "tmin": 15, "et0_mm": None, "precipitation_mm": 0}
    assert agro.build_daily_series(agro.CROPS["maiz"], [row]) == []


@pytest.mark.asyncio
async def test_history_reuses_persistent_cache(monkeypatch):
    saved = {}
    async def read(key): return saved.get(key)
    async def write(key, data, ttl): saved[key] = data
    monkeypatch.setattr(weather_cache, "read", read)
    monkeypatch.setattr(weather_cache, "write", write)
    calls = []
    real_client = httpx.AsyncClient
    def handler(request):
        calls.append(request)
        assert request.url.params["community"] == "AG"
        assert request.url.params["time-standard"] == "LST"
        return httpx.Response(200, json=payload())
    monkeypatch.setattr(nasa.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    for _ in range(2):
        result = await nasa.fetch_history(-27.367, -55.896, date(2026, 8, 1), date(2026, 8, 3))
        assert len(result) == 1
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_persistent_open_meteo_cache_survives_memory_reset(monkeypatch):
    saved = {}
    async def read(key): return saved.get(key)
    async def write(key, data, ttl): saved[key] = data
    monkeypatch.setattr(weather_cache, "read", read)
    monkeypatch.setattr(weather_cache, "write", write)
    client = SimpleNamespace(get=AsyncMock(return_value=httpx.Response(200, json={"current": {"temperature_2m": 24}})))
    await open_meteo_http.get_response(client, "https://api.open-meteo.com/v1/forecast", {}, 60)
    open_meteo_http._cache.clear()
    result = await open_meteo_http.get_response(client, "https://api.open-meteo.com/v1/forecast", {}, 60)
    assert result.json()["current"]["temperature_2m"] == 24
    assert client.get.await_count == 1


@pytest.mark.asyncio
async def test_cache_database_expiry_and_json(monkeypatch):
    pool = SimpleNamespace(fetchval=AsyncMock(return_value='{"ok":true}'), execute=AsyncMock())
    monkeypatch.setattr(db, "pool", lambda: pool)
    assert await weather_cache.read("key") == {"ok": True}
    assert "expires_at > now()" in pool.fetchval.await_args.args[0]
    await weather_cache.write("key", {"ok": True}, 60)
    assert pool.execute.await_args.args[1:] == ("key", '{"ok": true}', 60.0)


@pytest.mark.asyncio
async def test_agro_saves_history_when_forecast_is_rate_limited(monkeypatch):
    from contextlib import asynccontextmanager
    from uuid import uuid4
    from app.routers import agro as router
    user = SimpleNamespace(id=uuid4(), org_id=uuid4())
    lot_id = uuid4()
    conn = SimpleNamespace(execute=AsyncMock(), copy_records_to_table=AsyncMock())
    @asynccontextmanager
    async def scope():
        yield conn
    conn.transaction = scope
    pool = SimpleNamespace(acquire=scope, fetch=AsyncMock(return_value=[]), execute=AsyncMock())
    monkeypatch.setattr(db, "pool", lambda: pool)
    monkeypatch.setattr(router, "require_agro_module", AsyncMock())
    monkeypatch.setattr(router, "_lot_or_404", AsyncMock(return_value={"crop_key": "maiz", "lat": -27.367,
        "lon": -55.896, "sowing_date": date(2026, 8, 1)}))
    monkeypatch.setattr(router, "record_audit", AsyncMock())
    monkeypatch.setattr(agro, "today_local", lambda: date(2026, 8, 3))
    history = nasa.parse_daily(payload(), -27.367)
    monkeypatch.setattr(agro, "fetch_history", AsyncMock(return_value=history))
    monkeypatch.setattr(agro, "fetch_forecast", AsyncMock(side_effect=agro.OpenMeteoError("HTTP 429")))
    result = await router.refresh_lot(lot_id, 90, user)
    assert result.history_days == 1 and result.forecast_days == 0
    assert result.stage_name is None
    assert "Sin pronostico actualizado" in result.detail
    assert "faltan 1 dias" in result.detail
    records = conn.copy_records_to_table.await_args.kwargs["records"]
    assert records[0][-2:] == ("nasa-power", False)
    assert any("partial:" in str(call.args) for call in conn.execute.await_args_list)
    assert result.advisories == []


@pytest.mark.asyncio
async def test_nasa_failure_does_not_delete_saved_series(monkeypatch):
    from uuid import uuid4
    from fastapi import HTTPException
    from app.routers import agro as router
    pool = SimpleNamespace(execute=AsyncMock(), acquire=AsyncMock())
    monkeypatch.setattr(db, "pool", lambda: pool)
    monkeypatch.setattr(router, "require_agro_module", AsyncMock())
    monkeypatch.setattr(router, "_lot_or_404", AsyncMock(return_value={"crop_key": "maiz", "lat": -27,
        "lon": -55, "sowing_date": None}))
    monkeypatch.setattr(agro, "fetch_history", AsyncMock(side_effect=nasa.NasaPowerError("NASA POWER respondio HTTP 503")))
    with pytest.raises(HTTPException) as error:
        await router.refresh_lot(uuid4(), 90, SimpleNamespace(id=uuid4(), org_id=uuid4()))
    assert error.value.status_code == 503
    assert "NASA POWER" in error.value.detail
    pool.acquire.assert_not_called()


@pytest.mark.asyncio
async def test_persistent_cooldown_prevents_retry_after_restart(monkeypatch):
    saved = {}
    async def read(key): return saved.get(key)
    async def write(key, data, ttl): saved[key] = data
    monkeypatch.setattr(weather_cache, "read", read)
    monkeypatch.setattr(weather_cache, "write", write)
    client = SimpleNamespace(get=AsyncMock(return_value=httpx.Response(429, headers={"retry-after": "3600"})))
    with pytest.raises(open_meteo_http.RateLimited):
        await open_meteo_http.get_response(client, "https://api.open-meteo.com/v1/forecast", {}, 60)
    open_meteo_http._cooldowns.clear()
    with pytest.raises(open_meteo_http.RateLimited):
        await open_meteo_http.get_response(client, "https://api.open-meteo.com/v1/forecast", {"latitude": "-26"}, 60)
    assert client.get.await_count == 1


@pytest.mark.asyncio
async def test_previous_forecast_is_reused_when_open_meteo_fails(monkeypatch):
    """Reprocesar durante un 429 no puede dejar al lote sin proximos dias."""
    from contextlib import asynccontextmanager
    from datetime import datetime, timezone
    from uuid import uuid4
    from app.routers import agro as router
    user = SimpleNamespace(id=uuid4(), org_id=uuid4())
    conn = SimpleNamespace(execute=AsyncMock(), copy_records_to_table=AsyncMock())

    @asynccontextmanager
    async def scope():
        yield conn

    conn.transaction = scope
    guardado = [
        {"day": date(2026, 8, 3), "tmax_c": 24.0, "tmin_c": 12.0, "precipitation_mm": 0.0,
         "et0_mm": 3.1, "created_at": datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)},
        {"day": date(2026, 8, 4), "tmax_c": 26.0, "tmin_c": 13.0, "precipitation_mm": 5.0,
         "et0_mm": 3.4, "created_at": datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)},
    ]
    pool = SimpleNamespace(acquire=scope, fetch=AsyncMock(side_effect=[guardado, []]), execute=AsyncMock())
    monkeypatch.setattr(db, "pool", lambda: pool)
    monkeypatch.setattr(router, "require_agro_module", AsyncMock())
    monkeypatch.setattr(router, "_lot_or_404", AsyncMock(return_value={"crop_key": "maiz", "lat": -27.367,
        "lon": -55.896, "sowing_date": date(2026, 8, 1)}))
    monkeypatch.setattr(router, "record_audit", AsyncMock())
    monkeypatch.setattr(agro, "today_local", lambda: date(2026, 8, 3))
    monkeypatch.setattr(agro, "fetch_history", AsyncMock(return_value=nasa.parse_daily(payload(), -27.367)))
    monkeypatch.setattr(agro, "fetch_forecast", AsyncMock(side_effect=agro.OpenMeteoError("HTTP 429")))

    result = await router.refresh_lot(uuid4(), 90, user)

    assert result.forecast_days == 2
    assert "Pronostico reutilizado del 2026-08-02" in result.detail
    assert any("previo del 2026-08-02" in fuente for fuente in result.sources)
    assert result.advisories == []
    registros = conn.copy_records_to_table.await_args.kwargs["records"]
    fuentes = {fila[2]: fila[-2] for fila in registros}
    assert fuentes[date(2026, 8, 1)] == "nasa-power"
    assert fuentes[date(2026, 8, 3)] == "open-meteo-previo"
    assert fuentes[date(2026, 8, 4)] == "open-meteo-previo"
