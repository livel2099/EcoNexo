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


async def _database_has_core_schema(conn: asyncpg.Connection) -> bool:
    return bool(
        await conn.fetchval("SELECT to_regclass('public.organizations') IS NOT NULL")
    )


async def migrate(*, status_only: bool = False, baseline_existing: bool = False) -> None:
    settings = get_settings()
    conn = await asyncpg.connect(
        dsn=settings.dsn,
        command_timeout=max(settings.db_command_timeout_seconds, 120.0),
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
                    raise RuntimeError(
                        f"La migracion aplicada {path.name} cambio de contenido. "
                        "Cree una migracion nueva en vez de editarla."
                    )
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
    args = parser.parse_args()
    asyncio.run(
        migrate(
            status_only=args.status,
            baseline_existing=args.baseline_existing,
        )
    )


if __name__ == "__main__":
    main()
