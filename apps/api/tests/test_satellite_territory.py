from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_firms_module():
    path = Path(__file__).resolve().parents[3] / "services" / "satellite" / "app" / "firms.py"
    spec = importlib.util.spec_from_file_location("econexo_satellite_firms", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_firms_polygon_rejects_corrientes_inside_rectangular_bbox() -> None:
    firms = _load_firms_module()
    assert firms._inside_misiones(-27.3621, -55.9007)  # Posadas
    assert not firms._inside_misiones(-28.05, -56.03)  # Gobernador Virasoro, Corrientes
