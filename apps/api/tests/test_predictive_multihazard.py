from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app import predictive_service as service
from app.predictive_engine import FEATURE_SETS, baseline, baseline_version, future_features, label_forecast, probability, train_model
from .test_predictions_api import context, observation_body

NOW = datetime(2026, 10, 6, 10, tzinfo=timezone.utc)
INPUTS = {"hydric": ("precipitation", "mm", 20), "health_heat": ("apparent_temperature", "°C", 42), "health_air": ("pm2_5", "μg/m³", 100)}


def payload(hazard, hours=73):
    variable, unit, value = INPUTS[hazard]
    return dict(hourly_units={variable: unit}, hourly={"time": [(NOW + timedelta(hours=i + 1)).isoformat() for i in range(hours)], variable: [value] * hours})


@pytest.mark.parametrize("hazard", INPUTS)
@pytest.mark.parametrize("hours", [6, 24, 72])
def test_complete_future_data_and_hazard_features(hazard, hours):
    features, start, end, series = future_features(payload(hazard), NOW, hours, hazard)
    assert set(features) == set(FEATURE_SETS[hazard])
    score, reasons = baseline(features, hazard)
    assert 0.65 <= score <= 1 and len(reasons) == 4
    assert start > NOW and end - start == timedelta(hours=hours) and len(series) == hours


@pytest.mark.parametrize("hazard", INPUTS)
def test_missing_source_never_returns_low_risk(hazard):
    data = payload(hazard)
    variable = INPUTS[hazard][0]
    data["hourly"][variable][5] = None
    with pytest.raises(ValueError):
        future_features(data, NOW, 24, hazard)


def test_results_of_other_hazard_cannot_label_predictions():
    prediction = dict(device_id=uuid4(), latitude=-26.9, longitude=-54.8, hazard="hydric", valid_from=NOW, valid_to=NOW + timedelta(hours=24))
    obs = dict(device_id=prediction["device_id"], latitude=-26.9, longitude=-54.8, hazard="fire", outcome="event", start_at=NOW, end_at=NOW)
    assert label_forecast(prediction, [obs])[0] is None
    obs["hazard"] = "hydric"
    assert label_forecast(prediction, [obs])[0] == 1


def test_pluvial_uses_accumulations_starting_in_the_future():
    data = payload("hydric")
    data["hourly"]["precipitation"][0] = 999  # Hora precedente que aún incluye el instante de emisión.
    features, start, end, series = future_features(data, NOW, 24, "hydric")
    assert features["rain_total_mm"] == 480
    assert series[0]["time"] == start.isoformat()
    assert series[-1]["time"] == (end - timedelta(hours=1)).isoformat()


@pytest.mark.parametrize("hazard", INPUTS)
def test_training_uses_separate_features_and_model_version(hazard):
    rows = []
    for i in range(160):
        positive = i % 2
        rows.append(dict(id=uuid4(), hazard=hazard, issued_at=NOW + timedelta(days=i), valid_to=NOW + timedelta(days=i, hours=6),
                         label=positive, risk_index=0.4, features={key: 60 * positive for key in FEATURE_SETS[hazard]}))
    artifact, metrics = train_model(rows, 6, hazard)
    assert artifact["schema"] == f"{hazard}-logistic-v1"
    assert metrics["hazard"] == hazard and artifact["features"] == list(FEATURE_SETS[hazard])
    assert probability(rows[1]["features"], artifact) > probability(rows[0]["features"], artifact)
    assert metrics["eligible"]
    rows[0]["hazard"] = "fire"
    with pytest.raises(ValueError, match="mezclar"):
        train_model(rows, 6, hazard)


@pytest.mark.parametrize("hazard", INPUTS)
def test_routes_are_scoped_by_hazard(context, hazard):
    assert context.client.get(f"/predictions?hazard={hazard}").status_code == 200
    assert context.pool.fetch.await_args.args[-1] == hazard
    assert "hazard=$4" in context.pool.fetch.await_args.args[0]
    assert context.client.get(f"/predictions/observations?hazard={hazard}").status_code == 200
    assert context.pool.fetch.await_args.args[-1] == hazard
    result = context.client.post("/predictions/models/deploy", json=dict(hazard=hazard, enabled=True, external_weather_consent=True))
    assert result.status_code == 200 and result.json()["hazard"] == hazard
    settings_insert = context.pool.execute.await_args_list[0].args
    assert settings_insert[-1] == hazard and "ON CONFLICT(org_id,horizon_hours,hazard)" in settings_insert[0]


def test_wrong_hazard_model_is_rejected_and_unknown_risk_is_invalid(context):
    context.pool.fetchrow.return_value = None
    result = context.client.post("/predictions/models/deploy", json=dict(hazard="hydric", model_id=str(uuid4()), enabled=True, external_weather_consent=True))
    assert result.status_code == 404
    assert "hazard=$4" in context.pool.fetchrow.await_args.args[0]
    assert context.pool.fetchrow.await_args.args[-1] == "hydric"
    assert context.client.get("/predictions?hazard=unknown").status_code == 422


def test_health_observation_conflicts_and_insert_use_health_scope(context):
    context.pool.fetchrow.side_effect = [dict(id=uuid4(), lat=-26.9, lon=-54.8), dict(id=uuid4())]
    context.pool.fetchval.side_effect = [NOW, False]
    assert context.client.post("/predictions/observations", json={**observation_body(), "hazard": "health_heat"}).status_code == 201
    assert "hazard=$8" in context.pool.fetchval.await_args.args[0]
    assert context.pool.fetchval.await_args.args[-1] == "health_heat"
    assert context.pool.fetchrow.await_args.args[-1] == "health_heat"


@pytest.mark.asyncio
async def test_unconsented_health_source_is_not_contacted(context, monkeypatch):
    context.pool.fetch.return_value = [dict(hazard="fire", horizon_hours=24, enabled=True)]
    provider = AsyncMock()
    monkeypatch.setattr(service, "forecasts_for_points", provider)
    result = await service.issue_forecasts(context.actor.org_id, context.actor.id, "health_air")
    assert result["created"] == 0
    provider.assert_not_awaited()


@pytest.mark.asyncio
async def test_multihazard_emission_archives_separate_predictions_and_source_failure(context, monkeypatch):
    device_id = uuid4()
    settings = [dict(hazard=risk, horizon_hours=24, enabled=True, active_model_id=None) for risk in INPUTS]
    context.pool.fetch.side_effect = [settings, [dict(id=device_id, name="Nodo", lat=-26.9, lon=-54.8)], [], settings]
    context.pool.fetchval.side_effect = [NOW, True, NOW, uuid4(), uuid4()]
    monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(pipeline_max_devices_per_run=10))
    async def provider(devices, hazard):
        if hazard == "health_air":
            raise RuntimeError("CAMS unavailable")
        return [payload(hazard)]
    monkeypatch.setattr(service, "forecasts_for_points", provider)
    result = await service.issue_forecasts(context.actor.org_id, context.actor.id)
    assert result["created"] == 2 and result["errors"][0]["hazard"] == "health_air"
    insertions = [call.args for call in context.pool.fetchval.await_args_list if "INSERT INTO predictions" in call.args[0]]
    assert {args[-1] for args in insertions} == {"hydric", "health_heat"}
    assert {args[12] for args in insertions} == {baseline_version("hydric"), baseline_version("health_heat")}
    assert all(args[14] is None for args in insertions)


@pytest.mark.asyncio
async def test_dataset_and_model_evaluation_query_all_filter_risk(context):
    context.pool.fetchval.return_value = NOW
    result = await service.evaluate_org(context.actor.org_id, 90, 24, "health_air")
    assert result["hazard"] == "health_air"
    assert result["metrics"][0]["model_version"] == baseline_version("health_air")
    for call in context.pool.fetch.await_args_list:
        assert call.args[-1] == "health_air" and "hazard=" in call.args[0]


@pytest.mark.asyncio
async def test_air_provider_uses_its_own_endpoint_and_variables(monkeypatch):
    import httpx
    monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(
        open_meteo_api_key="", open_meteo_air_quality_url="https://air-quality-api.open-meteo.com/v1/air-quality",
        pipeline_http_timeout_seconds=5))
    request = AsyncMock(return_value=httpx.Response(200, json=payload("health_air")))
    monkeypatch.setattr(service, "get_response", request)
    result = await service.forecasts_for_points([dict(lat=-26.9, lon=-54.8)], "health_air")
    assert result[0]["hourly_units"]["pm2_5"] == "μg/m³"
    args = request.await_args.args
    assert args[1] == "https://air-quality-api.open-meteo.com/v1/air-quality"
    assert args[2]["hourly"] == "pm2_5" and "temperature_unit" not in args[2]
    assert request.await_args.kwargs["ttl"] == 300
