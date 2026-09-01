"""El bootstrap del administrador general corre al arrancar la API.

`ensure_platform_admin` existia desde el inicio del proyecto y no la llamaba
nadie. La cuenta nunca se creaba, y el sintoma era un "Credenciales invalidas"
en el login con PLATFORM_ADMIN_EMAILS y PLATFORM_ADMIN_INITIAL_PASSWORD bien
cargadas: no habia forma de deducir desde afuera que el usuario no existia.
"""
from __future__ import annotations

import pytest

pytest.importorskip("asyncpg")
pytest.importorskip("aiomqtt")
pytest.importorskip("jose")


@pytest.mark.anyio
async def test_lifespan_invokes_the_platform_admin_bootstrap(monkeypatch) -> None:
    from app import db, main

    llamadas: list[str] = []

    async def _connect_falso():
        llamadas.append("db.connect")

    async def _disconnect_falso():
        llamadas.append("db.disconnect")

    async def _ensure_falso():
        llamadas.append("ensure_platform_admin")

    async def _worker_falso(stop):
        await stop.wait()

    monkeypatch.setattr(db, "connect", _connect_falso)
    monkeypatch.setattr(db, "disconnect", _disconnect_falso)
    monkeypatch.setattr(main, "ensure_platform_admin", _ensure_falso)
    monkeypatch.setattr(main, "mqtt_bridge", _worker_falso)
    monkeypatch.setattr(main, "pipeline_scheduler", _worker_falso)

    async with main.lifespan(main.app):
        pass

    assert "ensure_platform_admin" in llamadas, (
        "El arranque no llama a ensure_platform_admin: la cuenta de "
        "administracion general nunca se crearia."
    )
    # Tiene que correr con la base ya conectada.
    assert llamadas.index("db.connect") < llamadas.index("ensure_platform_admin")


@pytest.mark.anyio
async def test_a_failing_bootstrap_does_not_block_the_api(monkeypatch) -> None:
    """El resto del sistema funciona sin la cuenta de plataforma."""
    from app import db, main

    async def _sin_efecto():
        return None

    async def _ensure_que_falla():
        raise RuntimeError("PLATFORM_ADMIN_EMAILS no contiene un correo valido")

    async def _worker_falso(stop):
        await stop.wait()

    monkeypatch.setattr(db, "connect", _sin_efecto)
    monkeypatch.setattr(db, "disconnect", _sin_efecto)
    monkeypatch.setattr(main, "ensure_platform_admin", _ensure_que_falla)
    monkeypatch.setattr(main, "mqtt_bridge", _worker_falso)
    monkeypatch.setattr(main, "pipeline_scheduler", _worker_falso)

    async with main.lifespan(main.app):
        pass  # No debe propagar la excepcion.
