from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "econexo"
    postgres_user: str = "econexo"
    postgres_password: str = "econexo_dev_pw"

    jwt_secret: str = "change_me_dev_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    citizen_token_days: int = 180

    # Google Identity Services. Se acepta el cliente web y, opcionalmente,
    # clientes nativos de Android/iOS separados por coma.
    google_client_id: str = ""
    google_client_ids: str = ""

    # Credencial compartida solo entre servicios internos.
    internal_service_token: str = "change_me_internal_service_token"

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883

    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "econexo-reports"
    s3_access_key: str = "econexo"
    s3_secret_key: str = "econexo_dev_pw"
    max_report_photo_bytes: int = 8 * 1024 * 1024
    s3_server_side_encryption: str = ""

    anomaly_service_url: str = "http://localhost:8100"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    public_app_url: str = "http://localhost:3000"
    forwarded_allow_ips: str = "127.0.0.1"
    platform_admin_emails: str = ""
    sales_email: str = ""

    @property
    def dsn(self) -> str:
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
        return sorted({value.strip().lower() for value in self.platform_admin_emails.split(",") if value.strip()})

    @property
    def cors_list(self) -> list[str]:
        origins = {o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()}
        # En desarrollo, localhost y 127.0.0.1 son equivalentes para el usuario,
        # pero el navegador los trata como origins distintos. Aceptamos ambos.
        if "http://localhost:3000" in origins:
            origins.add("http://127.0.0.1:3000")
        if "http://127.0.0.1:3000" in origins:
            origins.add("http://localhost:3000")
        return sorted(origins)

        def insecure_production_values(self) -> list[str]:
        findings: list[str] = []

        if not self.is_production:
            return findings

        if self.jwt_secret == "change_me_dev_secret" or len(self.jwt_secret) < 32:
            findings.append("JWT_SECRET")

        if (
            self.internal_service_token == "change_me_internal_service_token"
            or len(self.internal_service_token) < 32
        ):
            findings.append("INTERNAL_SERVICE_TOKEN")

        if self.postgres_password == "econexo_dev_pw":
            findings.append("POSTGRES_PASSWORD")

        if self.s3_secret_key == "econexo_dev_pw":
            findings.append("S3_SECRET_KEY")

        if (
            not self.public_app_url.startswith("https://")
            or "localhost" in self.public_app_url
        ):
            findings.append("PUBLIC_APP_URL")

        if (
            not self.s3_public_endpoint.startswith("https://")
            or "localhost" in self.s3_public_endpoint
        ):
            findings.append("S3_PUBLIC_ENDPOINT")

        if self.s3_server_side_encryption not in {"AES256", "aws:kms"}:
            findings.append("S3_SERVER_SIDE_ENCRYPTION")

        proxy_ips = self.forwarded_allow_ips.strip()
        running_on_render = os.getenv("RENDER", "").lower() == "true"

        if proxy_ips in {"", "0.0.0.0/0"}:
            findings.append("FORWARDED_ALLOW_IPS")
        elif proxy_ips == "*" and not running_on_render:
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
