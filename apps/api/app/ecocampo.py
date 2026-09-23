"""EcoCampo: evaluación trazable, sin convertir NDVI en rendimiento."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SOURCES = [
    {"name": "CONICET · productividad de pastizales NEA", "url": "https://bicyt.conicet.gov.ar/fichas/produccion/12086803", "scope": "Modelos NDVI/PPNA requieren calibración local."},
    {"name": "INTA · modelos de productividad y calidad forrajera", "url": "https://repositorio.inta.gob.ar/handle/20.500.12123/5834", "scope": "Biomasa, productividad y calidad son magnitudes diferentes."},
    {"name": "OMS · gestión de plaguicidas", "url": "https://www.who.int/publications/b/57151", "scope": "Salud y exposición; no certifica aptitud del suelo ni rendimiento."},
]


class FieldEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    observed_on: date
    source: str = Field(min_length=3, max_length=500)
    use: Literal["agricultura", "ganaderia", "mixto"] = "mixto"
    ndvi: float | None = Field(default=None, ge=-1, le=1)
    baseline_ndvi: float | None = Field(default=None, ge=-1, le=1)
    valid_pixel_pct: float | None = Field(default=None, ge=0, le=100)
    soil_suitable: bool | None = None
    water_suitable: bool | None = None
    flooding: bool | None = None
    erosion: bool | None = None
    pesticide_exposure: bool | None = None
    forage_verified: bool | None = None
    dry_matter_kg_ha: float | None = Field(default=None, ge=0, le=100000)
    utilization_pct: float | None = Field(default=None, gt=0, le=100)
    animal_demand_kg_day: float | None = Field(default=None, gt=0, le=200)
    grazing_days: int | None = Field(default=None, ge=1, le=366)
    herd_size: int | None = Field(default=None, ge=0, le=1000000)

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.observed_on > date.today():
            raise ValueError("La observación no puede estar en el futuro")
        if not self.source.strip():
            raise ValueError("Indicá la procedencia de la evidencia")
        return self


def assess(e: FieldEvidence, area_ha: float, today: date | None = None) -> dict:
    age = ((today or date.today()) - e.observed_on).days
    missing, risks = [], []
    if age > 30:
        missing.append("Evidencia de campo de más de 30 días: actualizar antes de decidir.")
    for key, label in [("soil_suitable", "aptitud del suelo para el cultivo/uso"), ("water_suitable", "disponibilidad y calidad del agua"), ("flooding", "anegamiento"), ("erosion", "erosión"), ("pesticide_exposure", "exposición a plaguicidas")]:
        value = getattr(e, key)
        if value is None:
            missing.append(label)
        elif (key in {"soil_suitable", "water_suitable"} and not value) or (key not in {"soil_suitable", "water_suitable"} and value):
            risks.append({"factor": label, "level": "alto", "action": "Verificar en terreno y definir medidas con un profesional antes de intensificar el uso."})
    usable = e.ndvi is not None and e.valid_pixel_pct is not None and e.valid_pixel_pct >= 70 and age <= 30
    delta = round(e.ndvi - e.baseline_ndvi, 4) if usable and e.baseline_ndvi is not None else None
    if not usable:
        missing.append("NDVI reciente con al menos 70% de píxeles válidos sobre el lote")
    if usable and e.ndvi <= 0:
        risks.append({"factor": "Sin señal de vegetación activa", "level": "alto", "action": "Verificar agua, suelo desnudo y cobertura antes de planificar producción."})
    if e.baseline_ndvi is None:
        missing.append("Referencia NDVI de igual estación, sensor y cobertura")
    if delta is not None and delta < -0.15:
        risks.append({"factor": "Caída de actividad vegetal", "level": "medio", "action": "Inspeccionar sequía, cosecha, fenología, plagas o cambio de cobertura; NDVI no identifica la causa."})
    capacity = None
    if e.use in {"ganaderia", "mixto"}:
        if e.forage_verified is not True:
            missing.append("Identificación de especies aprovechables y calidad forrajera")
        values = [e.dry_matter_kg_ha, e.utilization_pct, e.animal_demand_kg_day, e.grazing_days]
        if e.forage_verified is True and all(v is not None for v in values) and age <= 30:
            capacity = int(area_ha * e.dry_matter_kg_ha * e.utilization_pct / 100 / e.animal_demand_kg_day / e.grazing_days)
            if e.herd_size is not None and e.herd_size > capacity:
                risks.append({"factor": "Demanda superior al forraje disponible", "level": "alto", "action": "Revisar carga, reservas y suplementación con el responsable ganadero."})
        else:
            missing.append("Medición de materia seca, aprovechamiento, demanda animal y días de pastoreo")
    return {
        "method_version": "ecocampo-1", "status": "condicionado" if risks else "datos_insuficientes" if missing else "potencial_favorable",
        "risks": risks, "missing": missing, "ndvi_usable": usable, "ndvi_delta": delta,
        "vegetation": "sin_datos_confiables" if not usable else "inferior_a_referencia" if delta is not None and delta < -0.15 else "comparable_a_referencia" if delta is not None and abs(delta) <= 0.15 else "superior_a_referencia" if delta is not None else "sin_referencia",
        "estimated_animals": capacity, "yield_t_ha": None,
        "limitations": "Evaluación preliminar, no certificación. NDVI no mide rendimiento, calidad forrajera ni inocuidad. Umbrales 30 días, 70% y 0,15 son filtros operativos no validados localmente, no normas OMS/CONICET. La carga es un presupuesto de forraje sin crecimiento futuro ni suplementos, no una recomendación de carga sostenible.",
        "sources": SOURCES,
    }
