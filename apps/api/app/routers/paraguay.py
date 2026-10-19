"""Centro de comando Paraguay, exclusivo soja, con informes por organización."""
import json
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from .. import agro, db
from ..paraguay import SoyEvidence, evaluate, in_paraguay
from ..deps import CurrentUser, require_role
from .agro import require_agro_module
from ..copernicus import access_token, EVALSCRIPTS, CopernicusError
from ..ecocampo_satellite import Polygon, fetch_ndvi
from ..rate_limit import enforce_rate_limit
from ..config import get_settings

router = APIRouter(prefix='/paraguay/soja', tags=['paraguay-soja'])


@router.post('/evaluate')
async def assessment(body: SoyEvidence, request: Request, user: CurrentUser = Depends(require_agro_module)):
    await enforce_rate_limit(request, bucket='py-soja-evaluate', limit=12, window_seconds=60)
    daily, error = [], None
    try:
        params = {'latitude':str(body.lat), 'longitude':str(body.lon), 'forecast_days':'7', 'timezone':'America/Asuncion', 'daily':','.join(agro.DAILY_VARIABLES)}
        payload = await agro._consultar(get_settings().open_meteo_forecast_url, params, 'pronóstico Paraguay')
        daily = agro._parse_daily(payload)
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        error = 'Pronóstico no disponible. Volvé a consultar; la evaluación conserva los datos de campo.'
    return evaluate(body, daily, error)


class SaveReport(BaseModel):
    evidence: SoyEvidence


@router.post('/reports', status_code=201)
async def save_report(body: SaveReport, request: Request, user: CurrentUser = Depends(require_role('admin', 'operador'))):
    await require_agro_module(user)
    result = await assessment(body.evidence, request, user)
    row = await db.pool().fetchrow('INSERT INTO paraguay_soy_reports(org_id,created_by,payload) VALUES($1,$2,$3::jsonb) RETURNING id,created_at', user.org_id, user.id, json.dumps(result, default=str))
    return {'id':str(row['id']), 'created_at':row['created_at'], 'report':result}


@router.get('/reports')
async def reports(user: CurrentUser = Depends(require_agro_module)):
    rows = await db.pool().fetch('SELECT id,created_at,payload FROM paraguay_soy_reports WHERE org_id=$1 ORDER BY created_at DESC LIMIT 30', user.org_id)
    return [{'id':str(r['id']), 'created_at':r['created_at'], 'report':json.loads(r['payload']) if isinstance(r['payload'],str) else r['payload']} for r in rows]


def validate_polygon(polygon):
    if any(not in_paraguay(lat,lon) for lon,lat in polygon.coordinates[0]):
        raise HTTPException(422,'Todos los vértices deben estar en Paraguay; límite orientativo Natural Earth')
    ring = polygon.coordinates[0]
    def orient(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    if abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]))) < 1e-12:
        raise HTTPException(422,'El polígono debe tener superficie')
    for i in range(len(ring)-1):
        for j in range(i+2,len(ring)-1):
            if i==0 and j==len(ring)-2: continue
            a,b,c,d=ring[i],ring[i+1],ring[j],ring[j+1]
            if orient(a,b,c)*orient(a,b,d)<=0 and orient(c,d,a)*orient(c,d,b)<=0 and max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1])):
                raise HTTPException(422,'El polígono tiene cruces o vértices repetidos')


@router.post('/ndvi')
async def ndvi(body: Polygon, request: Request, user: CurrentUser = Depends(require_agro_module)):
    await enforce_rate_limit(request, bucket='py-soja-ndvi', limit=6, window_seconds=60)
    validate_polygon(body)
    try: return await fetch_ndvi(body)
    except CopernicusError as exc: raise HTTPException(503,str(exc)) from exc


class ImageRequest(BaseModel):
    polygon: Polygon
    layer: str = 'TRUE_COLOR'


@router.post('/image')
async def image(body: ImageRequest, request: Request, user: CurrentUser = Depends(require_agro_module)):
    await enforce_rate_limit(request, bucket='py-soja-image', limit=6, window_seconds=60)
    validate_polygon(body.polygon)
    if body.layer not in ('TRUE_COLOR','NDVI','MOISTURE_INDEX'): raise HTTPException(422,'Capa no admitida')
    now = datetime.now(timezone.utc)
    payload = {'input':{'bounds':{'geometry':body.polygon.model_dump(), 'properties':{'crs':'http://www.opengis.net/def/crs/OGC/1.3/CRS84'}},'data':[{'type':'sentinel-2-l2a','dataFilter':{'timeRange':{'from':(now-timedelta(days=30)).isoformat(),'to':now.isoformat()},'mosaickingOrder':'leastCC'}}]},'output':{'width':768,'height':512,'responses':[{'identifier':'default','format':{'type':'image/png'}}]},'evalscript':EVALSCRIPTS[body.layer]}
    try:
        token = await access_token()
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post('https://sh.dataspace.copernicus.eu/api/v1/process',json=payload,headers={'Authorization':f'Bearer {token}'})
            response.raise_for_status()
            if not response.headers.get('content-type','').startswith('image/png'): raise ValueError('Respuesta satelital inválida')
    except (CopernicusError,httpx.HTTPError,ValueError) as exc:
        raise HTTPException(503,'Imagen no disponible: revisar credenciales Copernicus, cuota y cobertura. No se muestra una imagen simulada.') from exc
    return Response(response.content,media_type='image/png',headers={'Cache-Control':'private, max-age=300','X-Image-Period':f'{(now-timedelta(days=30)).date()}/{now.date()}'})
