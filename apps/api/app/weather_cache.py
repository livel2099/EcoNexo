"""Best-effort PostgreSQL cache of public weather data, shared across restarts."""
from __future__ import annotations
import json
import logging
from typing import Any

from . import db

log = logging.getLogger(__name__)


async def read(key: str):
    try:
        pool = db.pool()
    except RuntimeError:
        return None
    try:
        value = await pool.fetchval(
            "SELECT payload FROM weather_cache WHERE cache_key=$1 AND expires_at > now()", key,
        )
        return json.loads(value) if isinstance(value, str) else value
    except Exception as exc:
        log.warning("Weather cache read unavailable: %s", type(exc).__name__)
        return None


async def write(key: str, payload: Any, ttl: float):
    try:
        pool = db.pool()
    except RuntimeError:
        return
    try:
        await pool.execute("DELETE FROM weather_cache WHERE expires_at <= now()")
        await pool.execute(
            """INSERT INTO weather_cache(cache_key,payload,expires_at)
               VALUES ($1,$2::jsonb,now() + make_interval(secs => $3))
               ON CONFLICT (cache_key) DO UPDATE SET payload=EXCLUDED.payload,
                 expires_at=EXCLUDED.expires_at,updated_at=now()""",
            key, json.dumps(payload, allow_nan=False), float(ttl),
        )
    except Exception as exc:
        log.warning("Weather cache write unavailable: %s", type(exc).__name__)
