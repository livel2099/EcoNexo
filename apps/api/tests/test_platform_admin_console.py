from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas import PasswordChangeIn


def test_platform_admin_bootstrap_configuration_is_secure() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql://user:password@pooler.supabase.com:5432/postgres?sslmode=require",
        jwt_secret="a" * 64,
        internal_service_token="b" * 64,
        forwarded_allow_ips="127.0.0.1",
        public_app_url="https://econexo-web.onrender.com",
        cors_origins="https://econexo-web.onrender.com",
        platform_admin_emails="econexoargentina@gmail.com",
        platform_admin_bootstrap_enabled=True,
        platform_admin_initial_password="TemporalEcoNexo2026-9",
        sales_email="econexoargentina@gmail.com",
        mqtt_enabled=False,
        s3_enabled=False,
        anomaly_enabled=False,
    )
    assert settings.insecure_production_values() == []


def test_password_change_rejects_same_password() -> None:
    with pytest.raises(ValidationError):
        PasswordChangeIn(
            current_password="TemporalEcoNexo2026-9",
            new_password="TemporalEcoNexo2026-9",
        )
