"""Configuracion tipada (Pydantic Settings). Cero secretos hardcodeados."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "econexo"
    postgres_user: str = "econexo"
    postgres_password: str = "econexo_dev_pw"

    jwt_secret: str = "change_me_dev_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883

    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "econexo-reports"
    s3_access_key: str = "econexo"
    s3_secret_key: str = "econexo_dev_pw"

    anomaly_service_url: str = "http://localhost:8100"
    cors_origins: str = "http://localhost:3000"

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
