"""Limitador de intentos: respaldo en memoria cuando no hay base."""
from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("fastapi")

from fastapi import HTTPException

from app import rate_limit


class _ClienteFalso:
    def __init__(self, host: str) -> None:
        self.host = host


class _RequestFalso:
    """Lo minimo que consume el limitador: client y headers."""

    def __init__(self, host: str, headers: dict[str, str] | None = None) -> None:
        self.client = _ClienteFalso(host)
        self.headers = headers or {}


@pytest.fixture(autouse=True)
def _limpiar_estado():
    rate_limit._hits.clear()
    yield
    rate_limit._hits.clear()


def test_client_ip_ignora_x_forwarded_for() -> None:
    """El header es falsificable; uvicorn ya resolvio request.client."""
    request = _RequestFalso("203.0.113.9", {"x-forwarded-for": "1.2.3.4"})
    assert rate_limit.client_ip(request) == "203.0.113.9"


def test_respaldo_en_memoria_corta_al_llegar_al_limite() -> None:
    request = _RequestFalso("203.0.113.9")

    async def _correr() -> None:
        for _ in range(3):
            await rate_limit.enforce_rate_limit(
                request, bucket="prueba", limit=3, window_seconds=60
            )
        with pytest.raises(HTTPException) as exc:
            await rate_limit.enforce_rate_limit(
                request, bucket="prueba", limit=3, window_seconds=60
            )
        assert exc.value.status_code == 429
        assert int(exc.value.headers["Retry-After"]) >= 1

    asyncio.run(_correr())


def test_cada_ip_tiene_su_propio_cupo() -> None:
    async def _correr() -> None:
        for _ in range(3):
            await rate_limit.enforce_rate_limit(
                _RequestFalso("198.51.100.1"), bucket="prueba", limit=3, window_seconds=60
            )
        # La segunda IP no arrastra el consumo de la primera.
        await rate_limit.enforce_rate_limit(
            _RequestFalso("198.51.100.2"), bucket="prueba", limit=3, window_seconds=60
        )

    asyncio.run(_correr())
