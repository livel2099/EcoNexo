from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.routers import brazil


def collection():
    return {"type": "FeatureCollection", "features": [], "numberMatched": 0}


@pytest.mark.asyncio
async def test_deter_retries_workspace_endpoint():
    urls = []
    def handler(request):
        urls.append(str(request.url))
        if len(urls) == 1:
            return httpx.Response(503, text="temporarily unavailable")
        assert request.url.params["count"] == "250"
        assert "CICATRIZ_DE_QUEIMADA" in request.url.params["CQL_FILTER"]
        return httpx.Response(200, json=collection())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await brazil.deter(client, "deter-amz:deter_amz", "INPE", "2026-10-18")
    assert result["status"] == "ok"
    assert len(urls) == 2 and "/deter-amz/wfs?" in urls[1]
    assert result["queried_at"]


@pytest.mark.asyncio
async def test_deter_invalid_response_is_not_zero_alerts():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="<html>unavailable</html>"))) as client:
        result = await brazil.deter(client, "deter-amz:deter_amz", "INPE", "2026-10-18")
    assert result["status"] == "unavailable"
    assert "respuesta inválida" in result["message"]


@pytest.mark.asyncio
async def test_deter_reports_http_error():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(502))) as client:
        result = await brazil.deter(client, "deter-amz:deter_amz", "INPE", "2026-10-18")
    assert result["status"] == "unavailable"
    assert "HTTP 502" in result["message"]


def test_last_good_keeps_original_timestamp_and_expires(monkeypatch):
    monkeypatch.setattr(brazil, "_last_good", {})
    now = datetime.now(timezone.utc)
    good = {"source": "INPE", "status": "ok", "features": [{"id": "test"}], "message": "Datos"}
    brazil.preserve_last_good([good], now)
    bad = {"source": "INPE", "status": "unavailable", "features": [], "message": "HTTP 502"}
    result = brazil.preserve_last_good([bad], now + timedelta(minutes=5))[0]
    assert result["status"] == "stale"
    assert result["features"] == good["features"]
    assert result["queried_at"] == now.isoformat()
    assert brazil.preserve_last_good([bad], now + timedelta(days=1))[0]["status"] == "unavailable"
