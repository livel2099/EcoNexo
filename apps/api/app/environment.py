"""Reglas puras para convertir resultados SpaceAI en alertas operativas."""
from __future__ import annotations

from .schemas import EnvironmentalAlertSnapshot

_LEVEL_RANK = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4, "R5": 5}
_DOMAIN_ALERT_TYPE = {
    "air": "calidad_aire",
    "heat": "estres_termico",
    "moisture": "anomalia_hidrica",
    "fire": "incendio",
    "hydric": "riesgo_hidrico",
    "uv": "radiacion_uv",
    "vector": "riesgo_vectorial",
}


def alert_type_for_domain(domain: str) -> str:
    """Mapea un dominio SpaceAI a un valor de ``alert_type`` de PostgreSQL."""
    return _DOMAIN_ALERT_TYPE.get(domain, "anomalia")


def should_activate(alert: EnvironmentalAlertSnapshot, minimum_level: str) -> bool:
    """Decide si una alerta del snapshot cruza el nivel operativo configurado."""
    minimum = _LEVEL_RANK.get(minimum_level, _LEVEL_RANK["R3"])
    return _LEVEL_RANK.get(alert.level, 0) >= minimum
