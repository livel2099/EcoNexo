from datetime import date, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.paraguay import SoyEvidence, evaluate, in_paraguay
from app.routers import paraguay as routes
from app.deps import CurrentUser, current_user
from app.ecocampo_satellite import Polygon


def evidence(**overrides):
    return SoyEvidence(**dict({'name':'Soja PY','lat':-25.5,'lon':-55.2,'area_ha':10,'observed_on':date.today(),'source':'Relevamiento profesional'}, **overrides))


def forecast():
    return [{'day':date.today()+timedelta(days=i),'tmax':29,'tmin':19,'precipitation_mm':0,'et0_mm':4} for i in range(7)]


def test_country_boundary_excludes_misiones_and_brazil():
    assert in_paraguay(-25.5,-55.2)
    assert not in_paraguay(-27.36,-55.90)
    assert not in_paraguay(-24,-50)
    with pytest.raises(ValidationError): evidence(lat=-27.36,lon=-55.90)


def test_unknown_is_not_favorable():
    result=evaluate(evidence(),[])
    assert result['status']=='datos_insuficientes'
    assert 'Drenaje' in result['missing']
    assert any('Pronóstico completo' in s for s in result['missing'])


def test_complete_evidence_and_bad_drainage():
    e=evidence(ph=6,soil_temperature_c=24,soil_analysis_ok=True,drainage_ok=True,water_ok=True,compaction=False,erosion=False,seed_ok=True,nodulation_plan_ok=True,pests_present=False,cultivar='Cultivar validado por asesor',sowing_date=date.today())
    assert evaluate(e,forecast())['status']=='potencial_favorable'
    assert evaluate(e.model_copy(update={'drainage_ok':False}),forecast())['status']=='condicionado'
    assert evaluate(e.model_copy(update={'observed_on':date.today()-timedelta(days=31)}),forecast())['status']=='datos_insuficientes'


@pytest.mark.parametrize('changes',[{'ph':float('nan')},{'area_ha':0},{'observed_on':date.today()+timedelta(days=1)},{'source':'   '},{'crop':'maiz'}])
def test_invalid_inputs(changes):
    with pytest.raises(ValidationError): evidence(**changes)


def test_temperature_risks_and_partial_forecast():
    daily=forecast();daily[0]['tmax']=35;daily[1]['tmin']=1
    result=evaluate(evidence(),daily)
    assert {r['factor'] for r in result['risks']} >= {'Calor previsto','Frío previsto'}
    daily[2]['precipitation_mm']=None
    assert any('Pronóstico completo' in x for x in evaluate(evidence(),daily)['missing'])


@pytest.mark.asyncio
async def test_api_missing_weather_and_organization_history(monkeypatch):
    user=CurrentUser(id=uuid4(),org_id=uuid4(),role='visualizador')
    app=FastAPI();app.include_router(routes.router)
    app.dependency_overrides[routes.require_agro_module]=lambda:user
    monkeypatch.setattr(routes,'enforce_rate_limit',AsyncMock())
    monkeypatch.setattr(routes.agro,'_consultar',AsyncMock(side_effect=RuntimeError('unavailable')))
    pool=AsyncMock();pool.fetch.return_value=[]
    monkeypatch.setattr(routes.db,'pool',lambda:pool)
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        result=await client.post('/paraguay/soja/evaluate',json=evidence().model_dump(mode='json'))
        assert result.status_code==200
        assert result.json()['weather_error']
        assert result.json()['status']=='datos_insuficientes'
        assert (await client.get('/paraguay/soja/reports')).status_code==200
        assert pool.fetch.call_args.args[1]==user.org_id
        bad=await client.post('/paraguay/soja/ndvi',json={'type':'Polygon','coordinates':[[[-50,-24],[-50.01,-24],[-50.01,-24.01],[-50,-24]]]})
        assert bad.status_code==422


@pytest.mark.asyncio
async def test_endpoints_require_authentication():
    app=FastAPI();app.include_router(routes.router)
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        assert (await client.get('/paraguay/soja/reports')).status_code==401


@pytest.mark.asyncio
async def test_viewer_cannot_save_reports():
    app=FastAPI();app.include_router(routes.router)
    app.dependency_overrides[current_user]=lambda:CurrentUser(id=uuid4(),org_id=uuid4(),role='visualizador')
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post('/paraguay/soja/reports',json={'evidence':evidence().model_dump(mode='json')})
        assert response.status_code==403


def test_invalid_satellite_geometry():
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        routes.validate_polygon(Polygon(type='Polygon',coordinates=[[(-55.2,-25.5),(-55.19,-25.49),(-55.2,-25.49),(-55.19,-25.5),(-55.2,-25.5)]]))


def test_water_balance_is_not_soil_measurement():
    result=evaluate(evidence(stage='floracion'),forecast())
    risk=next(r for r in result['risks'] if r['factor']=='Balance climático previsto negativo')
    assert 'No incluye agua almacenada' in risk['detail']
