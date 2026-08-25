from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.deps import require_internal_service


@pytest.mark.asyncio
async def test_internal_service_token_requires_an_exact_match(monkeypatch) -> None:
    token = "t" * 64
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", token)
    get_settings.cache_clear()
    try:
        with pytest.raises(HTTPException) as failure:
            await require_internal_service("incorrecto")
        assert failure.value.status_code == 401
        await require_internal_service(token)
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_lifespan_starts_the_configured_pipeline_scheduler(monkeypatch) -> None:
    import app.main as main

    scheduler_started = asyncio.Event()

    async def connect() -> None:
        return None

    async def disconnect() -> None:
        return None

    async def background_worker(stop: asyncio.Event) -> None:
        await stop.wait()

    async def scheduler(stop: asyncio.Event) -> None:
        scheduler_started.set()
        await stop.wait()

    monkeypatch.setattr(main.db, "connect", connect)
    monkeypatch.setattr(main.db, "disconnect", disconnect)
    monkeypatch.setattr(main, "mqtt_bridge", background_worker)
    monkeypatch.setattr(main, "pipeline_scheduler", scheduler)
    monkeypatch.setattr(main.s, "pipeline_scheduler_enabled", True)

    async with main.lifespan(main.app):
        await asyncio.wait_for(scheduler_started.wait(), timeout=0.5)
