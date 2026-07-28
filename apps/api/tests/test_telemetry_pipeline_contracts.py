"""Contratos del pipeline de telemetria y sus rutas publicadas."""
from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.main import app
from app.schemas import (
    BootstrapTelemetryIn,
    DeviceIn,
    DeviceReadingsIn,
    TelemetryPipelineSettingsIn,
)
from app.telemetry_pipeline import _confidence


def test_pipeline_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/pipeline/settings" in paths
    assert "/pipeline/run" in paths
    assert "/pipeline/runs" in paths
    assert "/pipeline/bootstrap" in paths
    assert "/devices/{device_id}/readings" in paths


def test_virtual_device_contract_normalizes_external_id() -> None:
    zone_id = uuid4()
    device = DeviceIn(
        name="Nodo Norte",
        external_id=" Nodo Virtual 01 ",
        lat=-26.92,
        lon=-54.78,
        marker_shape="triangle",
        telemetry_mode="open_meteo",
        zone_id=zone_id,
        pipeline_enabled=True,
        telemetry_config={"provider": "open-meteo"},
    )
    assert device.external_id == "nodo-virtual-01"
    assert device.marker_shape == "triangle"
    assert device.telemetry_mode == "open_meteo"
    assert device.zone_id == zone_id


def test_device_contract_rejects_location_outside_misiones() -> None:
    with pytest.raises(ValidationError):
        DeviceIn(
            name="Nodo externo",
            external_id="outside-1",
            lat=-27.47,
            lon=-58.83,
        )


def test_manual_readings_are_normalized() -> None:
    readings = DeviceReadingsIn(values={" Humidity ": 76.4, "Soil Moisture": 42})
    assert readings.values == {"humidity": 76.4, "soil_moisture": 42.0}


def test_pipeline_limits_and_firms_confidence() -> None:
    settings = TelemetryPipelineSettingsIn(interval_minutes=15, stale_minutes=30)
    assert settings.enabled is True
    assert BootstrapTelemetryIn(count=2).count == 2
    assert _confidence("h") == 0.9
    assert _confidence("75") == 0.75
    assert _confidence("0.3") == 0.3

    with pytest.raises(ValidationError):
        TelemetryPipelineSettingsIn(interval_minutes=1)
