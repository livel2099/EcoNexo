from __future__ import annotations

from app.config import Settings
from app.schemas import LicenseRequestIn, PlatformSubscriptionUpdateIn
import ast
from pathlib import Path


def _plan_definitions() -> dict:
    source = Path(__file__).resolve().parents[1] / "app" / "subscriptions.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "PLAN_DEFINITIONS":
            return ast.literal_eval(node.value)
    raise AssertionError("PLAN_DEFINITIONS no encontrado")


PLAN_DEFINITIONS = _plan_definitions()


def test_business_plan_prices_are_encoded() -> None:
    assert PLAN_DEFINITIONS["diagnostic"]["price_min_usd"] == 2000
    assert PLAN_DEFINITIONS["diagnostic"]["price_max_usd"] == 4000
    assert PLAN_DEFINITIONS["pilot_8_weeks"]["price_min_usd"] == 18000
    assert PLAN_DEFINITIONS["pilot_8_weeks"]["price_max_usd"] == 35000
    assert PLAN_DEFINITIONS["municipal"]["price_min_usd"] == 800
    assert PLAN_DEFINITIONS["municipal"]["price_max_usd"] == 1500
    assert PLAN_DEFINITIONS["province_pro"]["price_min_usd"] == 3500
    assert PLAN_DEFINITIONS["province_pro"]["price_max_usd"] == 8000
    assert PLAN_DEFINITIONS["enterprise"]["price_min_usd"] == 12000


def test_sandbox_is_limited_and_temporary() -> None:
    sandbox = PLAN_DEFINITIONS["sandbox"]
    assert sandbox["duration_days"] == 14
    assert sandbox["entitlements"]["max_users"] == 2
    assert sandbox["entitlements"]["operational_alerts"] is False


def test_license_request_rejects_unknown_plan_at_schema_level() -> None:
    body = LicenseRequestIn(requested_plan="municipal", message="Un municipio y alertas base")
    assert body.requested_plan == "municipal"


def test_platform_admin_emails_are_normalized() -> None:
    settings = Settings(platform_admin_emails=" ADMIN@ECONEXO.AR,ventas@econexo.ar,admin@econexo.ar ")
    assert settings.platform_admin_list == ["admin@econexo.ar", "ventas@econexo.ar"]


def test_platform_subscription_update_accepts_contract_overrides() -> None:
    body = PlatformSubscriptionUpdateIn(
        plan_key="province_pro",
        status="active",
        custom_entitlements={"max_users": 75},
        active_modules=["core", "fire_smoke"],
        notes="Contrato provincial con ampliación de usuarios",
    )
    assert body.custom_entitlements["max_users"] == 75
    assert "fire_smoke" in (body.active_modules or [])
