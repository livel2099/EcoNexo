"""Tests del pipeline de correlacion espacial multi-fuente."""
from app.correlation import (
    Source,
    correlate,
    haversine_m,
    spatial_proximity_factor,
    update_reputation,
)

# Coordenadas de referencia (Misiones, AR)
LAT, LON = -31.42, -64.18


def test_haversine_known_distance() -> None:
    # ~1 grado de latitud ~= 111 km
    d = haversine_m(0.0, 0.0, 1.0, 0.0)
    assert 110_000 < d < 112_000


def test_proximity_decays_to_zero_at_radius() -> None:
    assert spatial_proximity_factor(0, 2000) == 1.0
    assert spatial_proximity_factor(2000, 2000) == 0.0
    assert 0.4 < spatial_proximity_factor(1000, 2000) < 0.6


def test_single_source_low_confidence() -> None:
    res = correlate(LAT, LON, [Source("sensor", LAT, LON, 0.9)])
    # una sola fuente no alcanza confianza critica
    assert res.confidence < 0.6
    assert len(res.contributing) == 1


def test_multisource_agreement_boosts_confidence() -> None:
    """Sensor + satelite + ciudadano coincidiendo espacialmente => alta confianza."""
    sources = [
        Source("sensor", LAT, LON, 0.95),
        Source("satelite", LAT + 0.001, LON, 0.90),
        Source("ciudadano", LAT, LON + 0.001, 0.80),
    ]
    res = correlate(LAT, LON, sources, radius_m=2000)
    assert res.confidence > 0.85          # historia de demo ~0.94
    assert len({s.source_type for s in res.contributing}) == 3


def test_far_sources_are_excluded() -> None:
    # fuente a ~5km queda fuera del radio de 2km
    sources = [
        Source("sensor", LAT, LON, 0.9),
        Source("satelite", LAT + 0.05, LON + 0.05, 0.9),
    ]
    res = correlate(LAT, LON, sources, radius_m=2000)
    assert len(res.contributing) == 1


def test_reputation_starts_neutral_and_converges() -> None:
    assert update_reputation(0, 0) == 0.5
    good = update_reputation(20, 0)
    bad = update_reputation(0, 20)
    assert good > 0.8
    assert bad < 0.2
    assert good > bad
