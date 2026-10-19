from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app import met_no, paraguay_context, predictive_service
from app.predictive_engine import future_features
from app.open_meteo_http import RateLimited
from app.weather_fallback import hourly_payload, soy_context


def payload(hours=24):
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    def row(stamp):
        return {'time': stamp.isoformat(), 'data': {
            'instant': {'details': {'air_temperature': 28, 'relative_humidity': 50, 'wind_speed': 5, 'apparent_air_temperature': 30}},
            'next_1_hours': {'details': {'precipitation_amount': 1}},
            'next_6_hours': {'details': {'precipitation_amount': 2, 'air_temperature_max': 31, 'air_temperature_min': 19}},
        }}
    indexed = {now + timedelta(hours=h): row(now + timedelta(hours=h)) for h in range(hours + 1)}
    first = now.replace(hour=0) + timedelta(days=1)
    for h in range(0, 7 * 24, 6):
        indexed.setdefault(first + timedelta(hours=h), row(first + timedelta(hours=h)))
    return {'geometry': {'coordinates': [-54.6428, -25.4078, 250]}, 'properties': {
        'meta': {'units': {'air_temperature': 'celsius', 'relative_humidity': '%', 'wind_speed': 'm/s', 'precipitation_amount': 'mm', 'air_temperature_max': 'celsius', 'air_temperature_min': 'celsius', 'apparent_air_temperature': 'celsius'}},
        'timeseries': [indexed[t] for t in sorted(indexed)]}}


@pytest.mark.parametrize('hazard', ['fire', 'hydric', 'health_heat'])
def test_real_forecast_units_and_forward_rain_interval_are_preserved(hazard):
    now = datetime.now(timezone.utc)
    normalized = hourly_payload(payload(), -25.4078, -54.6428)
    features, start, end, series = future_features(normalized, now, 24, hazard)
    assert len(series) == 24 and end - start == timedelta(hours=24)
    if hazard in ('fire', 'hydric'):
        assert features['rain_total_mm'] == 24
    if hazard == 'fire':
        assert features['wind_max_kmh'] == 18
    assert normalized['_provider'] == 'met-no'


def test_coarse_periods_are_not_interpolated_for_72_hour_prediction():
    normalized = hourly_payload(payload(), -25.4, -54.6)
    with pytest.raises(ValueError, match='resolución horaria completa'):
        future_features(normalized, datetime.now(timezone.utc), 72)


def test_soy_has_seven_complete_utc_days_and_keeps_unavailable_soil_and_et0_missing():
    result = soy_context(payload(), -25.4078, -54.6428, 'HTTP 429')
    assert result['timezone'] == 'UTC' and result['provider'] == 'met-no'
    assert len(result['forecast']) == 7
    assert result['forecast'][0] == {'day': (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(), 'tmax': 31, 'tmin': 19, 'precipitation_mm': 8, 'et0_mm': None}
    assert not any('soil' in key for key in result['variables'])


def test_missing_six_hour_block_does_not_become_zero_rain():
    data = payload()
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()
    for row in data['properties']['timeseries']:
        stamp = datetime.fromisoformat(row['time'])
        if stamp.date() == tomorrow and stamp.hour == 6:
            del row['data']['next_6_hours']
    result = soy_context(data, -25.4, -54.6, 'HTTP 429')
    assert result['forecast'][0]['precipitation_mm'] is None
    assert result['forecast'][0]['tmax'] is None


@pytest.mark.asyncio
async def test_prediction_switches_to_met_no_after_primary_quota(monkeypatch):
    monkeypatch.setattr(predictive_service, 'get_settings', lambda: SimpleNamespace(met_no_fallback_enabled=True))
    monkeypatch.setattr(predictive_service, '_open_meteo_forecasts', AsyncMock(side_effect=RateLimited('HTTP 429')))
    backup = AsyncMock(return_value=[payload()])
    monkeypatch.setattr(met_no, 'fetch_forecast_batch', backup)
    result = await predictive_service.forecasts_for_points([{'lat': -25.4, 'lon': -54.6}])
    assert result[0]['_provider'] == 'met-no'
    backup.assert_awaited_once_with([(-25.4, -54.6)])


@pytest.mark.asyncio
async def test_air_quality_does_not_use_weather_as_a_pm25_substitute(monkeypatch):
    monkeypatch.setattr(predictive_service, 'get_settings', lambda: SimpleNamespace(met_no_fallback_enabled=True))
    monkeypatch.setattr(predictive_service, '_open_meteo_forecasts', AsyncMock(side_effect=RateLimited('HTTP 429')))
    backup = AsyncMock()
    monkeypatch.setattr(met_no, 'fetch_forecast_batch', backup)
    with pytest.raises(RateLimited):
        await predictive_service.forecasts_for_points([{'lat': -25.4, 'lon': -54.6}], 'health_air')
    backup.assert_not_awaited()


@pytest.mark.asyncio
async def test_soy_automatically_uses_identified_backup(monkeypatch):
    from app import agro
    monkeypatch.setattr(agro, '_consultar', AsyncMock(side_effect=RateLimited('HTTP 429')))
    monkeypatch.setattr(met_no, 'fetch_forecast_batch', AsyncMock(return_value=[payload()]))
    result = await paraguay_context.load_context(-25.4078, -54.6428)
    assert result['provider'] == 'met-no' and len(result['forecast']) == 7
    assert result['variables']['temperature_2m']['value'] == 28


@pytest.mark.asyncio
async def test_duplicate_points_share_one_forecast_request(monkeypatch):
    import httpx
    monkeypatch.setattr(met_no, 'get_settings', lambda: SimpleNamespace(met_no_user_agent='Econexo contacto autorizado', pipeline_http_timeout_seconds=5))
    monkeypatch.setattr(met_no.weather_cache, 'read', AsyncMock(return_value=None))
    monkeypatch.setattr(met_no.weather_cache, 'write', AsyncMock())
    calls = []
    real_client = httpx.AsyncClient
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=payload())
    monkeypatch.setattr(met_no.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    result = await met_no.fetch_forecast_batch([(-25.4, -54.6), (-25.4, -54.6)])
    assert len(result) == 2 and len(calls) == 1
