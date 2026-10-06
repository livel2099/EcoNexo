from types import SimpleNamespace

import httpx
import pytest

from app import pipeline


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,expected", [
    ({"score": 0.99, "trained": False}, 0.5),
    ({"score": 0.99}, 0.5),
    ({"score": 2, "trained": True}, 0.5),
    ({"score": "NaN", "trained": True}, 0.5),
    ({"score": "Infinity", "trained": True}, 0.5),
    ({"score": 0.87, "trained": True}, 0.87),
])
async def test_only_trained_finite_scores_contribute_to_alerts(monkeypatch, payload, expected):
    client_class = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    monkeypatch.setattr(pipeline, "get_settings", lambda: SimpleNamespace(
        anomaly_enabled=True, anomaly_service_url="http://anomaly.test"))
    monkeypatch.setattr(pipeline.httpx, "AsyncClient", lambda **kwargs: client_class(transport=transport, **kwargs))
    assert await pipeline.anomaly_score("device", "temp", 40) == expected
