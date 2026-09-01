"""Limitador de intentos para endpoints publicos.

El estado vive en Postgres (`rate_limit_hits`), asi que el limite es real
aunque el API corra con varias replicas: en memoria, `replicas: 2` convertia
un limite de 10 intentos por ventana en 20 repartidos por el balanceador.

Se conserva un limitador en memoria como respaldo para cuando no hay pool de
base disponible (arranque, tests, dev sin Postgres). En ese modo vuelve a ser
por proceso, que es exactamente lo que habia antes: nunca queda sin limite.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from . import db

log = logging.getLogger("econexo.rate_limit")

_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = asyncio.Lock()
# La ventana mas larga en uso es la de registro (1 h); se purga con ese margen.
_MAX_WINDOW = 60 * 60
_PURGE_THRESHOLD = 2048
# Probabilidad de barrer filas vencidas de claves que no volvieron a consultarse.
_SWEEP_PROBABILITY = 0.01


def client_ip(request: Request) -> str:
    """IP del cliente ya resuelta por uvicorn.

    Uvicorn corre con ``--proxy-headers --forwarded-allow-ips`` y reescribe
    ``request.client`` solo cuando el salto anterior es un proxy de confianza.
    Leer ``X-Forwarded-For`` a mano saltea esa verificacion: cualquiera podia
    mandar el header y estrenar un bucket nuevo en cada intento de login,
    anulando el limite de la fuerza bruta.
    """
    return request.client.host if request.client else "unknown"


def _too_many(retry_after: int) -> HTTPException:
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Demasiadas solicitudes. Intenta nuevamente mas tarde.",
        headers={"Retry-After": str(max(1, retry_after))},
    )


# El orden entre CTEs de un mismo statement no esta garantizado, asi que el
# advisory lock va como sentencia propia dentro de la transaccion: recien con la
# clave tomada se cuenta y se inserta. Sin eso dos replicas pueden leer el mismo
# conteo y colarse ambas por el ultimo lugar libre.
_LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtext($1))"

_PURGE_SQL = """
DELETE FROM rate_limit_hits
WHERE bucket_key = $1 AND hit_at < now() - make_interval(secs => $2)
"""

_COUNT_SQL = """
SELECT
    count(*)::int AS usados,
    GREATEST(
        1,
        CEIL(EXTRACT(EPOCH FROM (
            min(hit_at) + make_interval(secs => $2) - now()
        )))::int
    ) AS retry_after
FROM rate_limit_hits
WHERE bucket_key = $1
"""

_INSERT_SQL = "INSERT INTO rate_limit_hits (bucket_key) VALUES ($1)"

_SWEEP_SQL = """
DELETE FROM rate_limit_hits
WHERE hit_at < now() - make_interval(secs => $1)
"""


async def _enforce_in_memory(key: str, limit: int, window_seconds: int) -> None:
    now = time.monotonic()
    cutoff = now - window_seconds
    async with _lock:
        # Sin esta purga el dict crece una entrada por IP vista y nunca baja.
        # Se hace por lote para no recorrerlo entero en cada request.
        if len(_hits) > _PURGE_THRESHOLD:
            for stale in [k for k, v in _hits.items() if not v or v[-1] < now - _MAX_WINDOW]:
                del _hits[stale]
        values = _hits[key]
        while values and values[0] < cutoff:
            values.popleft()
        if len(values) >= limit:
            raise _too_many(int(window_seconds - (now - values[0])))
        values.append(now)


async def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> None:
    key = f"{bucket}:{client_ip(request)}"
    try:
        pool = db.pool()
    except RuntimeError:
        await _enforce_in_memory(key, limit, window_seconds)
        return

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(_LOCK_SQL, key)
                # Se purga primero para que el conteo siguiente sea exactamente
                # la ventana deslizante vigente, sin filtro de tiempo extra.
                await conn.execute(_PURGE_SQL, key, float(window_seconds))
                row = await conn.fetchrow(_COUNT_SQL, key, float(window_seconds))
                usados = int(row["usados"]) if row else 0
                if usados >= limit:
                    raise _too_many(int(row["retry_after"]) if row else window_seconds)
                await conn.execute(_INSERT_SQL, key)
        if random.random() < _SWEEP_PROBABILITY:
            await pool.execute(_SWEEP_SQL, float(_MAX_WINDOW))
    except HTTPException:
        raise
    except Exception as exc:
        # La base puede estar caida o la migracion 22 sin aplicar. Un endpoint
        # de auth sin ningun limite es peor que uno limitado por proceso.
        log.warning("Limitador compartido no disponible (%s); se usa el local", exc)
        await _enforce_in_memory(key, limit, window_seconds)
