"""Reproduce, contra la base, las mismas verificaciones que /auth/login.

El endpoint responde "Credenciales invalidas" para varias causas distintas: el
usuario no existe, el hash esta corrupto, la contrasena no coincide. Y responde
403 con otro texto si la cuenta o la organizacion estan inactivas. Desde el
navegador no se distinguen. Este script las separa una por una.

Uso:
    python scripts/check-admin-login.py [email]

Pide la DATABASE_URL y la contrasena sin mostrarlas. Solo lee: no escribe nada.
"""
from __future__ import annotations

import asyncio
import getpass
import sys

try:
    import asyncpg
    from argon2 import PasswordHasher
    from argon2.exceptions import VerificationError, VerifyMismatchError
except ModuleNotFoundError as exc:
    raise SystemExit(
        f"Falta una dependencia ({exc.name}) en este interprete.\n"
        f"  Interprete actual: {sys.executable}\n"
        "  Instalar con: pip install asyncpg argon2-cffi"
    )

# Misma consulta que routers/auth.py::login.
_SQL = """
SELECT u.id, u.email, u.role::text AS role, u.password_hash, u.is_active,
       u.auth_provider, u.must_change_password, u.password_changed_at,
       o.name AS organizacion,
       COALESCE(o.is_active, true) AS organization_active,
       COALESCE(o.access_status, 'approved') AS access_status
FROM users u
JOIN organizations o ON o.id = u.org_id
WHERE lower(u.email) = lower($1)
"""


def _ok(m: str) -> None:
    print(f"  [OK]    {m}")


def _fallo(m: str) -> None:
    print(f"  [FALLA] {m}")


async def _revisar(url: str, email: str, password: str) -> int:
    conn = await asyncpg.connect(url, timeout=15)
    try:
        row = await conn.fetchrow(_SQL, email)
    finally:
        await conn.close()

    if row is None:
        _fallo(f"No existe ningun usuario con email {email!r}.")
        print("         El JOIN con organizations tambien lo descarta si la")
        print("         organizacion fue borrada. Verificar con:")
        print(f"           select id, org_id from users where lower(email)=lower('{email}');")
        return 1
    _ok(f"Usuario encontrado (rol {row['role']}, organizacion {row['organizacion']!r}).")

    # El hash pegado a mano es la fuente habitual de corrupcion: un salto de
    # linea o un espacio de mas lo invalidan y argon2 no puede ni parsearlo.
    hash_guardado = row["password_hash"]
    if not hash_guardado:
        _fallo("El usuario no tiene password_hash (probablemente entra con Google).")
        return 1
    largo = len(hash_guardado)
    if hash_guardado != hash_guardado.strip():
        _fallo(f"El hash tiene espacios o saltos de linea alrededor (largo {largo}).")
        print("         Se cuelan al pegar en el editor SQL. Corregir con:")
        print("           update users set password_hash = trim(password_hash)")
        print(f"           where lower(email)=lower('{email}');")
        return 1
    if not hash_guardado.startswith("$argon2"):
        _fallo(f"El hash no tiene formato argon2: empieza con {hash_guardado[:12]!r}.")
        return 1
    if largo != 97:
        print(f"  [AVISO] El hash mide {largo} caracteres; lo normal son 97.")
        print("          Puede estar truncado al copiar.")
    else:
        _ok(f"El hash tiene formato argon2 y largo correcto ({largo}).")

    try:
        PasswordHasher().verify(hash_guardado, password)
        _ok("La contrasena coincide con el hash guardado.")
    except VerifyMismatchError:
        _fallo("La contrasena NO coincide con el hash guardado.")
        print("         El hash de la base corresponde a otra contrasena.")
        print("         Regenerarlo con: python scripts/generar-hash-password.py")
        return 1
    except VerificationError as exc:
        _fallo(f"El hash guardado no se puede procesar: {exc}")
        print("         Esta corrupto. Regenerarlo y volver a aplicarlo.")
        return 1

    # Estas dos no dan "Credenciales invalidas" sino 403 con otro texto, pero
    # conviene verlas aca antes de volver al navegador.
    if row["access_status"] == "pending":
        _fallo("La organizacion esta en 'pending': el login responde 403.")
        return 1
    if not row["is_active"] or not row["organization_active"]:
        _fallo(
            f"Cuenta activa: {row['is_active']} / organizacion activa: "
            f"{row['organization_active']}. El login responde 403."
        )
        return 1
    _ok("Cuenta y organizacion activas, alta aprobada.")

    print("\nEsta credencial deberia entrar.")
    print("Si el navegador sigue rechazandola, la API esta leyendo OTRA base:")
    print("comparar la DATABASE_URL de Render con la que se uso aca.")
    return 0


def main() -> None:
    print(__doc__.split("Uso:")[0].strip())
    email = sys.argv[1] if len(sys.argv) > 1 else input("\nEmail: ").strip()
    if not email:
        raise SystemExit("El email es obligatorio.")
    url = getpass.getpass("DATABASE_URL (no se muestra): ").strip()
    if not url.startswith(("postgresql://", "postgres://")):
        raise SystemExit("Eso no es una URL de conexion: tiene que empezar con postgresql://")
    password = getpass.getpass("Contrasena a probar (no se muestra): ")
    raise SystemExit(asyncio.run(_revisar(url, email, password)))


if __name__ == "__main__":
    main()
