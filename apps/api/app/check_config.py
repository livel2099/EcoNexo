"""Valida variables de entorno sin iniciar Uvicorn ni conectarse a la base."""
from __future__ import annotations

from .config import get_settings

# En Render lo unico que se ve es este log: el nombre del hallazgo por si solo
# no alcanza para saber que tocar.
_PISTAS = {
    "DATABASE_URL_ENCODING": (
        "La URL no se puede parsear. Casi siempre es la contraseña con "
        "caracteres reservados sin codificar. Reemplazar en la contraseña: "
        "[ por %5B, ] por %5D, @ por %40, / por %2F, ? por %3F, # por %23, "
        ": por %3A. asyncpg falla con el mismo error al conectar."
    ),
    "DATABASE_URL_SSLMODE": (
        "Falta sslmode=require al final de la URL (o esta puesto en "
        "disable/allow/prefer, que aceptan texto plano). El trafico a Supabase "
        "sale a internet."
    ),
    "MIGRATIONS_DATABASE_URL_ENCODING": "Mismo problema de codificacion, en MIGRATIONS_DATABASE_URL.",
    "MIGRATIONS_DATABASE_URL_SSLMODE": "Falta sslmode=require en MIGRATIONS_DATABASE_URL.",
}


def main() -> None:
    settings = get_settings()
    findings = settings.insecure_production_values()
    if findings:
        lineas = ["Configuracion incompleta o insegura: " + ", ".join(findings)]
        for finding in findings:
            pista = _PISTAS.get(finding)
            if pista:
                lineas.append(f"  - {finding}: {pista}")
        raise SystemExit("\n".join(lineas))
    print(
        "Configuracion valida: "
        f"environment={settings.environment}, "
        f"mqtt={settings.mqtt_enabled}, "
        f"s3={settings.s3_enabled}, "
        f"anomaly={settings.anomaly_enabled}"
    )


if __name__ == "__main__":
    main()
