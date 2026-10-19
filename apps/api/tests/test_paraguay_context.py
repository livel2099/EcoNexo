from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.paraguay_context import parse_context,load_context
from app.routers import paraguay as routes
from app.paraguay import SoyEvidence
from app.ecocampo_satellite import Polygon
from app.copernicus import CopernicusError


@pytest.fixture(autouse=True)
def offline_fallback(monkeypatch):
    from app import met_no
    monkeypatch.setattr(met_no, 'fetch_forecast_batch', AsyncMock(side_effect=met_no.MetNoError('Respaldo no disponible en esta prueba')))


def payload():
    now=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    return {'utc_offset_seconds':0,'timezone':'America/Asuncion','latitude':-25.4,'longitude':-55.3,'elevation':277,'current':{'time':now.isoformat(),'temperature_2m':23,'relative_humidity_2m':55,'wind_speed_10m':0,'precipitation':0},'hourly':{'time':[now.isoformat()], 'soil_temperature_6cm':[24],'soil_moisture_3_to_9cm':[.3],'soil_moisture_9_to_27cm':[.28]},'daily':{'time':[(now+timedelta(days=i)).date().isoformat() for i in range(7)],'temperature_2m_max':[27]*7,'temperature_2m_min':[17]*7,'precipitation_sum':[0]*7,'et0_fao_evapotranspiration':[4]*7}}


def test_provider_schema_maps_all_forecast_values_and_preserves_zero():
    result=parse_context(payload(),-25.4,-55.3)
    assert len(result['forecast'])==7
    assert result['forecast'][0]['tmax']==27
    assert result['forecast'][0]['precipitation_mm']==0
    assert result['variables']['soil_temperature_6cm']['value']==24
    assert result['variables']['soil_moisture_9_to_27cm']['value']==.28
    assert result['variables']['wind_speed_10m']['value']==0
    assert result['error'] is None


def test_incomplete_weather_is_not_zero_and_old_soil_is_not_current():
    data=payload();data['daily']['precipitation_sum']=[None]*7
    data['hourly']['time']=[(datetime.now(timezone.utc)-timedelta(days=4)).isoformat()]
    result=parse_context(data,-25.4,-55.3)
    assert result['error']
    assert result['forecast'][0]['precipitation_mm'] is None
    assert 'soil_temperature_6cm' not in result['variables']


@pytest.mark.asyncio
async def test_provider_quota_is_visible(monkeypatch):
    from app import agro
    monkeypatch.setattr(agro,'_consultar',AsyncMock(side_effect=RuntimeError('Open-Meteo HTTP 429')))
    result=await load_context(-25.4,-55.3)
    assert '429' in result['error'] and result['forecast']==[]


@pytest.mark.asyncio
async def test_report_includes_automatic_snapshot_without_overwriting_field_measurement(monkeypatch):
    from fastapi import Request
    from app.deps import CurrentUser
    from uuid import uuid4
    context=parse_context(payload(),-25.5,-55.2)
    monkeypatch.setattr(routes,'load_context',AsyncMock(return_value=context))
    monkeypatch.setattr(routes,'enforce_rate_limit',AsyncMock())
    body=SoyEvidence(name='Lote PY',lat=-25.5,lon=-55.2,area_ha=10,observed_on=datetime.now().date(),soil_temperature_c=15)
    report=await routes.assessment(body,Request({'type':'http'}),CurrentUser(id=uuid4(),org_id=uuid4(),role='admin'))
    assert report['evidence']['soil_temperature_c']==15
    assert report['automatic']['variables']['soil_temperature_6cm']['value']==24
    assert len(report['forecast'])==7
    assert report['satellite']['status']=='sin_poligono'
    assert report['method']=='py-soja-v2'


@pytest.mark.asyncio
async def test_satellite_failure_does_not_hide_weather(monkeypatch):
    monkeypatch.setattr(routes,'fetch_ndvi',AsyncMock(side_effect=CopernicusError('quota')))
    polygon=Polygon(type='Polygon',coordinates=[[(-55.2,-25.5),(-55.19,-25.5),(-55.19,-25.51),(-55.2,-25.5)]])
    result=await routes.report_satellite(polygon)
    assert result['status']=='no_disponible' and result['series']==[]


@pytest.mark.asyncio
async def test_provider_quota_preserves_retry_guidance_without_creating_values(monkeypatch):
    from app import agro
    from app.open_meteo_http import RateLimited
    monkeypatch.setattr(agro, '_consultar', AsyncMock(side_effect=RateLimited('Open-Meteo HTTP 429. Reintentá en 300 segundos.')))
    result = await load_context(-25.4, -55.3)
    assert '300 segundos' in result['error']
    assert result['variables'] == {} and result['forecast'] == []
