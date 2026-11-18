from datetime import datetime,timedelta,timezone
from uuid import uuid4
from unittest.mock import AsyncMock,MagicMock
import json
import pytest
import httpx
from pydantic import ValidationError
from fastapi import FastAPI
from app.brazil_operations import Inspection,SoilReading,OperationsSettings,ParcelImport,inspection_signal,vegetation_signal
from app.routers import brazil_operations as routes
from app import brazil_operations_worker as worker,brazil_delivery as delivery
from app.deps import CurrentUser,current_user
from app.brazil_alerts import fire_features

NOW=datetime.now(timezone.utc)

def observation(**changes):
    return Inspection(**({'observed_at':NOW,'target':'citrus_psyllid','sampled_plants':100,'affected_plants':2,'evidence_reference':'Field photo A1'}|changes))

def features():
    return {'type':'FeatureCollection','features':[{'type':'Feature','properties':{'code':'A1','estate':'Fazenda A','name':'Talhão A1','crop':'orange'},
        'geometry':{'type':'Polygon','coordinates':[[[-55.73,-12.55],[-55.72,-12.55],[-55.72,-12.54],[-55.73,-12.55]]]}}]}

def pool_mock(monkeypatch):
    conn=MagicMock()
    for name in ('fetch','fetchval','fetchrow','execute'): setattr(conn,name,AsyncMock())
    conn.transaction.return_value.__aenter__=AsyncMock(return_value=None)
    pool=MagicMock()
    for name in ('fetch','fetchval','fetchrow','execute'): setattr(pool,name,AsyncMock())
    pool.acquire.return_value.__aenter__=AsyncMock(return_value=conn)
    monkeypatch.setattr(routes.db,'pool',lambda:pool)
    return pool,conn

def app(role='operador'):
    user=CurrentUser(id=uuid4(),org_id=uuid4(),role=role)
    application=FastAPI();application.include_router(routes.router)
    application.dependency_overrides[current_user]=lambda:user
    return application,user

def test_samples_do_not_claim_whole_estate_or_automatic_diagnosis():
    signal=inspection_signal('orange',observation())
    assert signal['sample_incidence_pct']==2
    assert signal['scope']=='sample_only' and signal['diagnosis']=='suspected'
    assert inspection_signal('orange',observation(affected_plants=0)) is None
    with pytest.raises(ValueError): inspection_signal('eucalyptus',observation())

@pytest.mark.parametrize('changes',[{'affected_plants':101},{'sampled_plants':0},{'captures':1},
    {'diagnosis':'confirmed'},{'observed_at':NOW+timedelta(days=1)},{'observed_at':NOW.replace(tzinfo=None)}])
def test_rejects_invalid_or_unsubstantiated_observations(changes):
    with pytest.raises(ValidationError): observation(**changes)

def test_trap_rate_and_expert_confirmation():
    x=observation(trap_count=4,trap_days=7,captures=28,diagnosis='confirmed',specialist='Eng. Silva',diagnosis_reference='Laudo 21')
    signal=inspection_signal('orange',x)
    assert signal['captures_per_trap_day']==1 and signal['priority']=='high'

def test_sensor_calibration_and_ph_range():
    base={'observed_at':NOW,'source':'sensor','reference':'sensor-001','depth_cm':10,'ph':5.8,'ph_method':'electrode','calibrated_at':NOW-timedelta(days=5)}
    assert SoilReading(**base).ph==5.8
    for patch in ({'ph':15},{'ph':float('nan')},{'calibrated_at':None},{'calibrated_at':NOW-timedelta(days=31)},{'calibrated_at':NOW+timedelta(hours=1)}):
        with pytest.raises(ValidationError): SoilReading(**(base|patch))

def test_recipient_consent_dedup_and_phone_validation():
    assert OperationsSettings().enabled is False
    assert OperationsSettings().target_area_ha==450000
    for recipients in ([{'channel':'whatsapp','address':'123','consent':True}],
        [{'channel':'email','address':'person@example.com','consent':False}],
        [{'channel':'email','address':'person@example.com','consent':True}]*2):
        with pytest.raises(ValidationError): OperationsSettings(recipients=recipients)

@pytest.mark.parametrize('geometry',[{'type':'Point','coordinates':[0,0]},{'type':'Polygon','coordinates':None},{'type':'Polygon','coordinates':[None]},
    {'type':'Polygon','coordinates':[[[0,0],[1,0],[0,1],[0,0]]]}])
def test_rejects_malformed_or_outside_geometry(geometry):
    data=features();data['features'][0]['geometry']=geometry
    with pytest.raises(ValidationError): ParcelImport.model_validate(data)

def test_no_vegetation_alert_from_missing_cloudy_old_or_increasing_data():
    series=[{'day':(NOW-timedelta(days=4-i)).date().isoformat(),'ndvi':v,'valid_pixel_pct':90} for i,v in enumerate([.8,.82,.81,.5])]
    assert vegetation_signal(series)['diagnosis']=='unconfirmed_anomaly'
    assert vegetation_signal(series[:3]) is None
    assert vegetation_signal([r|{'valid_pixel_pct':20} for r in series]) is None
    assert vegetation_signal([r|{'ndvi':.8} for r in series]) is None
    assert vegetation_signal([r|{'day':(NOW-timedelta(days=30-i)).date().isoformat()} for i,r in enumerate(series)]) is None

def test_fires_near_state_boundary_can_be_evaluated_for_perimeter():
    csv='latitude,longitude,acq_date,acq_time\n-18.3,-55.7,2026-11-18,1200\n'
    assert fire_features(csv,'VIIRS_NOAA20_NRT')[0]==[]
    assert len(fire_features(csv,'VIIRS_NOAA20_NRT',clip_to_state=False)[0])==1

@pytest.mark.asyncio
async def test_other_tenant_parcel_returns_404(monkeypatch):
    pool,_=pool_mock(monkeypatch);pool.fetchrow.return_value=None
    application,user=app();pid=uuid4()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application),base_url='http://test') as c:
        r=await c.get('/brasil/operations/parcels/'+str(pid))
    assert r.status_code==404
    assert pool.fetchrow.call_args.args[1:]==(user.org_id,pid)

@pytest.mark.asyncio
async def test_viewer_cannot_import_edit_settings_or_record_evidence(monkeypatch):
    pool,_=pool_mock(monkeypatch);application,_=app('visualizador')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application),base_url='http://test') as c:
        for path,body,method in [('/parcels/import',features(),'post'),('/settings',OperationsSettings().model_dump(),'patch'),
                               ('/parcels/'+str(uuid4())+'/inspections',observation().model_dump(mode='json'),'post')]:
            r=await getattr(c,method)('/brasil/operations'+path,json=body)
            assert r.status_code==403
    pool.execute.assert_not_called()

@pytest.mark.asyncio
async def test_import_topology_error_rolls_back(monkeypatch):
    pool,conn=pool_mock(monkeypatch);conn.fetchval.side_effect=['{}',False]
    monkeypatch.setattr(routes,'enforce_rate_limit',AsyncMock())
    application,_=app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application),base_url='http://test') as c:
        r=await c.post('/brasil/operations/parcels/import',json=features())
    assert r.status_code==422
    assert not any('INSERT INTO brazil_parcels' in x.args[0] for x in conn.execute.call_args_list)
    assert conn.transaction.return_value.__aexit__.call_args.args[0] is not None

@pytest.mark.asyncio
async def test_missing_firms_configuration_never_creates_detections(monkeypatch):
    monkeypatch.setattr(worker,'get_settings',lambda:MagicMock(nasa_firms_key='',firms_inline_enabled=True))
    result=await worker.fire_feed()
    assert result['status']=='not_configured' and result['features']==[]

@pytest.mark.asyncio
async def test_fire_scan_uses_tenant_spatial_join_and_durable_dedup(monkeypatch):
    pool,conn=pool_mock(monkeypatch);conn.fetchval.return_value=True;conn.fetch.return_value=[]
    feed={'status':'ok','features':[{'type':'Feature','properties':{},'geometry':{'type':'Point','coordinates':[-55.7,-12.5]}}],'sources':[]}
    org=uuid4();result=await worker.scan_fires(org,feed)
    sql=conn.fetch.call_args.args[0]
    assert 'ST_DWithin' in sql and 'ON CONFLICT(org_id,parcel_id,event_key) DO NOTHING' in sql
    assert conn.fetch.call_args.args[1]==org and result['created']==0

@pytest.mark.asyncio
async def test_revoked_recipient_is_cancelled_without_sending(monkeypatch):
    pool,conn=pool_mock(monkeypatch)
    conn.fetchrow.side_effect=[{'id':uuid4(),'enabled':False,'recipients':'[]','channel':'email','recipient':'x@example.com'},None]
    monkeypatch.setattr(delivery,'readiness',lambda:{'email':True,'whatsapp':False})
    send=AsyncMock();monkeypatch.setattr(delivery,'send',send)
    await delivery.dispatch_batch()
    send.assert_not_called()
    assert any("status='cancelled'" in x.args[0] for x in conn.execute.call_args_list)

@pytest.mark.asyncio
async def test_ambiguous_delivery_is_not_automatically_retried(monkeypatch):
    pool,conn=pool_mock(monkeypatch);qid=uuid4()
    conn.fetchrow.side_effect=[{'id':qid,'enabled':True,'attempts':0,'recipients':json.dumps([{'channel':'email','address':'x@example.com','consent':True}]),'channel':'email','recipient':'x@example.com'},None]
    monkeypatch.setattr(delivery,'readiness',lambda:{'email':True,'whatsapp':False})
    monkeypatch.setattr(delivery,'send',AsyncMock(side_effect=TimeoutError()))
    await delivery.dispatch_batch()
    assert pool.execute.call_args.args[1:]==(qid,'uncertain',None,'provider_result_unknown')

@pytest.mark.asyncio
async def test_alert_action_is_scoped_and_audited(monkeypatch):
    pool,conn=pool_mock(monkeypatch);aid=uuid4();conn.fetchval.return_value=aid
    application,user=app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application),base_url='http://test') as c:
        r=await c.patch('/brasil/operations/alerts/'+str(aid),json={'status':'acknowledged','assigned_to':'Brigada A','resolution':'Visita programada para verificar'})
    assert r.status_code==200
    assert conn.fetchval.call_args.args[1:3]==(user.org_id,aid)
    assert 'INSERT INTO brazil_alert_actions' in conn.execute.call_args.args[0]
