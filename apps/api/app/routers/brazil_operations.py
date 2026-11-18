"""Organization-scoped citrus/eucalyptus operations in Mato Grosso."""
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from .. import db
from ..deps import CurrentUser,current_user,require_role,require_internal_service
from ..brazil_operations import ParcelImport,OperationsSettings,Inspection,SoilReading,AlertAction,inspection_signal
from ..brazil_alerts import municipalities
from ..brazil_delivery import enqueue,readiness
from ..rate_limit import enforce_rate_limit

router=APIRouter(prefix='/brasil/operations',tags=['brasil-operations'])

def record(row):
    result=dict(row)
    for k in ('geometry','context','satellite','evidence','recipients','payload'):
        if isinstance(result.get(k),str): result[k]=json.loads(result[k])
    return result

async def parcel(org_id, parcel_id):
    row=await db.pool().fetchrow("""SELECT id,org_id,code,name,estate,crop,area_ha,cultivar,planted_on,manager,
        ST_AsGeoJSON(geom)::json AS geometry,ST_Y(ST_PointOnSurface(geom)) AS lat,ST_X(ST_PointOnSurface(geom)) AS lon,
        context,context_at,satellite,satellite_at FROM brazil_parcels WHERE org_id=$1 AND id=$2""",org_id,parcel_id)
    if row is None: raise HTTPException(404,'Parcel not found')
    return record(row)

@router.get('/summary')
async def summary(user: CurrentUser=Depends(current_user)):
    totals=await db.pool().fetchrow("""SELECT count(*) AS parcel_count,COALESCE(sum(area_ha),0) AS mapped_ha,
        COALESCE(sum(area_ha) FILTER(WHERE crop='orange'),0) AS orange_ha,
        COALESCE(sum(area_ha) FILTER(WHERE crop='eucalyptus'),0) AS eucalyptus_ha,
        count(*) FILTER(WHERE context_at>now()-interval '1 hour' AND context->>'error' IS NULL AND context->'variables'<>'{}'::jsonb) AS recent_context,
        count(*) FILTER(WHERE satellite_at>now()-interval '1 day' AND satellite->>'status'='ok') AS recent_satellite
        FROM brazil_parcels WHERE org_id=$1""",user.org_id)
    settings=await db.pool().fetchrow('SELECT * FROM brazil_operations_settings WHERE org_id=$1',user.org_id)
    alerts=await db.pool().fetch('SELECT kind,priority,count(*) AS count FROM brazil_operations_alerts WHERE org_id=$1 AND status IN (\'open\',\'acknowledged\') GROUP BY kind,priority',user.org_id)
    return {'totals':dict(totals),'settings':record(settings) if settings else OperationsSettings().model_dump(),
            'alerts':[dict(r) for r in alerts],'services':readiness()}

@router.patch('/settings')
async def settings(body: OperationsSettings,user: CurrentUser=Depends(require_role('admin'))):
    await db.pool().execute("""INSERT INTO brazil_operations_settings(org_id,target_area_ha,enabled,fire_buffer_m,recipients)
        VALUES($1,$2,$3,$4,$5::jsonb) ON CONFLICT(org_id) DO UPDATE SET target_area_ha=$2,enabled=$3,
        fire_buffer_m=$4,recipients=$5::jsonb,updated_at=now()""",user.org_id,body.target_area_ha,body.enabled,body.fire_buffer_m,json.dumps([r.model_dump() for r in body.recipients]))
    return body

@router.get('/parcels')
async def parcels(crop: str='',q: str=Query('',max_length=100),offset: int=Query(0,ge=0),limit: int=Query(50,ge=1,le=100),user: CurrentUser=Depends(current_user)):
    rows=await db.pool().fetch("""SELECT id,code,name,estate,crop,area_ha,cultivar,manager,context_at,satellite_at,count(*) OVER() AS total
        FROM brazil_parcels WHERE org_id=$1 AND ($2='' OR crop=$2) AND ($3='' OR name ILIKE '%'||$3||'%' OR estate ILIKE '%'||$3||'%' OR code ILIKE '%'||$3||'%')
        ORDER BY estate,code,id LIMIT $4 OFFSET $5""",user.org_id,crop,q,limit,offset)
    return {'items':[dict(r) for r in rows],'total':rows[0]['total'] if rows else 0}

@router.post('/parcels/import')
async def import_parcels(body: ParcelImport,request: Request,user: CurrentUser=Depends(require_role('admin','operador'))):
    await enforce_rate_limit(request,bucket='brazil-parcel-import',limit=6,window_seconds=60)
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))",'br-import:'+str(user.org_id))
            # Validate topology before converting to geography, then enforce real state coverage.
            state=await conn.fetchval("""SELECT ST_AsGeoJSON(ST_Buffer(ST_UnaryUnion(ST_Collect(ST_GeomFromGeoJSON(f->'geometry'))),0.0001))
                FROM jsonb_array_elements($1::jsonb) f""",json.dumps(municipalities()))
            for f in body.features:
                geometry=json.dumps(f.geometry);props=f.properties
                valid=await conn.fetchval('SELECT ST_IsValid(ST_SetSRID(ST_GeomFromGeoJSON($1),4326))',geometry)
                if not valid: raise HTTPException(422,f'{props.code}: invalid polygon topology')
                info=await conn.fetchrow("""WITH g AS(SELECT ST_SetSRID(ST_GeomFromGeoJSON($1),4326) AS geom)
                    SELECT ST_Area(geom::geography)/10000 AS area,ST_CoveredBy(geom,ST_GeomFromGeoJSON($2)) AS inside FROM g""",geometry,state)
                if not info['inside'] or info['area']<=0: raise HTTPException(422,f'{props.code}: polygon must be inside Mato Grosso')
                if await conn.fetchval('SELECT EXISTS(SELECT 1 FROM brazil_parcels WHERE org_id=$1 AND code=$2)',user.org_id,props.code):
                    raise HTTPException(409,f'{props.code}: duplicate code, import cancelled')
                overlap=await conn.fetchval("""SELECT EXISTS(SELECT 1 FROM brazil_parcels WHERE org_id=$1 AND
                    ST_Intersects(geom,ST_GeomFromGeoJSON($2)) AND ST_Area(ST_Intersection(geom,ST_GeomFromGeoJSON($2))::geography)>1)""",user.org_id,geometry)
                if overlap: raise HTTPException(409,f'{props.code}: overlapping management units, import cancelled')
                await conn.execute("""INSERT INTO brazil_parcels(org_id,code,estate,name,crop,cultivar,planted_on,manager,geom,area_ha)
                    VALUES($1,$2,$3,$4,$5,$6,$7,$8,ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON($9),4326)),$10)""",
                    user.org_id,props.code,props.estate,props.name,props.crop,props.cultivar,props.planted_on,props.manager,geometry,info['area'])
            await conn.execute('INSERT INTO brazil_operations_settings(org_id) VALUES($1) ON CONFLICT DO NOTHING',user.org_id)
    return {'imported':len(body.features)}

@router.get('/parcels/{parcel_id}')
async def detail(parcel_id: UUID,user: CurrentUser=Depends(current_user)):
    data=await parcel(user.org_id,parcel_id)
    readings=await db.pool().fetch("""SELECT observed_at,source,reference,depth_cm,ph,ph_method,temperature_c,calibrated_at,
        observed_at<now()-CASE WHEN source='sensor' THEN interval '24 hours' ELSE interval '180 days' END AS stale
        FROM brazil_soil_readings WHERE org_id=$1 AND parcel_id=$2 ORDER BY observed_at DESC LIMIT 10""",user.org_id,parcel_id)
    data['soil']=[dict(r) for r in readings]
    data['inspections']=[record(r) for r in await db.pool().fetch('SELECT id,observed_at,payload FROM brazil_inspections WHERE org_id=$1 AND parcel_id=$2 ORDER BY observed_at DESC LIMIT 20',user.org_id,parcel_id)]
    return data

@router.post('/parcels/{parcel_id}/context')
async def context(parcel_id: UUID,request: Request,user: CurrentUser=Depends(current_user)):
    await enforce_rate_limit(request,bucket='brazil-ops-context',limit=12,window_seconds=60)
    from ..brazil_operations_worker import refresh_context
    await refresh_context(await parcel(user.org_id,parcel_id))
    return await detail(parcel_id,user)

@router.post('/parcels/{parcel_id}/satellite')
async def satellite(parcel_id: UUID,request: Request,user: CurrentUser=Depends(current_user)):
    await enforce_rate_limit(request,bucket='brazil-ops-satellite',limit=6,window_seconds=60)
    from ..brazil_operations_worker import refresh_satellite
    await refresh_satellite(await parcel(user.org_id,parcel_id))
    return await detail(parcel_id,user)

async def save_soil(org_id,parcel_id,body):
    await parcel(org_id,parcel_id)
    await db.pool().execute("""INSERT INTO brazil_soil_readings(org_id,parcel_id,observed_at,source,reference,depth_cm,ph,ph_method,temperature_c,calibrated_at)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) ON CONFLICT DO NOTHING""",org_id,parcel_id,body.observed_at,body.source,body.reference,body.depth_cm,body.ph,body.ph_method,body.temperature_c,body.calibrated_at)
    return {'stored':True}

@router.post('/parcels/{parcel_id}/soil')
async def soil(parcel_id: UUID,body: SoilReading,user: CurrentUser=Depends(require_role('admin','operador'))):
    if body.source!='laboratory': raise HTTPException(422,'Sensor readings require the authenticated telemetry endpoint')
    return await save_soil(user.org_id,parcel_id,body)

@router.post('/telemetry/{org_id}/{parcel_id}',dependencies=[Depends(require_internal_service)])
async def telemetry(org_id: UUID,parcel_id: UUID,body: SoilReading,request: Request):
    from ..config import get_settings
    if get_settings().internal_service_token in {'','change_me_internal_dev_secret'}:
        raise HTTPException(503,'Configure a private internal service token before sensor ingestion')
    await enforce_rate_limit(request,bucket='brazil-soil-ingest',limit=120,window_seconds=60)
    if body.source!='sensor': raise HTTPException(422,'Sensor source required')
    return await save_soil(org_id,parcel_id,body)

@router.post('/parcels/{parcel_id}/inspections')
async def inspection(parcel_id: UUID,body: Inspection,user: CurrentUser=Depends(require_role('admin','operador'))):
    p=await parcel(user.org_id,parcel_id)
    try: signal=inspection_signal(p['crop'],body)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            iid=await conn.fetchval('INSERT INTO brazil_inspections(org_id,parcel_id,created_by,observed_at,payload) VALUES($1,$2,$3,$4,$5::jsonb) RETURNING id',user.org_id,parcel_id,user.id,body.observed_at,body.model_dump_json())
            if signal:
                aid=await conn.fetchval("""INSERT INTO brazil_operations_alerts(org_id,parcel_id,event_key,kind,priority,observed_at,evidence)
                    VALUES($1,$2,$3,'pest',$4,$5,$6::jsonb) RETURNING id""",user.org_id,parcel_id,'inspection:'+str(iid),signal['priority'],body.observed_at,json.dumps({**signal,'inspection_id':str(iid),'specialist':body.specialist,'diagnosis_reference':body.diagnosis_reference,'reference':body.evidence_reference}))
                await enqueue(conn,user.org_id,[aid])
    return {'id':iid,'signal':signal}

@router.get('/alerts')
async def alerts(status: str='active',offset: int=Query(0,ge=0),user: CurrentUser=Depends(current_user)):
    rows=await db.pool().fetch("""SELECT a.*,p.name,p.code,p.estate,p.crop,p.area_ha,count(*) OVER() AS total
        FROM brazil_operations_alerts a JOIN brazil_parcels p ON p.org_id=a.org_id AND p.id=a.parcel_id
        WHERE a.org_id=$1 AND ($2='all' OR ($2='active' AND a.status IN ('open','acknowledged')) OR a.status=$2)
        ORDER BY CASE a.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END,a.observed_at DESC,a.id LIMIT 50 OFFSET $3""",user.org_id,status,offset)
    return {'items':[record(r) for r in rows],'total':rows[0]['total'] if rows else 0}

@router.patch('/alerts/{alert_id}')
async def update_alert(alert_id: UUID,body: AlertAction,user: CurrentUser=Depends(require_role('admin','operador'))):
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            aid=await conn.fetchval("""UPDATE brazil_operations_alerts SET status=$3,assigned_to=$4,resolution=$5,updated_by=$6,updated_at=now()
                WHERE org_id=$1 AND id=$2 RETURNING id""",user.org_id,alert_id,body.status,body.assigned_to,body.resolution,user.id)
            if aid is None: raise HTTPException(404,'Alert not found')
            await conn.execute('INSERT INTO brazil_alert_actions(org_id,alert_id,actor_id,payload) VALUES($1,$2,$3,$4::jsonb)',user.org_id,alert_id,user.id,body.model_dump_json())
    return {'updated':True}

@router.post('/scan')
async def scan(request: Request,user: CurrentUser=Depends(require_role('admin','operador'))):
    await enforce_rate_limit(request,bucket='brazil-ops-scan',limit=2,window_seconds=300)
    from ..brazil_operations_worker import scan_fires
    return await scan_fires(user.org_id)

@router.get('/deliveries')
async def deliveries(user: CurrentUser=Depends(require_role('admin','operador'))):
    return [dict(r) for r in await db.pool().fetch('SELECT id,alert_id,channel,recipient,status,attempts,last_error,provider_id,created_at FROM brazil_delivery_queue WHERE org_id=$1 ORDER BY created_at DESC LIMIT 100',user.org_id)]
