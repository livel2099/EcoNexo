"""Valida variables de entorno sin iniciar Uvicorn ni conectarse a la base."""
from __future__ import annotations

from pydantic import ValidationError

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


def _cargar_settings():
    """Traduce el ValidationError de pydantic a una linea por variable.

    El traceback crudo ocupa quince lineas de stack de pydantic y entierra el
    unico dato util —que variable y con que valor— en la ultima. En Render eso
    es lo unico que se ve, y cada lectura equivocada cuesta un deploy.
    """
    try:
        return get_settings()
    except ValidationError as exc:
        lineas = ["Variables de entorno con valores invalidos:"]
        for error in exc.errors():
            variable = str(error["loc"][0]).upper() if error["loc"] else "(desconocida)"
            recibido = repr(error.get("input"))
            lineas.append(f"  - {variable}: {error['msg']}. Recibido: {recibido}")
        lineas.append(
            "  Revisar esos valores en Render > Environment. Un caracter de mas"
        )
        lineas.append("  al pegar (por ejemplo 'true<') alcanza para invalidarlos.")
        raise SystemExit("\n".join(lineas)) from exc


def main() -> None:
    settings = _cargar_settings()
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
