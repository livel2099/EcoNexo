"""Configuracion tipada de EcoNexo.

Los valores por defecto son exclusivamente para desarrollo local. En produccion,
las variables sensibles y los endpoints publicos deben configurarse por entorno.
"""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    release_version: str = "1.0.0-rc.4-render"

    # Render y otros PaaS entregan habitualmente una URL completa. Si esta
    # presente, tiene prioridad sobre las variables POSTGRES_* individuales.
    database_url: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "econexo"
    postgres_user: str = "econexo"
    postgres_password: str = "econexo_dev_pw"
    db_pool_min_size: int = 1
    db_pool_max_size: int = 5
    db_command_timeout_seconds: float = 30.0

    jwt_secret: str = "change_me_dev_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    citizen_token_days: int = 180

    google_client_id: str = ""
    google_client_ids: str = ""

    internal_service_token: str = "change_me_internal_service_token"

    # Los adaptadores externos son opcionales para que el core pueda arrancar
    # en una primera etapa de Render. Se habilitan cuando existe infraestructura.
    mqtt_enabled: bool = True
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883

    s3_enabled: bool = True
    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "econexo-reports"
    s3_access_key: str = "econexo"
    s3_secret_key: str = "econexo_dev_pw"
    max_report_photo_bytes: int = 8 * 1024 * 1024
    s3_server_side_encryption: str = ""

    anomaly_enabled: bool = True
    anomaly_service_url: str = "http://localhost:8100"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    public_app_url: str = "http://localhost:3000"
    forwarded_allow_ips: str = "127.0.0.1"
    platform_admin_emails: str = ""
    sales_email: str = ""

    @property
    def dsn(self) -> str:
        if self.database_url.strip():
            return self.database_url.strip()
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def google_audiences(self) -> list[str]:
        values = [self.google_client_id, *self.google_client_ids.split(",")]
        return sorted({value.strip() for value in values if value.strip()})

    @property
    def platform_admin_list(self) -> list[str]:
        return sorted(
            {
                value.strip().lower()
                for value in self.platform_admin_emails.split(",")
                if value.strip()
            }
        )

    @property
    def cors_list(self) -> list[str]:
        origins = {
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        }
        if "http://localhost:3000" in origins:
            origins.add("http://127.0.0.1:3000")
        if "http://127.0.0.1:3000" in origins:
            origins.add("http://localhost:3000")
        return sorted(origins)

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def is_render(self) -> bool:
        return os.getenv("RENDER", "").strip().lower() == "true" or any(
            os.getenv(name, "").strip()
            for name in (
                "RENDER_SERVICE_ID",
                "RENDER_EXTERNAL_URL",
                "RENDER_INSTANCE_ID",
            )
        )

    @staticmethod
    def _looks_placeholder(value: str) -> bool:
        normalized = value.strip().upper()
        markers = (
            "REEMPLAZAR",
            "CHANGE_ME",
            "USUARIO:",
            ":CONTRASENA",
            "HOST-INTERNO",
            "YOUR_",
        )
        return not normalized or any(marker in normalized for marker in markers)

    def insecure_production_values(self) -> list[str]:
        findings: list[str] = []
        if not self.is_production:
            return findings

        if self._looks_placeholder(self.jwt_secret) or len(self.jwt_secret) < 32:
            findings.append("JWT_SECRET")
        if (
            self._looks_placeholder(self.internal_service_token)
            or len(self.internal_service_token) < 32
        ):
            findings.append("INTERNAL_SERVICE_TOKEN")

        # DATABASE_URL es el camino recomendado en Render. Para configuracion
        # tradicional, la contraseña local de ejemplo no se admite.
        if self.database_url.strip():
            if self._looks_placeholder(self.database_url):
                findings.append("DATABASE_URL")
        elif self._looks_placeholder(self.postgres_password) or self.postgres_password == "econexo_dev_pw":
            findings.append("DATABASE_URL/POSTGRES_PASSWORD")

        if (
            not self.public_app_url.startswith("https://")
            or "localhost" in self.public_app_url
        ):
            findings.append("PUBLIC_APP_URL")

        proxy_ips = self.forwarded_allow_ips.strip()
        if proxy_ips in {"", "0.0.0.0/0"}:
            findings.append("FORWARDED_ALLOW_IPS")
        elif proxy_ips == "*" and not self.is_render:
            findings.append("FORWARDED_ALLOW_IPS")

        if not self.cors_list or any(
            origin == "*"
            or not origin.startswith("https://")
            or "localhost" in origin
            for origin in self.cors_list
        ):
            findings.append("CORS_ORIGINS")

        if not self.platform_admin_list or any(
            "@" not in email or " " in email or self._looks_placeholder(email)
            for email in self.platform_admin_list
        ):
            findings.append("PLATFORM_ADMIN_EMAILS")

        sales_email = self.sales_email.strip().lower()
        if (
            "@" not in sales_email
            or " " in sales_email
            or self._looks_placeholder(sales_email)
        ):
            findings.append("SALES_EMAIL")

        if self.s3_enabled:
            if self.s3_secret_key == "econexo_dev_pw" or self._looks_placeholder(self.s3_secret_key):
                findings.append("S3_SECRET_KEY")
            if self._looks_placeholder(self.s3_access_key):
                findings.append("S3_ACCESS_KEY")
            if (
                not self.s3_endpoint.startswith("https://")
                or "localhost" in self.s3_endpoint
            ):
                findings.append("S3_ENDPOINT")
            if (
                not self.s3_public_endpoint.startswith("https://")
                or "localhost" in self.s3_public_endpoint
            ):
                findings.append("S3_PUBLIC_ENDPOINT")
            if self.s3_server_side_encryption not in {"AES256", "aws:kms"}:
                findings.append("S3_SERVER_SIDE_ENCRYPTION")

        if self.db_pool_min_size < 1:
            findings.append("DB_POOL_MIN_SIZE")
        if self.db_pool_max_size < self.db_pool_min_size:
            findings.append("DB_POOL_MAX_SIZE")

        return findings


@lru_cache
def get_settings() -> Settings:
    return Settings()
