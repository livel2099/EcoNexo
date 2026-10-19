"""Adaptación de pronósticos MET Norway sin inventar horas ni variables ausentes."""
from datetime import datetime, timedelta, timezone
import math

from .met_no import ATTRIBUTION, MetNoError


def number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def rows(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('properties'), dict):
        raise MetNoError('MET Norway devolvió una respuesta inválida')
    properties = payload['properties']
    units = properties.get('meta', {}).get('units', {})
    if any(units.get(k) != v for k, v in {'air_temperature': 'celsius', 'relative_humidity': '%', 'wind_speed': 'm/s', 'precipitation_amount': 'mm'}.items()):
        raise MetNoError('MET Norway no declara las unidades meteorológicas esperadas')
    return properties.get('timeseries', []), units


def hourly_payload(payload, lat, lon):
    series, units = rows(payload)
    hourly = {key: [] for key in ('time', 'temperature_2m', 'relative_humidity_2m', 'wind_speed_10m', 'precipitation', 'apparent_temperature')}
    for row in series:
        data = row.get('data', {})
        instant = data.get('instant', {}).get('details', {})
        wind = number(instant.get('wind_speed'))
        hourly['time'].append(row['time'])
        hourly['temperature_2m'].append(number(instant.get('air_temperature')))
        hourly['relative_humidity_2m'].append(number(instant.get('relative_humidity')))
        hourly['wind_speed_10m'].append(wind * 3.6 if wind is not None else None)
        hourly['precipitation'].append(number(data.get('next_1_hours', {}).get('details', {}).get('precipitation_amount')))
        hourly['apparent_temperature'].append(number(instant.get('apparent_air_temperature')) if units.get('apparent_air_temperature') == 'celsius' else None)
    return {'latitude': lat, 'longitude': lon, 'hourly': hourly,
            'hourly_units': {'temperature_2m': '°C', 'relative_humidity_2m': '%', 'wind_speed_10m': 'km/h', 'precipitation': 'mm', 'apparent_temperature': '°C'},
            '_provider': 'met-no', '_attribution': ATTRIBUTION, 'precipitation_time': 'interval_start'}


def soy_context(payload, lat, lon, primary_error):
    series, units = rows(payload)
    now = datetime.now(timezone.utc)
    indexed = {datetime.fromisoformat(row['time'].replace('Z', '+00:00')): row for row in series}
    current_time = max((stamp for stamp in indexed if stamp <= now), default=None)
    if current_time is None or now - current_time > timedelta(hours=2):
        raise MetNoError('MET Norway no ofrece una hora actual reciente')
    current = indexed[current_time].get('data', {}).get('instant', {}).get('details', {})
    variables = {}
    for key, field, label, unit in [('temperature_2m', 'air_temperature', 'Temperatura del aire', '°C'), ('relative_humidity_2m', 'relative_humidity', 'Humedad relativa', '%'), ('wind_speed_10m', 'wind_speed', 'Viento a 10 m', 'km/h')]:
        value = number(current.get(field))
        if key == 'wind_speed_10m' and value is not None:
            value = round(value * 3.6, 2)
        variables[key] = {'label': label, 'value': value, 'unit': unit, 'valid_at': current_time.isoformat(), 'kind': 'modelo'}
    # Los bloques de 6 h permiten sumar lluvia y extremos sin repartir cantidades
    # entre días ni interpolar. Se muestran siete días completos en UTC.
    first = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    daily = []
    for day in range(7):
        start = first + timedelta(days=day)
        blocks = [indexed.get(start + timedelta(hours=h), {}).get('data', {}).get('next_6_hours', {}).get('details', {}) for h in (0, 6, 12, 18)]
        def aggregate(key, unit, operation):
            values = [number(block.get(key)) for block in blocks]
            return round(operation(values), 2) if units.get(key) == unit and all(v is not None for v in values) else None
        daily.append({'day': start.date().isoformat(), 'tmax': aggregate('air_temperature_max', 'celsius', max), 'tmin': aggregate('air_temperature_min', 'celsius', min), 'precipitation_mm': aggregate('precipitation_amount', 'mm', sum), 'et0_mm': None})
    coords = payload.get('geometry', {}).get('coordinates', [])
    return {'queried_at': now.isoformat(), 'timezone': 'UTC', 'requested_location': {'lat': lat, 'lon': lon},
            'grid_location': {'lat': coords[1] if len(coords) > 1 else None, 'lon': coords[0] if coords else None},
            'elevation_m': coords[2] if len(coords) > 2 else None, 'source': ATTRIBUTION, 'provider': 'met-no',
            'variables': variables, 'forecast': daily,
            'error': 'Open-Meteo no disponible. Respaldo MET Norway activo; no ofrece ET0 ni humedad o temperatura del suelo.',
            'primary_error': primary_error,
            'note': 'Pronóstico de modelo, no mediciones. Siete días completos en UTC desde mañana; extremos y lluvia agregados de cuatro bloques de 6 h. No se calcula balance hídrico sin ET0. Las variables ausentes permanecen sin datos.'}
