import os
import sys

# permite `from app...` al correr pytest desde apps/api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import asyncio
import pytest


@pytest.fixture(autouse=True)
def isolated_weather_cache(monkeypatch):
    from app import open_meteo_http
    open_meteo_http._cache.clear()
    open_meteo_http._cooldowns.clear()
    monkeypatch.setattr(open_meteo_http, "_lock", asyncio.Lock())
