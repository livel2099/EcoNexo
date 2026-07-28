"""Configuracion tipada de EcoNexo para desarrollo local y Render."""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    release_version: str = "1.0.0-rc.6.2-render"

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

    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"

    # Copernicus Data Space Ecosystem. Process API es el modo predeterminado;
    # las credenciales quedan exclusivamente en el backend. WMS es fallback.
    copernicus_enabled_by_default: bool = True
    copernicus_mode: str = "process_api"
    copernicus_client_id: str = ""
    copernicus_client_secret: str = ""
    copernicus_token_url: str = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    copernicus_process_url: str = "https://sh.dataspace.copernicus.eu/process/v1"
    copernicus_instance_id: str = ""
    copernicus_wms_url: str = ""
    copernicus_http_timeout_seconds: float = 45.0
    copernicus_time_range_days: int = 90
    copernicus_max_cloud_coverage: int = 80
    copernicus_max_dimension: int = 1024
    copernicus_cache_seconds: int = 600

    nasa_firms_key: str = ""
    firms_inline_enabled: bool = True
    firms_source: str = "VIIRS_SNPP_NRT"
    pipeline_max_devices_per_run: int = 100
    pipeline_http_timeout_seconds: float = 20.0

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    public_app_url: str = "http://localhost:3000"
    forwarded_allow_ips: str = "127.0.0.1"

    platform_admin_emails: str = "econexoargentina@gmail.com"
    platform_admin_bootstrap_enabled: bool = False
    platform_admin_initial_password: str = ""
    platform_admin_force_password_change: bool = True
    platform_admin_reset_initial_password: bool = False
    platform_admin_name: str = "Administrador General EcoNexo"
    platform_admin_organization: str = "EcoNexo Plataforma"
    sales_email: str = ""

    @property
    def dsn(self) -> str:
        value = self.database_url.strip()
        if value:
            if value.startswith("postgres://"):
                value = "postgresql://" + value[len("postgres://"):]
            return value
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def copernicus_mode_normalized(self) -> str:
        value = self.copernicus_mode.strip().lower().replace("-", "_")
        return value if value in {"process_api", "wms"} else "process_api"

    @property
    def copernicus_process_configured(self) -> bool:
        return bool(
            self.copernicus_client_id.strip()
            and self.copernicus_client_secret.strip()
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
        """Orígenes permitidos para navegador.

        PUBLIC_APP_URL se incorpora siempre para evitar que una variable
        CORS_ORIGINS desactualizada deje al frontend sin acceso. En producción
        también se conserva el dominio oficial de la beta en Render.
        """
        raw_values = self.cors_origins.replace(";", ",").replace("\n", ",")
        origins = {
            origin.strip().rstrip("/")
            for origin in raw_values.split(",")
            if origin.strip()
        }

        public_origin = self.public_app_url.strip().rstrip("/")
        if public_origin.startswith(("http://", "https://")):
            origins.add(public_origin)

        configured_web_origin = os.getenv("ECONEXO_WEB_ORIGIN", "").strip().rstrip("/")
        if configured_web_origin.startswith(("http://", "https://")):
            origins.add(configured_web_origin)

        if self.is_production:
            origins.add("https://econexo-web.onrender.com")

        if "http://localhost:3000" in origins:
            origins.add("http://127.0.0.1:3000")
        if "http://127.0.0.1:3000" in origins:
            origins.add("http://localhost:3000")
        return sorted(origins)

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

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
            "TU_",
            "SECRETO_",
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

        if self.database_url.strip():
            if self._looks_placeholder(self.database_url):
                findings.append("DATABASE_URL")
        elif (
            self._looks_placeholder(self.postgres_password)
            or self.postgres_password == "econexo_dev_pw"
        ):
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

        if self.platform_admin_bootstrap_enabled:
            password = self.platform_admin_initial_password
            if self._looks_placeholder(password) or len(password) < 12:
                findings.append("PLATFORM_ADMIN_INITIAL_PASSWORD")
            if not any(char.isalpha() for char in password) or not any(
                char.isdigit() for char in password
            ):
                findings.append("PLATFORM_ADMIN_INITIAL_PASSWORD_COMPLEXITY")

        sales_email = self.sales_email.strip().lower()
        if (
            "@" not in sales_email
            or " " in sales_email
            or self._looks_placeholder(sales_email)
        ):
            findings.append("SALES_EMAIL")

        if self.s3_enabled:
            if (
                self.s3_secret_key == "econexo_dev_pw"
                or self._looks_placeholder(self.s3_secret_key)
            ):
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
        if self.pipeline_max_devices_per_run < 1:
            findings.append("PIPELINE_MAX_DEVICES_PER_RUN")

        raw_copernicus_mode = self.copernicus_mode.strip().lower().replace("-", "_")
        if raw_copernicus_mode not in {"process_api", "wms"}:
            findings.append("COPERNICUS_MODE")
        has_copernicus_client_id = bool(self.copernicus_client_id.strip())
        has_copernicus_client_secret = bool(self.copernicus_client_secret.strip())
        if has_copernicus_client_id != has_copernicus_client_secret:
            findings.append("COPERNICUS_CLIENT_ID/COPERNICUS_CLIENT_SECRET")
        if not self.copernicus_token_url.startswith("https://identity.dataspace.copernicus.eu/"):
            findings.append("COPERNICUS_TOKEN_URL")
        if not self.copernicus_process_url.startswith("https://sh.dataspace.copernicus.eu/"):
            findings.append("COPERNICUS_PROCESS_URL")
        if not 1 <= self.copernicus_time_range_days <= 366:
            findings.append("COPERNICUS_TIME_RANGE_DAYS")
        if not 0 <= self.copernicus_max_cloud_coverage <= 100:
            findings.append("COPERNICUS_MAX_CLOUD_COVERAGE")
        if not 64 <= self.copernicus_max_dimension <= 2500:
            findings.append("COPERNICUS_MAX_DIMENSION")

        return findings


@lru_cache
def get_settings() -> Settings:
    return Settings()
