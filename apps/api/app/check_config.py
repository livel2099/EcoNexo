"""Valida variables de entorno sin iniciar Uvicorn ni conectarse a la base."""
from __future__ import annotations

from .config import get_settings


def main() -> None:
    settings = get_settings()
    findings = settings.insecure_production_values()
    if findings:
        raise SystemExit(
            "Configuracion incompleta o insegura: " + ", ".join(findings)
        )
    print(
        "Configuracion valida: "
        f"environment={settings.environment}, "
        f"mqtt={settings.mqtt_enabled}, "
        f"s3={settings.s3_enabled}, "
        f"anomaly={settings.anomaly_enabled}"
    )


if __name__ == "__main__":
    main()
