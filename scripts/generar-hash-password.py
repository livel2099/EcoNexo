"""Genera el hash argon2id de una contrasena y el UPDATE para aplicarlo.

EcoNexo guarda las contrasenas con argon2id (apps/api/app/security.py). pgcrypto
no implementa argon2 —solo bcrypt, md5 y des— asi que no hay forma de escribir
la contraseña desde SQL puro: el hash se calcula aca y a la base va solo el
resultado.

Uso:
    python scripts/generar-hash-password.py [email]

La contrasena se pide sin mostrarla y no se escribe a disco. Lo que se imprime
es el hash, que es lo unico que necesita la base.
"""
from __future__ import annotations

import getpass
import sys

try:
    from argon2 import PasswordHasher
except ModuleNotFoundError:
    raise SystemExit(
        "Falta argon2-cffi en este interprete.\n"
        f"  Interprete actual: {sys.executable}\n"
        "  Instalar con: pip install argon2-cffi"
    )


def main() -> None:
    email = sys.argv[1] if len(sys.argv) > 1 else input("Email de la cuenta: ").strip()
    if not email:
        raise SystemExit("El email es obligatorio.")

    password = getpass.getpass("Contrasena nueva (no se muestra): ")
    if len(password) < 8:
        raise SystemExit("La contrasena debe tener al menos 8 caracteres.")
    # Mismas reglas que _validate_password en routers/auth.py: si no las cumple,
    # la cuenta no va a poder cambiarla despues desde la propia plataforma.
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise SystemExit("La contrasena debe tener al menos una letra y un numero.")
    if password != getpass.getpass("Repetir contrasena: "):
        raise SystemExit("Las contrasenas no coinciden.")

    # PasswordHasher() con los parametros por defecto: los mismos que usa la API.
    hash_argon2 = PasswordHasher().hash(password)

    print("\n-- Ejecutar en el SQL Editor de Supabase.")
    print("-- El hash no permite recuperar la contrasena: es seguro pegarlo aca.")
    print(
        f"""
UPDATE users
SET password_hash = '{hash_argon2}',
    auth_provider = 'password',
    is_active = true,
    must_change_password = false,
    password_changed_at = now(),
    updated_at = now()
WHERE lower(email) = lower('{email}');
"""
    )
    print("-- Verificar que afecto exactamente una fila:")
    print(
        f"SELECT email, role, is_active, password_changed_at\n"
        f"FROM users WHERE lower(email) = lower('{email}');"
    )
    print(
        "\n-- password_changed_at deja de ser NULL, asi que el bootstrap por\n"
        "-- variables de entorno ya no vuelve a pisar esta contrasena."
    )


if __name__ == "__main__":
    main()
