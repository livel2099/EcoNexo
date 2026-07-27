from __future__ import annotations

from app.config import Settings
from app.schemas import AlertShareIn, ModuleEntitlementOut


def test_google_audiences_accepts_web_android_and_ios() -> None:
    settings = Settings(
        google_client_id="web.apps.googleusercontent.com",
        google_client_ids="android.apps.googleusercontent.com, ios.apps.googleusercontent.com,web.apps.googleusercontent.com",
    )
    assert settings.google_audiences == [
        "android.apps.googleusercontent.com",
        "ios.apps.googleusercontent.com",
        "web.apps.googleusercontent.com",
    ]


def test_alert_share_requires_a_known_module_and_channel() -> None:
    body = AlertShareIn(
        channel="whatsapp",
        audience="publico",
        title="Alerta preventiva de humo",
        message="Se detectó una señal que requiere verificación humana antes de comunicar.",
        module_key="fire_smoke",
        metadata={"level": "R3"},
    )
    assert body.module_key == "fire_smoke"
    assert body.channel == "whatsapp"


def test_module_entitlement_serializes_trial_availability() -> None:
    from datetime import datetime, timezone

    body = ModuleEntitlementOut(
        module_key="fire_smoke",
        status="trial",
        plan_name="Focos de incendio forestal y humo",
        starts_at=datetime.now(timezone.utc),
        expires_at=None,
        config={"human_approval_required": True},
        available=True,
    )
    assert body.available is True
    assert body.config["human_approval_required"] is True


def test_forestry_pest_module_is_supported() -> None:
    from datetime import datetime, timezone

    body = ModuleEntitlementOut(
        module_key="forestry_pests",
        status="trial",
        plan_name="Vigilancia de plagas forestales",
        starts_at=datetime.now(timezone.utc),
        expires_at=None,
        config={"focus_area": "San Antonio - General Manuel Belgrano"},
        available=True,
    )
    assert body.module_key == "forestry_pests"
