"""Correlacion multi-fuente y calculo de confianza.

Una alerta sube de confianza cuando coinciden espacialmente varias fuentes
(sensor + satelite + reporte ciudadano). Esta logica cruza el score del
anomaly-service con la correlacion espacial (nodos cercanos via ST_DWithin
en la capa de datos) y con la reputacion del ciudadano emisor.

Funciones puras -> testeables sin base de datos.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

EARTH_RADIUS_M = 6_371_000.0

# Peso base de cada tipo de fuente en el score de confianza combinado.
SOURCE_WEIGHTS = {"sensor": 0.42, "satelite": 0.32, "ciudadano": 0.18}


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos puntos (WGS84). Espeja ST_Distance geog."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


@dataclass
class Source:
    """Una evidencia que contribuye a una alerta."""
    source_type: str                 # sensor | satelite | ciudadano
    lat: float
    lon: float
    # score propio de la fuente [0..1]:
    #  - sensor: score de anomalia del anomaly-service
    #  - satelite: confidence de FIRMS
    #  - ciudadano: reputacion del emisor
    score: float


@dataclass
class CorrelationResult:
    confidence: float
    contributing: list[Source] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)


def spatial_proximity_factor(distance_m: float, radius_m: float) -> float:
    """1.0 en el centro, cae linealmente a 0 en el borde del radio."""
    if distance_m >= radius_m:
        return 0.0
    return 1.0 - (distance_m / radius_m)


def correlate(
    origin_lat: float,
    origin_lon: float,
    sources: list[Source],
    radius_m: float = 2000.0,
) -> CorrelationResult:
    """Combina fuentes que caen dentro de `radius_m` del origen en un score [0..1].

    Modelo: suma ponderada por tipo de fuente, escalada por proximidad espacial
    y por el score propio de la fuente. La coincidencia de multiples tipos de
    fuente eleva la confianza (bonus de corroboracion).
    """
    contributing: list[Source] = []
    accum = 0.0
    weight_used: dict[str, float] = {}

    for src in sources:
        dist = haversine_m(origin_lat, origin_lon, src.lat, src.lon)
        prox = spatial_proximity_factor(dist, radius_m)
        if prox <= 0.0:
            continue
        base_w = SOURCE_WEIGHTS.get(src.source_type, 0.1)
        contribution = base_w * prox * _clamp(src.score)
        accum += contribution
        weight_used[src.source_type] = weight_used.get(src.source_type, 0.0) + contribution
        contributing.append(src)

    # Bonus de corroboracion multi-fuente: +8% por cada tipo de fuente extra.
    distinct_types = len({s.source_type for s in contributing})
    corroboration = 1.0 + 0.07 * max(0, distinct_types - 1)

    confidence = _clamp(accum * corroboration)
    return CorrelationResult(
        confidence=round(confidence, 3),
        contributing=contributing,
        weights={k: round(v, 3) for k, v in weight_used.items()},
    )


def update_reputation(valid_count: int, invalid_count: int, prior: float = 0.5, strength: int = 4) -> float:
    """Score reputacional bayesiano suavizado [0..1].

    Evita saltos bruscos con pocos datos: arranca en `prior` (0.5) y converge
    al ratio de reportes validos a medida que crece el historial.
    """
    total = valid_count + invalid_count
    return round((valid_count + prior * strength) / (total + strength), 3)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
