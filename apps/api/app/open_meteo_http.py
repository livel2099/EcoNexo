"""Bounded, process-local cache and shared Open-Meteo rate-limit backoff."""
from __future__ import annotations

import asyncio
import hashlib
import math
import time
from collections import OrderedDict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit

import httpx

from . import weather_cache

_cache: OrderedDict = OrderedDict()
_cooldowns: OrderedDict = OrderedDict()
_lock = asyncio.Lock()


class RateLimited(RuntimeError):
    pass


def customer_url(url: str, api_key: str) -> str:
    parts = urlsplit(url)
    hosts = {"api.open-meteo.com": "customer-api.open-meteo.com",
             "archive-api.open-meteo.com": "customer-archive-api.open-meteo.com"}
    if api_key and parts.netloc in hosts:
        return urlunsplit(parts._replace(netloc=hosts[parts.netloc]))
    return url


def retry_seconds(value: str | None) -> float:
    try:
        seconds = float(value or "300")
    except ValueError:
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            seconds = 300
    return max(1, seconds) if math.isfinite(seconds) else 300


async def get_response(client, url: str, params: dict, ttl: float):
    # Cache keys include credentials, hashed so keys never retain a plain secret.
    key = hashlib.sha256(repr((url, sorted(params.items()))).encode()).hexdigest()
    scope = (urlsplit(url).netloc, hashlib.sha256(str(params.get("apikey", "")).encode()).hexdigest())
    async with _lock:
        now = time.monotonic()
        cached = _cache.get(key)
        if cached and cached[0] > now:
            _cache.move_to_end(key)
            return cached[1]
        _cache.pop(key, None)
        saved = await weather_cache.read("response:" + key)
        # Lista: respuesta de Open-Meteo con varias coordenadas en una consulta.
        if isinstance(saved, (dict, list)):
            return httpx.Response(200, json=saved)
        cooldown_key = "cooldown:" + hashlib.sha256(repr(scope).encode()).hexdigest()
        paused = await weather_cache.read(cooldown_key)
        if isinstance(paused, dict) and isinstance(paused.get("until"), (float, int)):
            remaining = paused["until"] - time.time()
            if remaining > 0:
                raise RateLimited(f"Open-Meteo HTTP 429 (límite de consultas). Reintentá en {math.ceil(remaining)} segundos.")
        until = _cooldowns.get(scope, 0)
        if until > now:
            raise RateLimited(f"Open-Meteo HTTP 429 (límite de consultas). Reintentá en {math.ceil(until - now)} segundos.")
        _cooldowns.pop(scope, None)
        response = await client.get(url, params=params)
        if response.status_code == 429:
            delay = retry_seconds(response.headers.get("retry-after"))
            _cooldowns[scope] = time.monotonic() + delay
            await weather_cache.write(cooldown_key, {"until": time.time() + delay}, delay)
            if len(_cooldowns) > 128:
                _cooldowns.popitem(last=False)
            raise RateLimited(f"Open-Meteo HTTP 429 (límite de consultas). Reintentá en {math.ceil(delay)} segundos."
                              + (" Configurá OPEN_METEO_API_KEY si disponés de un plan comercial." if not params.get("apikey") else ""))
        if response.status_code == 200:
            payload = response.json()  # Never cache an invalid response body.
            if isinstance(payload, (dict, list)):
                await weather_cache.write("response:" + key, payload, ttl)
            _cache[key] = (time.monotonic() + ttl, response)
            if len(_cache) > 128:
                _cache.popitem(last=False)
        return response
