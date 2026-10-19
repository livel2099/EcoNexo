"""Evaluación preliminar de soja en Paraguay. Reglas explícitas, sin rendimiento inferido."""
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

BOUNDARY = json.loads((Path(__file__).parent / 'data/paraguay.geojson').read_text(encoding='utf-8-sig'))
SOURCES = [
    {'name': 'FAO · Soybean / Ecocrop', 'url': 'https://ecocrop.apps.fao.org/ecocrop/srv/en/cropView?id=1150'},
    {'name': 'IPTA · Protección vegetal de soja', 'url': 'https://www.ipta.gov.py/portada/informaciones/informacion-al-productor/soja/proteccion-vegetal/'},
    {'name': 'Open-Meteo · Pronóstico', 'url': 'https://open-meteo.com/en/docs'},
]


def in_paraguay(lat: float, lon: float) -> bool:
    geometry = BOUNDARY['geometry']
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    def inside(ring):
        result = False
        for a, b in zip(ring, ring[1:]):
            if (a[1] > lat) != (b[1] > lat) and lon < (b[0]-a[0])*(lat-a[1])/(b[1]-a[1])+a[0]:
                result = not result
        return result
    return any(inside(poly[0]) and not any(inside(hole) for hole in poly[1:]) for poly in polygons)


class SoyEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    name: str = Field(min_length=2, max_length=120)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    area_ha: float = Field(gt=0, le=100000)
    observed_on: date
    sowing_date: date | None = None
    stage: Literal['pre-siembra', 'vegetativo', 'floracion', 'llenado', 'madurez'] = 'pre-siembra'
    cultivar: str = Field(default='', max_length=120)
    source: str = Field(min_length=3, max_length=1000)
    ph: float | None = Field(default=None, ge=0, le=14)
    soil_temperature_c: float | None = Field(default=None, ge=-20, le=70)
    soil_analysis_ok: bool | None = None
    drainage_ok: bool | None = None
    water_ok: bool | None = None
    compaction: bool | None = None
    erosion: bool | None = None
    seed_ok: bool | None = None
    nodulation_plan_ok: bool | None = None
    pests_present: bool | None = None

    @model_validator(mode='after')
    def validate_evidence(self):
        if not self.name.strip() or not self.source.strip():
            raise ValueError('Nombre y procedencia de campo obligatorios')
        if not in_paraguay(self.lat, self.lon):
            raise ValueError('El lote debe ubicarse dentro de Paraguay (límite cartográfico aproximado)')
        if self.observed_on > date.today():
            raise ValueError('La observación no puede ser futura')
        return self


def evaluate(body: SoyEvidence, daily: list, weather_error: str | None = None) -> dict:
    risks, missing, recommendations = [], [], []
    def risk(factor, detail, action):
        risks.append({'factor': factor, 'detail': detail, 'action': action})
        recommendations.append(action)
    if (date.today()-body.observed_on).days > 30:
        missing.append('Actualizar evidencia de campo: supera 30 días (criterio operativo)')
    for key, title in [('ph','pH de suelo'),('soil_temperature_c','Temperatura del suelo'),('soil_analysis_ok','Análisis de suelo y nutrición'),('drainage_ok','Drenaje'),('water_ok','Agua en el perfil'),('compaction','Compactación'),('erosion','Erosión'),('seed_ok','Calidad de semilla'),('nodulation_plan_ok','Plan de inoculación y nodulación'),('pests_present','Monitoreo de plagas y enfermedades')]:
        if getattr(body, key) is None: missing.append(title)
    if not body.cultivar.strip(): missing.append('Cultivar y grupo de madurez validados para la zona y fecha')
    if body.sowing_date is None: missing.append('Fecha de siembra prevista o realizada')
    if body.ph is not None and not 5.5 <= body.ph <= 7.5:
        risk('Reacción del suelo', f'pH declarado {body.ph}; fuera del rango bibliográfico orientativo 5,5–7,5.', 'Revisar pH, aluminio y nutrición con análisis y asesor local; definir corrección según laboratorio.')
    for key, bad, title, action in [
        ('soil_analysis_ok',False,'Nutrición sin resolver','Completar análisis de suelo y un plan de nutrición específico para soja.'),
        ('drainage_ok',False,'Anegamiento','Revisar drenaje y transitabilidad antes de sembrar; verificar asfixia radicular.'),
        ('water_ok',False,'Agua insuficiente','Medir agua disponible en el perfil y revisar la fecha de siembra con el asesor.'),
        ('compaction',True,'Compactación','Evaluar raíces y resistencia del suelo antes de definir manejo.'),
        ('erosion',True,'Erosión','Revisar cobertura, rotación y control de escurrimiento.'),
        ('seed_ok',False,'Implantación','Verificar germinación, vigor y calidad sanitaria de la semilla.'),
        ('nodulation_plan_ok',False,'Fijación de nitrógeno','Revisar inoculación compatible y planificar control de nodulación.'),
        ('pests_present',True,'Sanidad observada','Identificar el agente y cuantificar incidencia con un profesional antes de tratar.'),
    ]:
        if getattr(body,key) is bad: risk(title, 'Evidencia declarada por el usuario.', action)
    if body.soil_temperature_c is not None and body.soil_temperature_c < 20:
        risk('Implantación en suelo frío', f'{body.soil_temperature_c} °C declarados. Filtro operativo orientativo: 20 °C.', 'Revisar temperatura a profundidad de siembra y tendencia antes de iniciar la labor.')
    weather_complete = len(daily) >= 7 and all(all(d.get(k) is not None for k in ('tmax','tmin','precipitation_mm','et0_mm')) for d in daily)
    if not weather_complete: missing.append('Pronóstico completo de 7 días; no se interpreta ausencia de datos como riesgo bajo')
    hot = [str(d['day']) for d in daily if d.get('tmax') is not None and d['tmax'] >= 34]
    cold = [str(d['day']) for d in daily if d.get('tmin') is not None and d['tmin'] <= 2]
    if hot: risk('Calor previsto', ', '.join(hot)+' con máxima ≥34 °C (umbral operativo).', 'Priorizar revisión de estrés hídrico, especialmente en floración y llenado.')
    if cold: risk('Frío previsto', ', '.join(cold)+' con mínima ≤2 °C a 2 m (umbral operativo).', 'Revisar exposición del lote y postergar labores sensibles si el asesor lo indica.')
    if weather_complete and body.stage != 'pre-siembra':
        kc = {'vegetativo':0.78,'floracion':1.15,'llenado':1.15,'madurez':0.50}[body.stage]
        rain = sum(d['precipitation_mm'] for d in daily)
        demand = sum(d['et0_mm'] for d in daily)*kc
        if rain < demand:
            risk('Balance climático previsto negativo', f'Lluvia {rain:.1f} mm frente a demanda estimada {demand:.1f} mm en 7 días; Kc orientativo {kc}. No incluye agua almacenada, riego ni escurrimiento.', 'Medir humedad del perfil y revisar la necesidad de agua con el asesor, especialmente en floración y llenado. Este balance no diagnostica sequía del lote.')
    recommendations.append('Validar cultivar, fotoperíodo y fecha de siembra para la zona de Paraguay; la etapa es declarada y no se deduce solo de grados día.')
    recommendations.append('Recorrer para detectar roya asiática, otras enfermedades, insectos y malezas. El clima y el NDVI no confirman presencia ni justifican aplicaciones automáticas.')
    return {'issued_at': datetime.now(timezone.utc).isoformat(), 'method':'py-soja-v1', 'status': 'condicionado' if risks else 'datos_insuficientes' if missing else 'potencial_favorable', 'evidence':body.model_dump(mode='json'), 'risks':risks, 'missing':missing, 'recommendations':recommendations, 'forecast':daily, 'weather_error':weather_error, 'sources':SOURCES, 'limitations':'Evaluación preliminar, no certifica aptitud, rendimiento ni rentabilidad. Requiere validación agronómica local. Rangos bibliográficos y filtros operativos sin calibración regional; no se prescriben productos ni dosis. Mapa Natural Earth 1:10m orientativo, no catastral.'}

