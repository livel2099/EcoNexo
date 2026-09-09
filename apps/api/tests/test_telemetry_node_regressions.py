"""Regresiones del alta virtual y del error 500 en configuración del pipeline."""
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import asyncpg
import httpx
import pytest
from fastapi import FastAPI

from app import db, telemetry_pipeline as engine
from app.deps import CurrentUser, current_user
from app.routers import devices, pipeline


@pytest.fixture
def context(monkeypatch):
    user = CurrentUser(uuid4(), uuid4(), "admin")
    zone_id, device_id = uuid4(), uuid4()
    row = dict(id=device_id, name="Posadas", external_id="posadas",
               lat=-27.3671, lon=-55.8961, status="offline", tags=["virtual"],
               telemetry_mode="open_meteo", marker_shape="triangle", zone_id=zone_id,
               pipeline_enabled=True, telemetry_config='{"provider":"open-meteo"}',
               latest_readings='{"temp":25.5}')
    pool = SimpleNamespace(fetch=AsyncMock(return_value=[row]), fetchrow=AsyncMock(return_value=row),
                           fetchval=AsyncMock(return_value=device_id), execute=AsyncMock(return_value="UPDATE 1"))
    monkeypatch.setattr(db, "pool", lambda: pool)
    monkeypatch.setattr(devices, "enforce_resource_limit", AsyncMock())
    monkeypatch.setattr(devices, "hash_secret", lambda secret: "hashed")
    monkeypatch.setattr(devices, "record_audit", AsyncMock())
    monkeypatch.setattr(pipeline, "record_audit", AsyncMock())
    app = FastAPI()
    app.include_router(devices.router)
    app.include_router(pipeline.router)
    app.dependency_overrides[current_user] = lambda: user
    return SimpleNamespace(app=app, pool=pool, user=user, row=row, zone_id=zone_id, device_id=device_id)


@pytest.mark.asyncio
async def test_create_and_list_preserve_virtual_configuration(context):
    c = context
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=c.app), base_url="http://test") as client:
        response = await client.post("/devices", json=dict(
            name="Posadas", external_id="Posadas", lat=-27.3671, lon=-55.8961,
            telemetry_mode="open_meteo", marker_shape="triangle", zone_id=str(c.zone_id),
            pipeline_enabled=True, telemetry_config={"provider": "open-meteo"},
        ))
        assert response.status_code == 201, response.text
        args = c.pool.fetchval.await_args.args
        assert args[10:14] == ("triangle", "open_meteo", c.zone_id, True)
        assert json.loads(args[14]) == {"provider": "open-meteo"}
        assert response.json()["status"] == "offline"  # No lecturas inventadas.
        response = await client.get("/devices")
        assert response.status_code == 200
        assert response.json()[0]["telemetry_mode"] == "open_meteo"
        assert response.json()[0]["latest_readings"] == {"temp": 25.5}
        assert c.pool.fetch.await_args.args[1] == c.user.org_id


@pytest.mark.asyncio
async def test_duplicate_identifier_returns_conflict(context):
    context.pool.fetchval.side_effect = asyncpg.UniqueViolationError("duplicate")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=context.app), base_url="http://test") as client:
        response = await client.post("/devices", json=dict(
            name="Posadas", external_id="posadas", lat=-27.3671, lon=-55.8961,
        ))
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_cross_org_zone_is_rejected(context):
    context.pool.fetchval.return_value = False
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=context.app), base_url="http://test") as client:
        response = await client.post("/devices", json=dict(
            name="Posadas", external_id="posadas", lat=-27.3671, lon=-55.8961, zone_id=str(uuid4()),
        ))
    assert response.status_code == 404
    assert context.pool.fetchval.await_count == 1  # Sin INSERT.


@pytest.mark.asyncio
async def test_update_source_is_scoped_and_allows_clearing_zone(context):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=context.app), base_url="http://test") as client:
        response = await client.patch(f"/devices/{context.device_id}", json={"telemetry_mode": "open_meteo", "zone_id": None})
        assert response.status_code == 200
        args = context.pool.execute.await_args.args
        assert args[1:3] == (context.device_id, context.user.org_id)
        assert args[3:] == ("open_meteo", None)
        response = await client.patch(f"/devices/{context.device_id}", json={"telemetry_mode": None})
        assert response.status_code == 422
        context.pool.fetchrow.return_value = None
        response = await client.patch(f"/devices/{uuid4()}", json={"telemetry_mode": "open_meteo"})
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_pipeline_settings_get_and_patch_do_not_shadow_config(context):
    context.pool.fetchrow.return_value = dict(
        org_id=context.user.org_id, enabled=True, auto_run=False, interval_minutes=15,
        stale_minutes=30, refresh_firms=True, evaluate_rules=True, updated_at=datetime.now(timezone.utc),
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=context.app), base_url="http://test") as client:
        for method, payload in [("GET", None), ("PATCH", {"enabled": True})]:
            response = await client.request(method, "/pipeline/settings", json=payload)
            assert response.status_code == 200, response.text
            assert isinstance(response.json()["firms_configured"], bool)


@pytest.mark.asyncio
async def test_bootstrap_passes_virtual_configuration_to_real_creator(context, monkeypatch):
    c = context
    c.pool.fetchrow.side_effect = [dict(id=c.zone_id, lat=-27.3671, lon=-55.8961), c.row, c.row]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=c.app), base_url="http://test") as client:
        response = await client.post("/pipeline/bootstrap", json={"count": 2, "zone_id": str(c.zone_id)})
    assert response.status_code == 201, response.text
    assert len(response.json()["created"]) == 2
    inserts = [call.args for call in c.pool.fetchval.await_args_list if "INSERT INTO devices" in call.args[0]]
    assert len(inserts) == 2
    assert all(args[11] == "open_meteo" and args[12] == c.zone_id for args in inserts)


@pytest.mark.asyncio
async def test_real_readings_are_saved_before_marking_online(context, monkeypatch):
    conn = SimpleNamespace(copy_records_to_table=AsyncMock(), execute=AsyncMock())

    @asynccontextmanager
    async def scope():
        yield conn

    conn.transaction = scope
    context.pool.acquire = scope
    monkeypatch.setattr(engine, "fetch_open_meteo_current", AsyncMock(return_value={"temp": 24, "humidity": 70}))
    monkeypatch.setattr(engine, "publish", AsyncMock())
    device = {**context.row, "org_id": context.user.org_id}
    count, values = await engine.refresh_open_meteo_device(device)
    assert count == 2 and values["temp"] == 24
    assert len(conn.copy_records_to_table.await_args.kwargs["records"]) == 2
    assert "status='online'" in conn.execute.await_args.args[0]
    conn.execute.reset_mock()
    monkeypatch.setattr(engine, "fetch_open_meteo_current", AsyncMock(return_value={}))
    with pytest.raises(RuntimeError, match="no devolvio"):
        await engine.refresh_open_meteo_device(device)
    conn.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_pipeline_closes_run_if_loading_devices_fails(context, monkeypatch):
    monkeypatch.setattr(engine, "pipeline_settings", AsyncMock(return_value={"enabled": True}))
    context.pool.fetch.side_effect = RuntimeError("database unavailable")
    with pytest.raises(RuntimeError, match="database unavailable"):
        await engine.run_org_pipeline(context.user.org_id, context.user.id)
    assert "status='failed'" in context.pool.execute.await_args.args[0]


@pytest.mark.asyncio
async def test_pipeline_uses_open_meteo_and_reports_partial_failures(context, monkeypatch):
    device = {**context.row, "org_id": context.user.org_id}
    context.pool.fetch.return_value = [device]
    monkeypatch.setattr(engine, "pipeline_settings", AsyncMock(return_value={
        "enabled": True, "stale_minutes": 30, "refresh_firms": False, "evaluate_rules": False,
    }))
    refresh = AsyncMock(return_value=(2, {"temp": 24, "humidity": 70}))
    monkeypatch.setattr(engine, "refresh_open_meteo_device", refresh)
    monkeypatch.setattr(engine, "publish", AsyncMock())
    result = await engine.run_org_pipeline(context.user.org_id, context.user.id)
    assert result["devices_updated"] == 1 and result["readings_inserted"] == 2
    assert result["status"] == "completed"
    refresh.side_effect = httpx.ReadTimeout("Open-Meteo timeout")
    result = await engine.run_org_pipeline(context.user.org_id, context.user.id)
    assert result["status"] == "partial"
    assert result["devices_updated"] == 0
    assert result["errors"][0]["device"] == str(context.device_id)
