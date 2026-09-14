from unittest.mock import AsyncMock

import httpx
import pytest

from app import open_meteo_http as weather


@pytest.mark.asyncio
async def test_cache_and_expiry(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(weather.time, "monotonic", lambda: clock[0])
    response = httpx.Response(200, json={"current": {"temperature_2m": 20}})
    client = AsyncMock()
    client.get.return_value = response
    for _ in range(2):
        assert await weather.get_response(client, "https://api.open-meteo.com/v1/forecast", {}, 60) is response
    assert client.get.await_count == 1
    clock[0] += 61
    await weather.get_response(client, "https://api.open-meteo.com/v1/forecast", {}, 60)
    assert client.get.await_count == 2


@pytest.mark.asyncio
async def test_cooldown_applies_to_other_coordinates_until_retry_after(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(weather.time, "monotonic", lambda: clock[0])
    client = AsyncMock()
    client.get.side_effect = [httpx.Response(429, headers={"retry-after": "3600"}), httpx.Response(200, json={})]
    for latitude in ["-27", "-26"]:
        with pytest.raises(weather.RateLimited, match="3600"):
            await weather.get_response(client, "https://api.open-meteo.com/v1/forecast", {"latitude": latitude}, 60)
    assert client.get.await_count == 1
    clock[0] += 3601
    await weather.get_response(client, "https://api.open-meteo.com/v1/forecast", {}, 60)
    assert client.get.await_count == 2


def test_commercial_routing_preserves_custom_urls():
    assert weather.customer_url("https://api.open-meteo.com/v1/forecast", "key") == "https://customer-api.open-meteo.com/v1/forecast"
    assert weather.customer_url("https://archive-api.open-meteo.com/v1/archive", "key") == "https://customer-archive-api.open-meteo.com/v1/archive"
    assert weather.customer_url("https://api.open-meteo.com/v1/forecast", "") == "https://api.open-meteo.com/v1/forecast"
    assert weather.customer_url("https://custom.test/forecast", "key") == "https://custom.test/forecast"
