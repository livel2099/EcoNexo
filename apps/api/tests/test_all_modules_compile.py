"""Todos los modulos compilan y los entrypoints se pueden importar.

Un SyntaxError en `app/migrate.py` llego a produccion: ningun test lo importaba,
porque las migraciones necesitan una base y el resto de la suite no lo toca. El
fallo aparecio recien en el arranque del contenedor, como
`SyntaxError: unterminated f-string literal`, despues de un build completo.

Compilar cuesta milisegundos y cubre todos los archivos, incluidos los que no
tienen tests propios: seed, migrate, check_config y los servicios.
"""
from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
RAIZ = Path(__file__).resolve().parents[3]


def _modulos_python(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)


@pytest.mark.parametrize("ruta", _modulos_python(APP), ids=lambda p: p.name)
def test_el_modulo_compila(ruta: Path) -> None:
    try:
        ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    except SyntaxError as exc:
        pytest.fail(f"{ruta.relative_to(APP.parent)}:{exc.lineno} {exc.msg}")


@pytest.mark.parametrize(
    "modulo",
    [
        # Entrypoints que corren fuera de la API y por eso no los cubre el
        # resto de la suite. Importar tiene que ser libre de efectos.
        "app.migrate",
        "app.seed",
        "app.check_config",
    ],
)
def test_el_entrypoint_importa(modulo: str) -> None:
    importlib.import_module(modulo)


def test_los_servicios_tambien_compilan() -> None:
    """Cubre services/, que no tiene suite propia."""
    servicios = RAIZ / "services"
    if not servicios.is_dir():
        pytest.skip("no hay directorio services/")
    fallos = []
    for ruta in _modulos_python(servicios):
        try:
            ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        except SyntaxError as exc:
            fallos.append(f"{ruta.relative_to(RAIZ)}:{exc.lineno} {exc.msg}")
    assert not fallos, "\n".join(fallos)
