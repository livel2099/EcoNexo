"""Ejecutor de migraciones SQL para Render y otros entornos administrados.

Uso:
    python -m app.migrate
    python -m app.migrate --status

El comando aplica archivos de ``/app/migrations`` en orden alfanumerico y guarda
el checksum de cada archivo en ``schema_migrations``. No intenta adivinar el
estado de una base preexistente sin historial para evitar aplicar 01_schema.sql
sobre objetos ya creados.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
from pathlib import Path

import asyncpg

from .config import get_settings

_LOCK_ID = 725_901_2026


def _migration_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parents[1] / "migrations",
        Path("/app/migrations"),
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise RuntimeError("No se encontro el directorio de migraciones")


def _files() -> list[Path]:
    files = sorted(_migration_dir().glob("*.sql"), key=lambda path: path.name)
    if not files:
        raise RuntimeError("No se encontraron archivos SQL de migracion")
    return files


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def _ensure_tracking(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


# Las tres que crea 01_schema.sql y que el esquema usa sin calificar
# (uuid_generate_v4, gen_random_uuid, ST_MakePoint...).
_REQUIRED_EXTENSIONS = ("postgis", "uuid-ossp", "pgcrypto")


async def _check_extension_visibility(conn: asyncpg.Connection) -> None:
    """Falla temprano si una extension existe pero fuera del search_path.

    Es el modo de falla tipico de Supabase: habilitar PostGIS desde el panel la
    instala en el esquema ``extensions``. Ahi ``CREATE EXTENSION IF NOT EXISTS``
    no hace nada, pero ``uuid_generate_v4()`` tampoco resuelve, y la migracion
    01 muere con un "function does not exist" que no dice nada del search_path.
    """
    invisibles = await conn.fetch(
        """
        SELECT e.extname, n.nspname
        FROM pg_extension e
        JOIN pg_namespace n ON n.oid = e.extnamespace
        WHERE e.extname = ANY($1::text[])
          AND n.nspname <> ALL (current_schemas(true))
        """,
        list(_REQUIRED_EXTENSIONS),
    )
    if not invisibles:
        return
    detalle = ", ".join(f"{row['extname']} en '{row['nspname']}'" for row in invisibles)
    visibles = await conn.fetchval("SELECT array_to_string(current_schemas(true), ',')")
    raise RuntimeError(
        f"Extensiones fuera del search_path: {detalle}. "
        f"El search_path actual es '{visibles}'. "
        "Agregue esos esquemas a DB_SEARCH_PATH (en Supabase suele ser "
        "'public,extensions') y vuelva a ejecutar las migraciones."
    )


async def _database_has_core_schema(conn: asyncpg.Connection) -> bool:
    return bool(
        await conn.fetchval("SELECT to_regclass('public.organizations') IS NOT NULL")
    )


async def migrate(
    *,
    status_only: bool = False,
    baseline_existing: bool = False,
    strict_checksums: bool = False,
) -> None:
    settings = get_settings()
    conn = await asyncpg.connect(
        dsn=settings.migration_dsn,
        command_timeout=max(settings.db_command_timeout_seconds, 120.0),
        **settings.db_connect_kwargs,
    )
    try:
        await conn.execute("SELECT pg_advisory_lock($1)", _LOCK_ID)
        tracking_existed = bool(
            await conn.fetchval(
                "SELECT to_regclass('public.schema_migrations') IS NOT NULL"
            )
        )
        core_existed = await _database_has_core_schema(conn)
        await _ensure_tracking(conn)

        applied_rows = await conn.fetch(
            "SELECT filename, checksum, applied_at FROM schema_migrations"
        )
        applied = {row["filename"]: row for row in applied_rows}
        files = _files()

        if status_only:
            for path in files:
                row = applied.get(path.name)
                state = "aplicada" if row else "pendiente"
                print(f"{state:9} {path.name}")
            return

        # Despues de --status para que consultar el estado siga funcionando
        # aunque el search_path este mal, que es justo cuando se lo consulta.
        await _check_extension_visibility(conn)

        if core_existed and not tracking_existed and not applied and not baseline_existing:
            raise RuntimeError(
                "La base ya contiene tablas de EcoNexo pero no tiene historial de "
                "schema_migrations. Verifique la base y ejecute una sola vez "
                "`python -m app.migrate --baseline-existing` o use una base vacia."
            )

        if baseline_existing and core_existed and not applied:
            for path in files:
                await conn.execute(
                    """
                    INSERT INTO schema_migrations(filename, checksum)
                    VALUES ($1, $2)
                    ON CONFLICT (filename) DO NOTHING
                    """,
                    path.name,
                    _checksum(path),
                )
                print(f"baseline  {path.name}")
            return

        for path in files:
            checksum = _checksum(path)
            row = applied.get(path.name)
            if row:
                if row["checksum"] != checksum:
                    if strict_checksums:
                        raise RuntimeError(
                            f"La migracion aplicada {path.name} cambio de contenido. "
                            "Cree una migracion nueva en vez de editarla."
                        )
                    # Abortar aca deja el deploy muerto sin forma de recuperarlo
                    # en entornos sin shell (Render). Se re-sincroniza el
                    # checksum y se sigue, pero el SQL editado NO se re-ejecuta.
                    print(f"resync    {path.name}")
                    print("          ATENCION: cambio despues de aplicarse. Se")
                    print("          actualiza el checksum pero su SQL no se")
                    print("          re-ejecuta. Si la edicion agrega esquema,")
                    print("          replicala en una migracion nueva.")
                    await conn.execute(
                        "UPDATE schema_migrations SET checksum=$2 WHERE filename=$1",
                        path.name,
                        checksum,
                    )
                    continue
                print(f"skip      {path.name}")
                continue

            print(f"apply     {path.name}")
            sql = path.read_text(encoding="utf-8")
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations(filename, checksum) VALUES ($1, $2)",
                path.name,
                checksum,
            )

        print("Migraciones EcoNexo completadas")
    finally:
        try:
            await conn.execute("SELECT pg_advisory_unlock($1)", _LOCK_ID)
        except Exception:
            pass
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migraciones EcoNexo")
    parser.add_argument("--status", action="store_true")
    parser.add_argument(
        "--baseline-existing",
        action="store_true",
        help=(
            "Marca una base existente como migrada sin ejecutar SQL. "
            "Usar SOLO si la base ya tiene TODAS las migraciones del repo: "
            "cualquier archivo pendiente queda marcado como aplicado y su SQL "
            "no corre nunca, dejando el esquema atrasado respecto del codigo."
        ),
    )
    parser.add_argument(
        "--strict-checksums",
        action="store_true",
        help=(
            "Aborta si una migracion aplicada cambio de contenido, en vez de "
            "re-sincronizar el checksum. Pensado para CI y entornos locales."
        ),
    )
    args = parser.parse_args()
    asyncio.run(
        migrate(
            status_only=args.status,
            baseline_existing=args.baseline_existing,
            strict_checksums=args.strict_checksums,
        )
    )


if __name__ == "__main__":
    main()
