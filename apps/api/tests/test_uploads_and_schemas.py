from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas import ImpactReportCreateIn
from app.storage import validate_image


@pytest.mark.parametrize(
    "media_type,data,extension",
    [
        ("image/jpeg", b"\xff\xd8\xffrest", ".jpg"),
        ("image/png", b"\x89PNG\r\n\x1a\nrest", ".png"),
        ("image/webp", b"RIFF0000WEBPrest", ".webp"),
    ],
)
def test_validate_image_checks_magic_bytes(media_type: str, data: bytes, extension: str) -> None:
    assert validate_image(data, media_type) == extension


def test_validate_image_rejects_mime_spoofing() -> None:
    with pytest.raises(ValueError):
        validate_image(b"not-a-real-image", "image/jpeg")


def test_impact_report_rejects_inverted_period() -> None:
    with pytest.raises(ValidationError):
        ImpactReportCreateIn(
            title="Informe institucional",
            recipient_type="municipio",
            recipient_name="Municipio de prueba",
            period_start="2026-07-23",
            period_end="2026-07-01",
        )


def test_production_defaults_are_rejected() -> None:
    settings = Settings(environment="production")
    findings = settings.insecure_production_values()
    assert "JWT_SECRET" in findings
    assert "INTERNAL_SERVICE_TOKEN" in findings
    assert "PUBLIC_APP_URL" in findings
    assert "S3_PUBLIC_ENDPOINT" in findings
    assert "S3_SERVER_SIDE_ENCRYPTION" in findings
    assert "CORS_ORIGINS" in findings


def test_email_registration_requires_letter_and_number() -> None:
    from app.schemas import EmailRegisterIn

    with pytest.raises(ValidationError):
        EmailRegisterIn(
            organization_name="EcoNexo Misiones",
            vertical="forestal",
            name="Miguel Ibachuta",
            email="miguel@example.com",
            password="sololetras",
            terms_accepted=True,
        )


def test_email_registration_accepts_local_onboarding() -> None:
    from app.schemas import EmailRegisterIn

    body = EmailRegisterIn(
        organization_name="EcoNexo Misiones",
        vertical="forestal",
        name="Miguel Ibachuta",
        email="miguel@example.com",
        password="EcoNexo2026",
        terms_accepted=True,
    )
    assert body.organization_name == "EcoNexo Misiones"
    assert str(body.email) == "miguel@example.com"


def test_local_cors_accepts_localhost_and_loopback() -> None:
    settings = Settings(cors_origins="http://localhost:3000")
    assert "http://localhost:3000" in settings.cors_list
    assert "http://127.0.0.1:3000" in settings.cors_list


def test_secure_production_configuration_passes_launch_guard() -> None:
    settings = Settings(
        environment="production",
        postgres_password="a-secure-postgres-password",
        jwt_secret="a" * 64,
        internal_service_token="b" * 64,
        s3_secret_key="c" * 64,
        s3_endpoint="https://s3.example.com",
        s3_public_endpoint="https://s3.example.com",
        s3_server_side_encryption="AES256",
        public_app_url="https://app.econexo.com.ar",
        cors_origins="https://app.econexo.com.ar",
        forwarded_allow_ips="10.0.0.0/8",
        platform_admin_emails="admin@econexo.com.ar",
        sales_email="comercial@econexo.com.ar",
    )
    assert settings.insecure_production_values() == []


def test_copernicus_source_settings_accept_official_wms() -> None:
    from app.schemas import EnvironmentalSourceSettingsIn

    body = EnvironmentalSourceSettingsIn(
        default_latitude=-26.01709,
        default_longitude=-53.78987,
        copernicus_enabled=True,
        copernicus_wms_url="https://sh.dataspace.copernicus.eu/ogc/wms/123e4567-e89b-12d3-a456-426614174000",
    )
    assert body.copernicus_enabled is True
    assert body.copernicus_wms_url and body.copernicus_wms_url.startswith("https://sh.dataspace.copernicus.eu/ogc/wms/")


def test_copernicus_source_settings_reject_arbitrary_host() -> None:
    from app.schemas import EnvironmentalSourceSettingsIn

    with pytest.raises(ValidationError):
        EnvironmentalSourceSettingsIn(
            default_latitude=-26.01709,
            default_longitude=-53.78987,
            copernicus_enabled=True,
            copernicus_wms_url="https://example.com/wms/demo",
        )


def test_render_core_configuration_can_disable_optional_adapters(monkeypatch) -> None:
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-test")
    settings = Settings(
        environment="production",
        database_url="postgresql://user:password@internal/econexo",
        jwt_secret="a" * 64,
        internal_service_token="b" * 64,
        public_app_url="https://econexo.example.com",
        cors_origins="https://econexo.example.com",
        forwarded_allow_ips="*",
        mqtt_enabled=False,
        anomaly_enabled=False,
        s3_enabled=False,
        platform_admin_emails="admin@econexo.com.ar",
        sales_email="comercial@econexo.com.ar",
    )
    assert settings.insecure_production_values() == []
    assert settings.dsn.startswith("postgresql://")


def test_render_placeholders_are_rejected(monkeypatch) -> None:
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-test")
    settings = Settings(
        environment="production",
        database_url="postgresql://USUARIO:CONTRASENA@HOST-INTERNO/econexo",
        jwt_secret="REEMPLAZAR_CON_64_CARACTERES_ALEATORIOS",
        internal_service_token="REEMPLAZAR_CON_OTRO_SECRET_MUY_LARGO",
        public_app_url="https://econexo.example.com",
        cors_origins="https://econexo.example.com",
        forwarded_allow_ips="*",
        s3_enabled=False,
    )
    findings = settings.insecure_production_values()
    assert "DATABASE_URL" in findings
    assert "JWT_SECRET" in findings
    assert "INTERNAL_SERVICE_TOKEN" in findings
