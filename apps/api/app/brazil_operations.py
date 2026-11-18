"""Validated field evidence; screening never identifies a pest from weather/NDVI."""
from datetime import datetime, timedelta, timezone, date
from typing import Literal
import math
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator, model_validator

CROP_TARGETS = {
 'orange': {'citrus_psyllid', 'hlb_symptoms', 'citrus_canker', 'citrus_mite', 'other'},
 'eucalyptus': {'bronze_bug', 'lerp_psyllid', 'gall_wasp', 'leafcutter_ant', 'defoliation', 'other'},
 'soy': {'other'}, 'reserve': {'other'},
}

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, str_strip_whitespace=True)

class ParcelProperties(StrictModel):
    code: str = Field(min_length=1, max_length=80)
    estate: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=120)
    crop: Literal['orange','eucalyptus','soy','reserve']
    cultivar: str = Field(default='', max_length=120)
    planted_on: date | None = None
    manager: str = Field(default='', max_length=120)

class ParcelFeature(StrictModel):
    type: Literal['Feature']
    properties: ParcelProperties
    geometry: dict

    @field_validator('geometry')
    @classmethod
    def geometry_limits(cls, value):
        if value.get('type') not in {'Polygon','MultiPolygon'} or set(value) != {'type','coordinates'}:
            raise ValueError('Polygon / MultiPolygon WGS84 required')
        polygons = [value['coordinates']] if value['type']=='Polygon' else value['coordinates']
        if not isinstance(polygons,list) or not polygons or len(polygons)>100: raise ValueError('Invalid polygon count')
        count=0
        for polygon in polygons:
            if not isinstance(polygon,list) or not polygon: raise ValueError('Empty polygon')
            for ring in polygon:
                if not isinstance(ring,list): raise ValueError('Invalid ring')
                count+=len(ring)
                if len(ring)<4 or ring[0]!=ring[-1]: raise ValueError('Closed rings required')
                for xy in ring:
                    if not isinstance(xy,(list,tuple)) or len(xy)!=2 or any(isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) for x in xy):
                        raise ValueError('Finite WGS84 coordinates required')
                    if not (-61.7<=xy[0]<=-50 and -18.2<=xy[1]<=-7): raise ValueError('Outside Mato Grosso bounding region')
        if count>10000: raise ValueError('Maximum 10000 vertices per management unit')
        return value

class ParcelImport(StrictModel):
    type: Literal['FeatureCollection']
    features: list[ParcelFeature] = Field(min_length=1,max_length=200)

    @model_validator(mode='after')
    def unique_codes(self):
        if len({f.properties.code for f in self.features})!=len(self.features): raise ValueError('Duplicate parcel codes')
        if sum(len(ring) for f in self.features for p in ([f.geometry['coordinates']] if f.geometry['type']=='Polygon' else f.geometry['coordinates']) for ring in p)>100000:
            raise ValueError('Maximum 100000 vertices per import; split the file')
        return self

class Recipient(StrictModel):
    channel: Literal['email','whatsapp']
    address: str = Field(min_length=4,max_length=254)
    consent: Literal[True]

    @model_validator(mode='after')
    def validate_address(self):
        if self.channel=='email':
            from pydantic import TypeAdapter
            self.address=str(TypeAdapter(EmailStr).validate_python(self.address)).lower()
        else:
            import re
            if not re.fullmatch(r'\+[1-9]\d{7,14}',self.address): raise ValueError('Use E.164, e.g. +5565999999999')
        return self

class OperationsSettings(StrictModel):
    target_area_ha: float = Field(default=450000,gt=0,le=100000000)
    enabled: bool = False
    fire_buffer_m: int = Field(default=5000,ge=0,le=20000)
    recipients: list[Recipient] = Field(default_factory=list,max_length=20)

    @model_validator(mode='after')
    def distinct(self):
        if len({(r.channel,r.address) for r in self.recipients})!=len(self.recipients): raise ValueError('Duplicate recipients')
        return self

def valid_observation(stamp):
    if stamp.tzinfo is None or stamp>datetime.now(timezone.utc)+timedelta(minutes=5):
        raise ValueError('Timestamp must include timezone and cannot be in the future')
    return stamp

class SoilReading(StrictModel):
    observed_at: datetime
    source: Literal['sensor','laboratory']
    reference: str = Field(min_length=3,max_length=180)
    depth_cm: int = Field(ge=0,le=200)
    ph: float | None = Field(default=None,ge=0,le=14)
    ph_method: Literal['H2O','CaCl2','KCl','electrode']
    temperature_c: float | None = Field(default=None,ge=-20,le=80)
    calibrated_at: datetime | None = None

    _observed=field_validator('observed_at')(valid_observation)

    @model_validator(mode='after')
    def calibration(self):
        if self.ph is None and self.temperature_c is None: raise ValueError('No readings')
        if self.source=='sensor':
            if self.calibrated_at is None or self.calibrated_at.tzinfo is None or self.calibrated_at>self.observed_at or self.observed_at-self.calibrated_at>timedelta(days=30):
                raise ValueError('Sensor calibration within 30 days of observation required')
        return self

class Inspection(StrictModel):
    observed_at: datetime
    target: str = Field(min_length=2,max_length=40)
    sampled_plants: int = Field(ge=1,le=1000000)
    affected_plants: int = Field(ge=0,le=1000000)
    trap_count: int = Field(default=0,ge=0,le=100000)
    trap_days: int | None = Field(default=None,ge=1,le=365)
    captures: int = Field(default=0,ge=0,le=1000000)
    symptoms: str = Field(default='',max_length=2000)
    evidence_reference: str = Field(min_length=3,max_length=1000)
    diagnosis: Literal['suspected','confirmed'] = 'suspected'
    specialist: str = Field(default='',max_length=180)
    diagnosis_reference: str = Field(default='',max_length=500)
    _observed=field_validator('observed_at')(valid_observation)

    @model_validator(mode='after')
    def evidence(self):
        if self.affected_plants>self.sampled_plants: raise ValueError('Affected exceeds sampled')
        if self.captures and (not self.trap_count or not self.trap_days): raise ValueError('Trap count and exposure required')
        if self.diagnosis=='confirmed' and (len(self.specialist)<3 or len(self.diagnosis_reference)<3): raise ValueError('Specialist and diagnostic reference required')
        return self

class AlertAction(StrictModel):
    status: Literal['acknowledged','resolved','dismissed']
    assigned_to: str = Field(min_length=2,max_length=180)
    resolution: str = Field(min_length=5,max_length=2000)

def inspection_signal(crop, observation: Inspection):
    if observation.target not in CROP_TARGETS[crop]: raise ValueError('Target incompatible with crop')
    if not (observation.affected_plants or observation.captures or observation.symptoms or observation.diagnosis=='confirmed'): return None
    return {'kind':'pest','priority':'high' if observation.diagnosis=='confirmed' or observation.target=='hlb_symptoms' else 'medium',
            'diagnosis':observation.diagnosis,'target':observation.target,
            'sample_incidence_pct':round(observation.affected_plants/observation.sampled_plants*100,2),
            'captures_per_trap_day':round(observation.captures/(observation.trap_count*observation.trap_days),3) if observation.trap_count and observation.trap_days else None,
            'scope':'sample_only','requires_field_review':True}

def vegetation_signal(series):
    observations={}
    today=datetime.now(timezone.utc).date()
    for r in series:
        if not isinstance(r,dict): continue
        try:
            day=date.fromisoformat(r.get('day',''))
            ndvi=r.get('ndvi');coverage=r.get('valid_pixel_pct')
            if day>today: continue
            if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in (ndvi,coverage)): continue
            if not -1<=ndvi<=1 or not 70<=coverage<=100: continue
            observations[day.isoformat()]=r
        except (ValueError,TypeError):
            continue
    good=sorted(observations.values(),key=lambda r:r['day'])
    if len(good)<4: return None
    latest=good[-1]
    if date.fromisoformat(latest['day'])<datetime.now(timezone.utc).date()-timedelta(days=10): return None
    baseline=sum(r['ndvi'] for r in good[-4:-1])/3
    drop=baseline-latest['ndvi']
    if drop<0.15: return None
    return {'day':latest['day'],'baseline_ndvi':round(baseline,4),'latest_ndvi':latest['ndvi'],'drop':round(drop,4),
            'valid_pixel_pct':latest['valid_pixel_pct'],'diagnosis':'unconfirmed_anomaly',
            'method':'ndvi-screen-v1','requires_field_review':True}
