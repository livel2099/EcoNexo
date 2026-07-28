import os
"""Configuracion tipada de EcoNexo.

Los valores por defecto son exclusivamente para desarrollo local. En produccion,
@@ -7,6 +6,7 @@
"""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
@@ -28,12 +28,9 @@
    jwt_expire_minutes: int = 60 * 12
    citizen_token_days: int = 180

    # Google Identity Services. Se acepta el cliente web y, opcionalmente,
    # clientes nativos de Android/iOS separados por coma.
    google_client_id: str = ""
    google_client_ids: str = ""

    # Credencial compartida solo entre servicios internos.
    internal_service_token: str = "change_me_internal_service_token"

    mqtt_host: str = "localhost"
@@ -73,8 +70,6 @@
    @property
    def cors_list(self) -> list[str]:
        origins = {o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()}
        # En desarrollo, localhost y 127.0.0.1 son equivalentes para el usuario,
        # pero el navegador los trata como origins distintos. Aceptamos ambos.
        if "http://localhost:3000" in origins:
            origins.add("http://127.0.0.1:3000")
        if "http://127.0.0.1:3000" in origins:
@@ -107,19 +102,18 @@
        if self.s3_server_side_encryption not in {"AES256", "aws:kms"}:
            findings.append("S3_SERVER_SIDE_ENCRYPTION")
        proxy_ips = self.forwarded_allow_ips.strip()

        if proxy_ips in {"", "0.0.0.0/0"}:
        findings.append("FORWARDED_ALLOW_IPS")
            findings.append("FORWARDED_ALLOW_IPS")
        elif proxy_ips == "*" and os.getenv("RENDER", "").lower() != "true":
        findings.append("FORWARDED_ALLOW_IPS")
            findings.append("FORWARDED_ALLOW_IPS")
        if not self.cors_list or any(
            origin == "*" or not origin.startswith("https://") or "localhost" in origin
            for origin in self.cors_list
        ):
            findings.append("CORS_ORIGINS")
        return findings


@lru_cache
def get_settings() -> Settings:
    return Settings()