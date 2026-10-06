from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import CurrentUser, current_user
from app.routers import predictions as routes
from app import predictive_service as service


@pytest.fixture
def context(monkeypatch):
    pool = SimpleNamespace(fetch=AsyncMock(return_value=[]), fetchval=AsyncMock(), fetchrow=AsyncMock(), execute=AsyncMock())
    @asynccontextmanager
    async def scope(): yield pool
    pool.acquire = scope
    pool.transaction = scope
    monkeypatch.setattr(routes.db, "pool", lambda: pool)
    monkeypatch.setattr(routes, "enforce_rate_limit", AsyncMock())
    app = FastAPI()
    app.include_router(routes.router)
    actor = CurrentUser(uuid4(), uuid4(), "admin")
    app.dependency_overrides[current_user] = lambda: actor
    return SimpleNamespace(pool=pool, app=app, actor=actor, client=TestClient(app))


@pytest.mark.parametrize("path", ["/predictions/run", "/predictions/observations", "/predictions/models/train", "/predictions/models/deploy"])
def test_viewer_cannot_mutate(context, path):
    context.actor.role = "visualizador"
    assert context.client.post(path, json={}).status_code == 403
    context.pool.execute.assert_not_awaited()


def test_get_horizon_and_tenant_scope(context):
    result = context.client.get("/predictions?horizon_hours=24")
    assert result.status_code == 200, result.text
    assert context.pool.fetch.await_args.args[1] == context.actor.org_id
    assert context.client.get("/predictions?horizon_hours=48").status_code == 422


def test_enabling_requires_explicit_external_source_consent(context):
    result = context.client.post("/predictions/models/deploy", json={"enabled": True})
    assert result.status_code == 422
    context.pool.execute.assert_not_awaited()


def test_model_from_other_tenant_and_failed_candidate_cannot_be_deployed(context):
    body = dict(model_id=str(uuid4()), enabled=True, external_weather_consent=True)
    context.pool.fetchrow.return_value = None
    assert context.client.post("/predictions/models/deploy", json=body).status_code == 404
    context.pool.fetchrow.return_value = dict(eligible=False)
    assert context.client.post("/predictions/models/deploy", json=body).status_code == 409
    context.pool.execute.assert_not_awaited()


def test_baseline_rollback_is_audited(context):
    result = context.client.post("/predictions/models/deploy", json=dict(enabled=True, external_weather_consent=True, model_id=None))
    assert result.status_code == 200 and result.json()["mode"] == "shadow"
    assert len(context.pool.execute.await_args_list) == 2
    assert "predictive_deploy" in context.pool.execute.await_args.args[0]


def observation_body():
    return dict(device_id=str(uuid4()), outcome="event", start_at="2026-10-01T10:00:00Z", end_at="2026-10-01T10:00:00Z",
                source="field_report", reference="Incident-001", notes="Verificado por personal en campo", coverage_verified=True)


def test_observation_rejects_cross_tenant_node_and_future_result(context):
    context.pool.fetchrow.return_value = None
    assert context.client.post("/predictions/observations", json=observation_body()).status_code == 404
    context.pool.fetchrow.return_value = dict(id=uuid4(), lat=-26.92, lon=-54.78)
    context.pool.fetchval.return_value = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert context.client.post("/predictions/observations", json=observation_body()).status_code == 422
    context.pool.execute.assert_not_awaited()


def test_observation_requires_real_source_and_timezone(context):
    body = observation_body()
    body["source"] = "simulator"
    assert context.client.post("/predictions/observations", json=body).status_code == 422
    body["source"] = "field_report"
    body["start_at"] = "2026-10-01T10:00:00"
    assert context.client.post("/predictions/observations", json=body).status_code == 422


@pytest.mark.asyncio
async def test_default_disabled_tenant_never_contacts_provider(context, monkeypatch):
    context.pool.fetchval.return_value = True
    weather = AsyncMock()
    monkeypatch.setattr(service, "forecasts_for_points", weather)
    result = await service.issue_forecasts(context.actor.org_id, context.actor.id)
    assert result["created"] == 0
    weather.assert_not_awaited()
    assert context.pool.fetch.await_count == 1


@pytest.mark.asyncio
async def test_same_day_version_is_idempotent_without_provider_call(context, monkeypatch):
    device_id = uuid4()
    clock = datetime(2026, 10, 6, tzinfo=timezone.utc)
    context.pool.fetchval.side_effect = [clock]
    context.pool.fetch.side_effect = [[dict(horizon_hours=24, enabled=True, active_model_id=None)],
        [dict(id=device_id, name="Nodo", lat=-26.92, lon=-54.78)],
        [dict(device_id=device_id, horizon_hours=24, model_version=service.BASELINE_VERSION)]]
    monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(pipeline_max_devices_per_run=10))
    weather = AsyncMock()
    monkeypatch.setattr(service, "forecasts_for_points", weather)
    result = await service.issue_forecasts(context.actor.org_id, context.actor.id)
    assert result["created"] == 0 and result["skipped"] == 1
    weather.assert_not_awaited()


@pytest.mark.asyncio
async def test_successful_issue_archives_future_series_and_never_invents_probability(context, monkeypatch):
    NOW = datetime(2026, 10, 6, 10, tzinfo=timezone.utc)
    payload = dict(hourly_units={"temperature_2m": "°C", "relative_humidity_2m": "%", "wind_speed_10m": "km/h", "precipitation": "mm"},
                   hourly={"time": [(NOW + timedelta(hours=i + 1)).isoformat() for i in range(24)],
                           "temperature_2m": [35] * 24, "relative_humidity_2m": [20] * 24,
                           "wind_speed_10m": [40] * 24, "precipitation": [0] * 24})
    device_id, prediction_id = uuid4(), uuid4()
    context.pool.fetchval.side_effect = [NOW, True, NOW, prediction_id]
    context.pool.fetch.side_effect = [[dict(horizon_hours=24, enabled=True, active_model_id=None)],
        [dict(id=device_id, name="Nodo", lat=-26.92, lon=-54.78)], [],
        [dict(horizon_hours=24, active_model_id=None)]]
    monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(pipeline_max_devices_per_run=10))
    monkeypatch.setattr(service, "forecasts_for_points", AsyncMock(return_value=[payload]))
    result = await service.issue_forecasts(context.actor.org_id, context.actor.id)
    assert result["created"] == 1 and not result["errors"]
    args = context.pool.fetchval.await_args.args
    assert args[1] == context.actor.org_id and args[2] == device_id
    assert args[8] > args[7] and args[9] > args[8]  # Inicio y final futuros.
    assert args[14] is None  # No hay probabilidad de un modelo no entrenado.
    import json
    provenance = json.loads(args[18])
    assert len(provenance["hourly"]) == 24 and not provenance["simulated"]
    assert "predictive_issue" in context.pool.execute.await_args.args[0]


def test_independent_event_verification_is_audited_and_conflict_is_rejected(context):
    body = observation_body()
    device = dict(id=uuid4(), lat=-26.92, lon=-54.78)
    context.pool.fetchrow.side_effect = [device, dict(id=uuid4(), outcome="event")]
    context.pool.fetchval.side_effect = [datetime(2026, 10, 6, tzinfo=timezone.utc), False]
    assert context.client.post("/predictions/observations", json=body).status_code == 201
    assert "predictive_verify" in context.pool.execute.await_args.args[0]
    context.pool.execute.reset_mock()
    context.pool.fetchrow.side_effect = [device]
    context.pool.fetchval.side_effect = [datetime(2026, 10, 6, tzinfo=timezone.utc), True]
    assert context.client.post("/predictions/observations", json=body).status_code == 409
    context.pool.execute.assert_not_awaited()
