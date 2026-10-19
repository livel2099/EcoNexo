"""Contexto automático por ubicación; los modelos no sustituyen mediciones de campo."""
import asyncio
import math
import httpx
from datetime import datetime, timedelta, timezone
from . import agro, met_no
from .weather_fallback import soy_context
from .config import get_settings
from .open_meteo_http import RateLimited


def finite(value):
    return value if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) else None


def parse_context(payload, lat, lon):
    now=datetime.now(timezone.utc)
    offset=payload.get('utc_offset_seconds',0)
    hourly=payload.get('hourly',{})
    selected=None
    for i, stamp in enumerate(hourly.get('time',[])):
        try:
            acquired=datetime.fromisoformat(stamp).replace(tzinfo=timezone(timedelta(seconds=offset)))
        except (ValueError,TypeError): continue
        if acquired <= now and now-acquired <= timedelta(hours=2): selected=(i,acquired)
    soil={}
    if selected:
        i,acquired=selected
        for key,label,unit in [('soil_temperature_6cm','Temperatura de suelo a 6 cm','°C'),('soil_moisture_3_to_9cm','Humedad de suelo 3–9 cm','m³/m³'),('soil_moisture_9_to_27cm','Humedad de suelo 9–27 cm','m³/m³')]:
            values=hourly.get(key,[])
            soil[key]={'label':label,'value':finite(values[i]) if i<len(values) else None,'unit':unit,'valid_at':acquired.isoformat(),'kind':'modelo'}
    current=payload.get('current',{})
    variables={}
    for key,label,unit in [('temperature_2m','Temperatura del aire','°C'),('relative_humidity_2m','Humedad relativa','%'),('precipitation','Precipitación actual','mm'),('wind_speed_10m','Viento a 10 m','km/h')]:
        variables[key]={'label':label,'value':finite(current.get(key)),'unit':unit,'valid_at':current.get('time'),'kind':'modelo'}
    daily=[]
    for row in agro._parse_daily(payload):
        daily.append({k:finite(v) if k!='day' else v.isoformat() for k,v in row.items()})
    complete=len(daily)==7 and all(all(d.get(k) is not None for k in ('tmax','tmin','precipitation_mm','et0_mm')) for d in daily)
    return {'queried_at':now.isoformat(),'timezone':payload.get('timezone','America/Asuncion'),'requested_location':{'lat':lat,'lon':lon},'grid_location':{'lat':finite(payload.get('latitude')),'lon':finite(payload.get('longitude'))},'elevation_m':finite(payload.get('elevation')),'source':'Open-Meteo · modelo meteorológico','variables':{**variables,**soil},'forecast':daily,'error':None if complete else 'El proveedor devolvió un pronóstico incompleto. Los campos ausentes no equivalen a cero.','note':'Datos de grilla modelados, no sensores del lote. La humedad volumétrica no determina por sí sola agua útil, drenaje ni aptitud. Las mediciones declaradas se conservan por separado.'}


async def load_context(lat,lon):
    params={'latitude':f'{lat:.6f}','longitude':f'{lon:.6f}','forecast_days':'7','timezone':'America/Asuncion','current':'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m','hourly':'soil_temperature_6cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm','daily':','.join(agro.DAILY_VARIABLES)}
    try:
        payload=await asyncio.wait_for(agro._consultar(get_settings().open_meteo_forecast_url,params,'clima Paraguay'),timeout=12)
        return parse_context(payload,lat,lon)
    except (TimeoutError,ValueError,RuntimeError,httpx.HTTPError) as exc:
        try:
            if not get_settings().met_no_fallback_enabled: raise met_no.MetNoError('Respaldo deshabilitado')
            payloads = await asyncio.wait_for(met_no.fetch_forecast_batch([(lat, lon)]), timeout=12)
            return soy_context(payloads[0], lat, lon, 'Open-Meteo no disponible')
        except (met_no.MetNoError, TimeoutError, httpx.HTTPError, ValueError, IndexError):
            pass
        message=str(exc).lower()
        reason=str(exc) if isinstance(exc,RateLimited) else 'Tiempo de espera agotado' if isinstance(exc,TimeoutError) else 'Proveedor limitado (HTTP 429)' if '429' in message or 'límite' in message else 'Proveedor no disponible o respuesta inválida'
        return {'queried_at':datetime.now(timezone.utc).isoformat(),'source':'Open-Meteo','variables':{},'forecast':[],'error':reason+'. Reintentá la carga automática. Revisar conectividad, cuota y configuración del proveedor.','note':'Sin datos no se evalúa riesgo meteorológico bajo.'}
