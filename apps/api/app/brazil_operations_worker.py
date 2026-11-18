"""Bounded background work; spatial joins run in PostGIS, never in the browser."""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
import httpx
from pydantic import ValidationError
from . import db
from .config import get_settings
from .brazil_alerts import fire_features
from .brazil_delivery import enqueue,dispatch_batch
from .brazil_operations import vegetation_signal
from .brazil_soy_context import load_context
from .ecocampo_satellite import Polygon,fetch_ndvi
from .copernicus import CopernicusError

log=logging.getLogger('econexo.brazil.operations')

async def fire_feed():
    s=get_settings()
    if not s.nasa_firms_key or not s.firms_inline_enabled:
        return {'status':'not_configured','features':[],'sources':[]}
    sources=[];features=[]
    async with httpx.AsyncClient(timeout=25) as client:
        for source in ('VIIRS_NOAA20_NRT','VIIRS_NOAA21_NRT'):
            try:
                response=await client.get(f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{s.nasa_firms_key}/{source}/-61.9,-18.5,-49.7,-6.7/2')
                response.raise_for_status()
                rows,skipped=fire_features(response.text,source,clip_to_state=False)
                cutoff=datetime.now(timezone.utc)-timedelta(hours=48)
                rows=[f for f in rows if cutoff<=datetime.fromisoformat(f['properties']['observed_at'])<=datetime.now(timezone.utc)+timedelta(minutes=5)]
                sources.append({'source':source,'status':'partial' if skipped or len(rows)>20000 else 'ok','skipped':skipped,'queried_at':datetime.now(timezone.utc).isoformat()})
                features.extend(rows[:20000])
            except (httpx.HTTPError,ValueError,KeyError,TypeError):
                sources.append({'source':source,'status':'unavailable','queried_at':datetime.now(timezone.utc).isoformat()})
    return {'status':'ok' if all(s['status']=='ok' for s in sources) else 'partial' if any(s['status']!='unavailable' for s in sources) else 'unavailable','features':features,'sources':sources}

async def scan_fires(org_id,feed=None):
    feed=feed if feed is not None else await fire_feed()
    created=0
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval('SELECT pg_try_advisory_xact_lock(hashtext($1))','br-scan:'+str(org_id)):
                return {'status':'already_running','created':0}
            await conn.execute('INSERT INTO brazil_operations_settings(org_id) VALUES($1) ON CONFLICT DO NOTHING',org_id)
            for start in range(0,len(feed['features']),1000):
                # The geography GiST index prunes parcels outside the configured perimeter.
                ids=await conn.fetch("""WITH input AS (
                    SELECT f->'properties' AS prop,ST_SetSRID(ST_GeomFromGeoJSON(f->'geometry'),4326) AS point
                    FROM jsonb_array_elements($2::jsonb) f
                ), inserted AS (
                    INSERT INTO brazil_operations_alerts(org_id,parcel_id,event_key,kind,priority,observed_at,evidence)
                    SELECT p.org_id,p.id,'firms:'||(i.prop->>'id'),'fire',
                        CASE WHEN ST_Covers(p.geom,i.point) THEN 'critical' ELSE 'high' END,
                        (i.prop->>'observed_at')::timestamptz,
                        jsonb_build_object('source',i.prop->>'source','confidence',i.prop->>'confidence','diagnosis','thermal_anomaly',
                            'lat',ST_Y(i.point),'lon',ST_X(i.point),'distance_m',round(ST_Distance(p.geom::geography,i.point::geography)::numeric),
                            'inside',ST_Covers(p.geom,i.point),'requires_field_review',true)
                    FROM input i JOIN brazil_parcels p ON p.org_id=$1
                    JOIN brazil_operations_settings s ON s.org_id=p.org_id
                    WHERE ST_DWithin(p.geom::geography,i.point::geography,s.fire_buffer_m)
                    ON CONFLICT(org_id,parcel_id,event_key) DO NOTHING RETURNING id
                ) SELECT id FROM inserted""",org_id,json.dumps(feed['features'][start:start+1000]))
                created+=len(ids)
                await enqueue(conn,org_id,[r['id'] for r in ids])
            await conn.execute('UPDATE brazil_operations_settings SET last_scan_at=now(),last_scan_status=$2 WHERE org_id=$1',org_id,feed['status'])
    return {'status':feed['status'],'created':created,'sources':feed['sources']}

async def refresh_context(p):
    if p.get('context_at') and p['context_at']>datetime.now(timezone.utc)-timedelta(minutes=15): return
    context=await load_context(p['lat'],p['lon'])
    await db.pool().execute('UPDATE brazil_parcels SET context=$3::jsonb,context_at=now() WHERE org_id=$1 AND id=$2',p['org_id'],p['id'],json.dumps(context,default=str))

async def refresh_satellite(p):
    if p.get('satellite_at') and p['satellite_at']>datetime.now(timezone.utc)-timedelta(hours=12): return
    geometry=p['geometry']
    if isinstance(geometry,str): geometry=json.loads(geometry)
    if geometry['type']=='MultiPolygon' and len(geometry['coordinates'])==1:
        geometry={'type':'Polygon','coordinates':geometry['coordinates'][0]}
    try:
        polygon=Polygon.model_validate(geometry)
        result=await fetch_ndvi(polygon)
        result['status']='ok' if result['series'] else 'no_observations'
    except ValidationError: result={'status':'subdivide_required','series':[]}
    except (CopernicusError,httpx.HTTPError,TimeoutError): result={'status':'unavailable','series':[]}
    signal=vegetation_signal(result['series'])
    result['screening']=signal
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            await conn.execute('UPDATE brazil_parcels SET satellite=$3::jsonb,satellite_at=now() WHERE org_id=$1 AND id=$2',p['org_id'],p['id'],json.dumps(result))
            if signal:
                aid=await conn.fetchval("""INSERT INTO brazil_operations_alerts(org_id,parcel_id,event_key,kind,priority,observed_at,evidence)
                    VALUES($1,$2,$3,'vegetation','medium',$4,$5::jsonb) ON CONFLICT(org_id,parcel_id,event_key) DO NOTHING RETURNING id""",
                    p['org_id'],p['id'],'ndvi:'+signal['day'],datetime.fromisoformat(signal['day']).replace(tzinfo=timezone.utc),json.dumps(signal))
                if aid: await enqueue(conn,p['org_id'],[aid])

async def cycle():
    # Session advisory lock prevents competing API replicas from doing the same cycle.
    async with db.pool().acquire() as lock:
        if not await lock.fetchval('SELECT pg_try_advisory_lock(1450012345)'): return
        try:
            orgs=await db.pool().fetch("""SELECT s.org_id FROM brazil_operations_settings s
                JOIN organizations o ON o.id=s.org_id JOIN organization_subscriptions sub ON sub.org_id=s.org_id
                WHERE s.enabled AND o.is_active AND o.access_status='approved' AND sub.status IN ('active','trial')
                AND (sub.expires_at IS NULL OR sub.expires_at>now())
                ORDER BY last_scan_at NULLS FIRST LIMIT 50""")
            if orgs:
                feed=await fire_feed()
                for row in orgs: await scan_fires(row['org_id'],feed)
        finally: await lock.execute('SELECT pg_advisory_unlock(1450012345)')

async def delivery_cycle():
    async with db.pool().acquire() as lock:
        if not await lock.fetchval('SELECT pg_try_advisory_lock(1450012347)'): return
        try: await dispatch_batch()
        finally: await lock.execute('SELECT pg_advisory_unlock(1450012347)')

async def enrichment_cycle():
    # Separate worker: slow imagery/weather calls cannot delay fire polling.
    async with db.pool().acquire() as lock:
        if not await lock.fetchval('SELECT pg_try_advisory_lock(1450012346)'): return
        try:
            rows=await db.pool().fetch("""SELECT p.id,p.org_id,ST_Y(ST_PointOnSurface(p.geom)) AS lat,ST_X(ST_PointOnSurface(p.geom)) AS lon,context_at
                FROM brazil_parcels p JOIN brazil_operations_settings s ON s.org_id=p.org_id
                JOIN organizations o ON o.id=s.org_id JOIN organization_subscriptions sub ON sub.org_id=s.org_id
                WHERE s.enabled AND o.is_active AND o.access_status='approved' AND sub.status IN ('active','trial')
                AND (sub.expires_at IS NULL OR sub.expires_at>now()) AND (context_at IS NULL OR context_at<now()-interval '1 hour')
                ORDER BY context_at NULLS FIRST,p.id LIMIT 12""")
            for row in rows:
                try: await refresh_context(dict(row))
                except Exception: log.warning('Brazil weather batch item failed')
            s=get_settings()
            if s.copernicus_client_id and s.copernicus_client_secret:
                rows=await db.pool().fetch("""SELECT p.id,p.org_id,ST_AsGeoJSON(p.geom) AS geometry,satellite_at
                    FROM brazil_parcels p JOIN brazil_operations_settings s ON s.org_id=p.org_id
                    JOIN organizations o ON o.id=s.org_id JOIN organization_subscriptions sub ON sub.org_id=s.org_id
                    WHERE s.enabled AND o.is_active AND o.access_status='approved' AND sub.status IN ('active','trial')
                    AND (sub.expires_at IS NULL OR sub.expires_at>now()) AND p.crop IN ('orange','eucalyptus') AND (satellite_at IS NULL OR satellite_at<now()-interval '1 day')
                    ORDER BY satellite_at NULLS FIRST,p.id LIMIT 3""")
                for row in rows:
                    try: await refresh_satellite(dict(row))
                    except Exception: log.warning('Brazil satellite batch item failed')
        finally: await lock.execute('SELECT pg_advisory_unlock(1450012346)')

async def operations_scheduler(stop):
    async def loop(work,delay):
        while not stop.is_set():
            try: await work()
            except asyncio.CancelledError: raise
            except Exception: log.exception('Brazil operations cycle failed; check migration and service configuration')
            try: await asyncio.wait_for(stop.wait(),timeout=delay)
            except TimeoutError: pass
    tasks=[asyncio.create_task(loop(cycle,300)),asyncio.create_task(loop(enrichment_cycle,60)),asyncio.create_task(loop(delivery_cycle,30))]
    try: await asyncio.gather(*tasks)
    finally:
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
