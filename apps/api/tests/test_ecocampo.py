from datetime import date, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.ecocampo import FieldEvidence, assess
from app.ecocampo_satellite import Polygon, parse_statistics
from app.subscriptions import PLAN_DEFINITIONS
from app.routers import agro as routes
from app.deps import CurrentUser, current_user


def evidence(**kwargs):
    return FieldEvidence(**{"observed_on": date.today(), "source": "Informe de campo", **kwargs})


def test_missing_is_not_safe():
    result = assess(evidence(), 10)
    assert result["status"] == "datos_insuficientes"
    assert result["yield_t_ha"] is None
    assert result["estimated_animals"] is None


@pytest.mark.parametrize("changes", [{"ndvi": 0.8}, {"ndvi": 0.8, "valid_pixel_pct": 69}, {"ndvi": 0.8, "valid_pixel_pct": 100, "observed_on": date.today()-timedelta(days=31)}])
def test_clouds_missing_quality_and_old_data_are_not_usable(changes):
    assert not assess(evidence(**changes), 10)["ndvi_usable"]


def test_vegetation_is_not_yield_or_forage():
    result = assess(evidence(ndvi=0.9, valid_pixel_pct=100, baseline_ndvi=0.7), 10)
    assert result["yield_t_ha"] is None
    assert result["estimated_animals"] is None
    assert result["status"] != "potencial_favorable"


def test_forage_budget_and_excess_demand():
    result = assess(evidence(forage_verified=True, dry_matter_kg_ha=1000, utilization_pct=50, animal_demand_kg_day=10, grazing_days=100, herd_size=6), 10)
    assert result["estimated_animals"] == 5
    assert any("Demanda" in r["factor"] for r in result["risks"])


def test_zero_forage_is_zero_capacity():
    assert assess(evidence(forage_verified=True, dry_matter_kg_ha=0, utilization_pct=50, animal_demand_kg_day=10, grazing_days=100), 10)["estimated_animals"] == 0


@pytest.mark.parametrize("changes", [{"ndvi": float("nan")}, {"animal_demand_kg_day": 0}, {"observed_on": date.today()+timedelta(days=1)}, {"source": "   "}, {"valid_pixel_pct": 101}])
def test_invalid_evidence_rejected(changes):
    with pytest.raises(ValidationError):
        evidence(**changes)


def test_water_risk_not_hidden_by_green_ndvi():
    assert assess(evidence(ndvi=0.9, valid_pixel_pct=100, water_suitable=False), 10)["status"] == "condicionado"


def test_bare_surface_not_favorable():
    assert assess(evidence(ndvi=-0.1, valid_pixel_pct=100), 10)["status"] == "condicionado"


def test_polygon_rejects_unclosed_and_excessive_area():
    for coords in [[[[0, 0], [0, 0.01], [0.01, 0.01], [0.01, 0]]], [[[0, 0], [0, 1], [1, 1], [0, 0]]]]:
        with pytest.raises(ValidationError):
            Polygon(type="Polygon", coordinates=coords)


def test_missing_satellite_pixels_never_become_zero_ndvi():
    def item(mean, missing):
        return {"interval": {"from": "2026-09-01T00:00:00Z"}, "outputs": {"ndvi": {"bands": {"B0": {"stats": {"sampleCount": 100, "noDataCount": missing, "mean": mean}}}}}}
    assert parse_statistics({"data": [item(0, 100), item(float("nan"), 0)]}) == []
    assert parse_statistics({"data": [item(0.6, 20)]})[0]["valid_pixel_pct"] == 80


def test_productor_price_and_entitlement():
    plan = PLAN_DEFINITIONS["agro_productor"]
    assert plan["price_min_usd"] == plan["price_max_usd"] == 400
    assert plan["billing_period"] == "monthly"
    assert "agro" in plan["entitlements"]["included_modules"]


@pytest.mark.asyncio
async def test_foreign_lot_is_404_and_no_evidence_saved(monkeypatch):
    user = CurrentUser(uuid4(), uuid4(), "admin")
    pool = AsyncMock()
    pool.fetchrow.return_value = None
    monkeypatch.setattr(routes.db, "pool", lambda: pool)
    monkeypatch.setattr(routes, "require_ecocampo_module", AsyncMock())
    lot_id = uuid4()
    with pytest.raises(HTTPException) as exc:
        await routes.field_assessment(lot_id, evidence(), user)
    assert exc.value.status_code == 404
    assert pool.fetchrow.call_args.args[1:] == (lot_id, user.org_id)
    assert pool.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_expired_license_blocks_assessment(monkeypatch):
    monkeypatch.setattr(routes, "require_active_subscription", AsyncMock(side_effect=HTTPException(402, "Vencida")))
    with pytest.raises(HTTPException) as exc:
        await routes.field_assessment(uuid4(), evidence(), CurrentUser(uuid4(), uuid4(), "admin"))
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_reader_cannot_write_assessment():
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[current_user] = lambda: CurrentUser(uuid4(), uuid4(), "lector")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/agro/lots/{uuid4()}/ecocampo", json=evidence().model_dump(mode="json"))
    assert response.status_code == 403
@pytest.mark.asyncio
async def test_satellite_request_uses_polygon_and_masks_clouds(monkeypatch):
    from app import ecocampo_satellite as satellite
    import httpx
    captured = []
    async def handler(request):
        import json
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"status": "OK", "data": []})
    real_client = httpx.AsyncClient
    monkeypatch.setattr(satellite, "access_token", AsyncMock(return_value="test-token"))
    monkeypatch.setattr(satellite.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    polygon = Polygon(type="Polygon", coordinates=[[(-55.9,-27.4),(-55.9,-27.39),(-55.89,-27.39),(-55.9,-27.4)]])
    result = await satellite.fetch_ndvi(polygon)
    assert result["series"] == []
    assert captured[0]["input"]["bounds"]["geometry"]["type"] == "Polygon"
    assert captured[0]["input"]["data"][0]["type"] == "sentinel-2-l2a"
    assert "SCL" in captured[0]["aggregation"]["evalscript"]


@pytest.mark.asyncio
async def test_satellite_provider_failure_is_not_fabricated(monkeypatch):
    from app import ecocampo_satellite as satellite
    from app.copernicus import CopernicusError
    import httpx
    real_client = httpx.AsyncClient
    monkeypatch.setattr(satellite, "access_token", AsyncMock(return_value="test-token"))
    monkeypatch.setattr(satellite.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(lambda req: httpx.Response(429)), **kw))
    polygon = Polygon(type="Polygon", coordinates=[[(-55.9,-27.4),(-55.9,-27.39),(-55.89,-27.39),(-55.9,-27.4)]])
    with pytest.raises(CopernicusError):
        await satellite.fetch_ndvi(polygon)

@pytest.mark.asyncio
async def test_ecocampo_plan_does_not_require_agro_module(monkeypatch):
    user = CurrentUser(uuid4(), uuid4(), "admin")
    monkeypatch.setattr(routes, "require_active_subscription", AsyncMock())
    included = AsyncMock(return_value=True)
    monkeypatch.setattr(routes, "module_included_by_plan", included)
    assert await routes.require_ecocampo_module(user) is user
    included.assert_awaited_once_with(user.org_id, "ecocampo")


@pytest.mark.asyncio
async def test_agro_only_does_not_grant_ecocampo(monkeypatch):
    monkeypatch.setattr(routes, "require_active_subscription", AsyncMock())
    monkeypatch.setattr(routes, "module_included_by_plan", AsyncMock(return_value=False))
    pool = AsyncMock()
    pool.fetchval.return_value = False
    monkeypatch.setattr(routes.db, "pool", lambda: pool)
    with pytest.raises(HTTPException) as exc:
        await routes.require_ecocampo_module(CurrentUser(uuid4(), uuid4(), "admin"))
    assert exc.value.status_code == 402


def test_independent_routes_and_both_producer_modules():
    paths = {route.path for route in routes.ecocampo_router.routes}
    assert {"/ecocampo/lots", "/ecocampo/lots/{lot_id}/assessments", "/ecocampo/lots/{lot_id}/ndvi"} <= paths
    assert {"agro", "ecocampo"} <= set(PLAN_DEFINITIONS["agro_productor"]["entitlements"]["included_modules"])
