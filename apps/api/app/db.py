"""Pool asyncpg compartido. asyncpg maneja PostGIS via texto/GeoJSON en SQL.

La base es Supabase: la conexion sale a internet por el Session pooler, no es
un servicio interno. Eso obliga a fijar el ``search_path`` (las extensiones no
viven en ``public``) y a poder desactivar el cache de prepared statements.
"""
from __future__ import annotations

import logging

import asyncpg

from .config import get_settings

log = logging.getLogger("econexo.db")

_pool: asyncpg.Pool | None = None


async def connect() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        settings = get_settings()
        log.info("Abriendo pool contra %s", settings.describe_dsn(settings.dsn))
        _pool = await asyncpg.create_pool(
            dsn=settings.dsn,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            command_timeout=settings.db_command_timeout_seconds,
            **settings.db_connect_kwargs,
        )
    return _pool


async def disconnect() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool no inicializado")
    return _pool
