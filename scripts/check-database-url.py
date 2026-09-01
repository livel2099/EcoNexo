"""Verifica una DATABASE_URL antes de cargarla en Render.

Cada intento contra Render cuesta un deploy completo y el traceback de asyncpg
no dice que host intento resolver. Esto hace las mismas comprobaciones que hace
el arranque de la API, en orden, y explica cada fallo.

Uso:
    python scripts/check-database-url.py            # pega la URL ya armada
    python scripts/check-database-url.py --armar    # la arma por partes

El modo --armar pide project ref, region y contrasena por separado, codifica la
contrasena y agrega sslmode=require. Evita los tres errores tipicos: dejar un
placeholder sin reemplazar, equivocar la region y no codificar los caracteres
reservados.

En los dos modos la contrasena se pide sin mostrarla en pantalla, y nada se
escribe a disco ni queda en el historial de la shell.
"""
from __future__ import annotations

import asyncio
import getpass
import socket
import sys
from urllib.parse import quote, urlparse

try:
    import asyncpg
except ModuleNotFoundError:
    raise SystemExit(
        "Falta asyncpg en este interprete.\n"
        f"  Interprete actual: {sys.executable}\n"
        "  Instalar con: pip install asyncpg\n"
        "  (si tenes un venv del proyecto, activalo primero)"
    )


# Las tres funciones siguientes son copia de apps/api/app/config.py. Se
# duplican a proposito: este script tiene que poder correr en una maquina sin
# las dependencias de la API instaladas (pydantic, fastapi y demas), que es el
# caso tipico de quien esta configurando Render desde su portatil.


def describe_dsn(dsn: str) -> str:
    """`usuario@host:puerto/base`, sin la contrasena. Nunca levanta."""
    if not dsn.strip():
        return "(vacia)"
    resto = dsn.split("://", 1)[-1].split("?", 1)[0]
    netloc, _, ruta = resto.partition("/")
    # rpartition: la contrasena puede traer un `@` sin codificar.
    userinfo, _, hostport = netloc.rpartition("@")
    usuario = userinfo.split(":", 1)[0] if userinfo else "(sin usuario)"
    return f"{usuario}@{hostport or '(sin host)'}/{ruta or '(sin base)'}"


def dsn_query(dsn: str) -> str:
    _, separador, query = dsn.partition("?")
    return query if separador else ""


def dsn_has_tls(dsn: str) -> bool:
    modes = [
        value.split("=", 1)[1].strip().lower()
        for value in dsn_query(dsn).split("&")
        if value.strip().lower().startswith("sslmode=")
    ]
    return bool(modes) and modes[-1] not in {"disable", "allow", "prefer"}


def dsn_is_parseable(dsn: str) -> bool:
    """asyncpg parsea con urlparse: si esto falla, la conexion tampoco abre."""
    try:
        urlparse(dsn)
    except ValueError:
        return False
    return True


def _ok(mensaje: str) -> None:
    print(f"  [OK]    {mensaje}")


def _fallo(mensaje: str) -> None:
    print(f"  [FALLA] {mensaje}")


# Restos de plantilla que se copian sin querer. Los angulos vienen de la
# documentacion; los tokens, del panel de Supabase y de los .env.example.
_PLACEHOLDERS_SIMBOLO = ("<", ">")
# Se comparan respetando mayusculas a proposito. Una version insensible marcaba
# como plantilla cualquier contrasena que contuviera "contrasena" o "usuario"
# en minuscula, que es texto perfectamente valido dentro de una contrasena.
_PLACEHOLDERS_TOKEN = (
    "YOUR-PASSWORD", "YOUR_PASSWORD", "TU_PASSWORD", "CONTRASENA_NUEVA",
    "CONTRASENA_URL_ENCODED", "PASSWORD_CODIFICADA", "REEMPLAZAR",
    "PROJECT_REF", "HOST-INTERNO", "CONTRASENA", "USUARIO",
)


def _placeholders_presentes(url: str) -> list[str]:
    hallados = [p for p in _PLACEHOLDERS_SIMBOLO if p in url]
    hallados += [p for p in _PLACEHOLDERS_TOKEN if p in url]
    return hallados


async def _probar(url: str) -> int:
    resumen = describe_dsn(url)
    print(f"\nURL: {resumen}\n")

    # 0. Plantilla sin completar. Sin esto el sintoma es un fallo de DNS sobre
    # un host que contiene "<region>", y el mensaje habla de Supabase pausado.
    restos = _placeholders_presentes(url)
    if restos:
        _fallo(f"La URL todavia tiene texto de plantilla: {', '.join(restos)}")
        print(
            "         Hay que reemplazar esos tramos por los valores reales.\n"
            "         El string completo esta en Supabase > Connect > Session\n"
            "         pooler; conviene copiarlo de ahi entero en vez de armarlo\n"
            "         a mano, y despues solo cambiar la contrasena y agregar\n"
            "         ?sslmode=require al final."
        )
        return 1

    # 1. Parseo. asyncpg usa urlparse por dentro: si esto falla, no conecta.
    if not dsn_is_parseable(url):
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
    if dsn_has_tls(url):
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


def _normalizar_ref(valor: str) -> str:
    """Extrae el ref aunque le peguen el host completo o el usuario del pooler.

    El panel muestra el ref dentro de `db.<ref>.supabase.co` y dentro de
    `postgres.<ref>`, asi que es natural copiar cualquiera de los dos enteros.
    Sin esto el resultado era un `tenant/user not found` bastante opaco.
    """
    limpio = valor.strip().strip("/")
    if "://" in limpio:
        # En una URL completa el ref esta en el usuario, no en el host.
        limpio = limpio.split("://", 1)[1].split("@", 1)[0]
    else:
        limpio = limpio.split("@")[-1]
    limpio = limpio.split(":")[0]
    if limpio.startswith("db."):
        limpio = limpio[3:]
    if limpio.startswith("postgres."):
        limpio = limpio[len("postgres."):]
    for sufijo in (".supabase.co", ".supabase.com"):
        if limpio.endswith(sufijo):
            limpio = limpio[: -len(sufijo)]
    if limpio != valor.strip():
        print(f"    (interpretado como: {limpio})")
    if limpio and not limpio.isalnum():
        print(f"    AVISO: '{limpio}' no parece un ref (son solo letras y numeros).")
    return limpio


def _armar() -> str:
    """Construye la URL pidiendo las piezas por separado.

    Armarla a mano genero, en una sola sesion, cuatro intentos fallidos:
    placeholders sin reemplazar, region equivocada y caracteres reservados sin
    codificar. Pidiendo cada parte no queda margen para eso.
    """
    print("\nDatos del proyecto (Supabase > Connect > Session pooler):")
    print("  El project ref son ~20 letras y numeros, sin puntos.")
    print("  Ej: en db.abcdefghijklmnopqrst.supabase.co el ref es")
    print("      abcdefghijklmnopqrst")
    ref = _normalizar_ref(input("  Project ref: ").strip())
    if not ref:
        raise SystemExit("El project ref es obligatorio.")
    region = input("  Region [us-east-1]: ").strip() or "us-east-1"
    numero = input("  Numero de pooler, aws-0 o aws-1 [0]: ").strip() or "0"
    password = getpass.getpass("  Password de la base (no se muestra): ")
    if not password:
        raise SystemExit("La contrasena es obligatoria.")
    # quote con safe="" codifica todo lo reservado: @ [ ] / ? # : y demas.
    return (
        f"postgresql://postgres.{ref}:{quote(password, safe='')}"
        f"@aws-{numero}-{region}.pooler.supabase.com:5432/postgres?sslmode=require"
    )


def main() -> None:
    print(__doc__.split("Uso:")[0].strip())
    armada = "--armar" in sys.argv
    if armada:
        url = _armar()
    else:
        print("\n(Si preferis que el script la arme por partes: --armar)")
        url = getpass.getpass("\nDATABASE_URL completa (no se muestra): ").strip()
        if not url:
            raise SystemExit("No se ingreso ninguna URL.")
        if not url.startswith(("postgresql://", "postgres://")):
            raise SystemExit(
                "Eso no es una URL de conexion: tiene que empezar con\n"
                "  postgresql://\n"
                "Si lo que pegaste fue un comando de shell, ese va en la\n"
                "terminal, no en este prompt. Para armar la URL por partes:\n"
                "  python scripts/check-database-url.py --armar"
            )
    codigo = asyncio.run(_probar(url))
    if codigo == 0 and armada:
        print("\nCargar en Render > Environment > DATABASE_URL este valor")
        print("(contiene la contrasena: no pegarlo en chats ni capturas):\n")
        print(f"  {url}\n")
    raise SystemExit(codigo)


if __name__ == "__main__":
    main()
