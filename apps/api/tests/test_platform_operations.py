from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import deps, platform_operations
from app.routers import platform


def test_operations_rejects_missing_session_and_org_admin(monkeypatch):
    app = FastAPI()
    app.include_router(platform.router)
    with TestClient(app) as client:
        assert client.get("/platform/operations").status_code == 401
        app.dependency_overrides[deps.current_user] = lambda: SimpleNamespace(platform_admin=False, role="admin")
        assert client.get("/platform/operations").status_code == 403
    assert "/platform/operations" not in app.openapi()["paths"]


@pytest.mark.asyncio
async def test_empty_data_does_not_claim_prediction_or_integration_health(monkeypatch):
    now = datetime.now(timezone.utc)
    row = dict(generated_at=now, devices_total=0, devices_stale=0,
               latest_reading_at=None, alerts_pending=0, alerts_confirmed=0,
               alerts_discarded=0, pipeline_degraded_24h=0, latest_pipeline_at=None)
    pool = SimpleNamespace(fetchrow=AsyncMock(return_value=row))
    monkeypatch.setattr(platform_operations.db, "pool", lambda: pool)
    monkeypatch.setattr(platform_operations, "get_settings", lambda: SimpleNamespace(
        pipeline_scheduler_enabled=False, mqtt_enabled=False, anomaly_enabled=True,
        firms_inline_enabled=True, nasa_firms_key="private-key", copernicus_mode="wms",
        copernicus_client_id="private-id", copernicus_client_secret="private-secret", s3_enabled=False))
    result = await platform_operations.operations_snapshot()
    assert result.metrics.latest_reading_at is None
    assert result.predictive_status == "not_validated"
    assert result.integrations[2].configured  # Configuración, no disponibilidad.
    assert not result.integrations[4].configured  # Credenciales sin Process API.
    assert "private" not in result.model_dump_json()
    assert len(result.predictive_gaps) == 5
