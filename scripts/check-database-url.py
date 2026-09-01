"""Verifica una DATABASE_URL antes de cargarla en Render.

Cada intento contra Render cuesta un deploy completo y el traceback de asyncpg
no dice que host intento resolver. Esto hace las mismas comprobaciones que hace
el arranque de la API, en orden, y explica cada fallo.

Uso:
    python scripts/check-database-url.py

Pide la URL sin mostrarla en pantalla. No la escribe en ningun archivo ni la
deja en el historial de la shell.
"""
from __future__ import annotations

import asyncio
import getpass
import socket
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "apps" / "api"))

try:
    import asyncpg
except ModuleNotFoundError:
    raise SystemExit(
        "Falta asyncpg en este interprete.\n"
        f"  Interprete actual: {sys.executable}\n"
        "  Instalar con: pip install asyncpg\n"
        "  (si tenes un venv del proyecto, activalo primero)"
    )

from app.config import Settings  # noqa: E402


def _ok(mensaje: str) -> None:
    print(f"  [OK]    {mensaje}")


def _fallo(mensaje: str) -> None:
    print(f"  [FALLA] {mensaje}")


async def _probar(url: str) -> int:
    resumen = Settings.describe_dsn(url)
    print(f"\nURL: {resumen}\n")

    # 1. Parseo. asyncpg usa urlparse por dentro: si esto falla, no conecta.
    if not Settings._dsn_is_parseable(url):
        _fallo("La URL no se puede parsear.")
        print(
            "         Casi siempre es la contrasena con caracteres reservados.\n"
            "         Codificar: [ -> %5B   ] -> %5D   @ -> %40   / -> %2F\n"
            "                    ? -> %3F   # -> %23   : -> %3A\n"
            "         Ojo: [YOUR-PASSWORD] es un placeholder de Supabase, hay\n"
            "         que reemplazarlo entero, corchetes incluidos."
        )
        return 1
    _ok("La URL parsea.")

    # 2. TLS. En produccion la guarda de config.py aborta el arranque sin esto.
    if Settings._dsn_has_tls(url):
        _ok("Lleva sslmode que exige TLS.")
    else:
        _fallo("Falta sslmode=require (o esta en disable/allow/prefer).")
        print("         En produccion el arranque aborta con DATABASE_URL_SSLMODE.")

    # 3. DNS.
    host = resumen.split("@", 1)[-1].split("/", 1)[0]
    nombre, _, puerto = host.rpartition(":")
    nombre = nombre or host
    try:
        infos = socket.getaddrinfo(nombre, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        _fallo(f"El host no resuelve en DNS: {nombre}")
        print(f"         {exc}")
        if nombre.startswith("db.") and nombre.endswith(".supabase.co"):
            print(
                "         Ese es el host de Direct connection. Render no tiene\n"
                "         salida IPv6, hay que usar el Session pooler:\n"
                "         Supabase > Connect > Session pooler (puerto 5432).\n"
                "         El usuario cambia a postgres.<ref>."
            )
        print("         Si el host es correcto, revisa que el proyecto de")
        print("         Supabase no este pausado: al pausarlo retiran el DNS.")
        return 1
    familias = sorted({"IPv6" if i[0] == socket.AF_INET6 else "IPv4" for i in infos})
    _ok(f"DNS resuelve ({', '.join(familias)}).")
    if familias == ["IPv6"]:
        _fallo("Solo tiene IPv6. Render no puede salir por IPv6.")
        print("         Usar el Session pooler, que si tiene IPv4.")

    # 4. Conexion real.
    try:
        conn = await asyncpg.connect(url, timeout=15)
    except asyncpg.InvalidPasswordError:
        _fallo("Host alcanzado, pero la contrasena es incorrecta.")
        print("         Se puede regenerar en Supabase > Settings > Database.")
        return 1
    except Exception as exc:
        _fallo(f"No conecta: {type(exc).__name__}: {exc}")
        return 1

    try:
        _ok("Conecta y autentica.")
        version = await conn.fetchval("SELECT version()")
        print(f"          {str(version).split(',', 1)[0]}")

        # 5. Extensiones visibles: el modo de falla tipico de Supabase.
        esquemas = await conn.fetchval("SELECT array_to_string(current_schemas(true), ',')")
        print(f"          search_path efectivo: {esquemas}")
        faltantes = await conn.fetch(
            """
            SELECT unnest($1::text[]) AS nombre
            EXCEPT
            SELECT extname FROM pg_extension
            """,
            ["postgis", "uuid-ossp", "pgcrypto"],
        )
        invisibles = await conn.fetch(
            """
            SELECT e.extname, n.nspname
            FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace
            WHERE e.extname = ANY($1::text[])
              AND n.nspname <> ALL (current_schemas(true))
            """,
            ["postgis", "uuid-ossp", "pgcrypto"],
        )
        if faltantes:
            nombres = ", ".join(r["nombre"] for r in faltantes)
            print(f"  [AVISO] Extensiones no instaladas: {nombres}")
            print("          Las crea la migracion 01 si el rol tiene permiso.")
        if invisibles:
            detalle = ", ".join(f"{r['extname']} en '{r['nspname']}'" for r in invisibles)
            _fallo(f"Extensiones fuera del search_path: {detalle}")
            print("         Cargar DB_SEARCH_PATH=public,extensions en Render.")
            return 1
        if not faltantes and not invisibles:
            _ok("postgis, uuid-ossp y pgcrypto estan instaladas y visibles.")
    finally:
        await conn.close()

    print("\nLa URL sirve. Se puede cargar en Render.")
    return 0


def main() -> None:
    print(__doc__.split("Uso:")[0].strip())
    url = getpass.getpass("\nDATABASE_URL (no se muestra): ").strip()
    if not url:
        raise SystemExit("No se ingreso ninguna URL.")
    raise SystemExit(asyncio.run(_probar(url)))


if __name__ == "__main__":
    main()
