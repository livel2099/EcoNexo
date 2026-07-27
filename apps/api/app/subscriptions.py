"""Planes comerciales, límites de licencia y consumo de recursos.

Los precios y prestaciones comerciales provienen del dossier de negocio EcoNexo.
Los límites numéricos son una parametrización operativa inicial: se almacenan en
PostgreSQL y pueden modificarse sin cambiar el código.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from . import db

PLAN_DEFINITIONS: dict[str, dict[str, Any]] = {
    "sandbox": {
        "name": "Sandbox calificado",
        "description": "Entorno limitado para evaluación comercial; no reemplaza un piloto pago.",
        "price_min_usd": 0,
        "price_max_usd": 0,
        "billing_period": "trial",
        "duration_days": 14,
        "entitlements": {
            "max_users": 2,
            "max_devices": 2,
            "max_zones": 1,
            "max_rules": 2,
            "max_reports_per_month": 1,
            "max_critical_layers": 1,
            "municipality_limit": 1,
            "report_frequency": "muestra",
            "support_level": "autoservicio",
            "api_access": False,
            "audit_export": False,
            "custom_models": False,
            "sla": False,
            "community_reports": True,
            "operational_alerts": False,
            "included_modules": ["core"],
        },
    },
    "diagnostic": {
        "name": "Diagnóstico territorial",
        "description": "Mapa base, lectura de riesgo, propuesta de piloto y caso de uso priorizado.",
        "price_min_usd": 2000,
        "price_max_usd": 4000,
        "billing_period": "one_time",
        "duration_days": 30,
        "entitlements": {
            "max_users": 3,
            "max_devices": 0,
            "max_zones": 1,
            "max_rules": 0,
            "max_reports_per_month": 1,
            "max_critical_layers": 1,
            "municipality_limit": 1,
            "report_frequency": "informe diagnóstico",
            "support_level": "acompañamiento inicial",
            "api_access": False,
            "audit_export": False,
            "custom_models": False,
            "sla": False,
            "community_reports": False,
            "operational_alerts": False,
            "included_modules": ["core"],
        },
    },
    "pilot_8_weeks": {
        "name": "Piloto 8 semanas",
        "description": "Dashboard, tres capas críticas, validación, reportes y capacitación.",
        "price_min_usd": 18000,
        "price_max_usd": 35000,
        "billing_period": "one_time",
        "duration_days": 56,
        "entitlements": {
            "max_users": 10,
            "max_devices": 25,
            "max_zones": 2,
            "max_rules": 12,
            "max_reports_per_month": 4,
            "max_critical_layers": 3,
            "municipality_limit": 2,
            "report_frequency": "semanal o quincenal",
            "support_level": "acompañamiento de piloto",
            "api_access": False,
            "audit_export": True,
            "custom_models": False,
            "sla": False,
            "community_reports": True,
            "operational_alerts": True,
            "included_modules": ["core", "fire_smoke", "forestry_pests"],
        },
    },
    "municipal": {
        "name": "SaaS Municipal",
        "description": "Una municipalidad, alertas base, reportes mensuales y soporte limitado.",
        "price_min_usd": 800,
        "price_max_usd": 1500,
        "billing_period": "monthly",
        "duration_days": None,
        "entitlements": {
            "max_users": 10,
            "max_devices": 50,
            "max_zones": 5,
            "max_rules": 20,
            "max_reports_per_month": 4,
            "max_critical_layers": 3,
            "municipality_limit": 1,
            "report_frequency": "mensual",
            "support_level": "limitado",
            "api_access": False,
            "audit_export": False,
            "custom_models": False,
            "sla": False,
            "community_reports": True,
            "operational_alerts": True,
            "included_modules": ["core"],
        },
    },
    "province_pro": {
        "name": "SaaS Provincia / Pro",
        "description": "Múltiples zonas, reportes quincenales, usuarios internos y playbook operativo.",
        "price_min_usd": 3500,
        "price_max_usd": 8000,
        "billing_period": "monthly",
        "duration_days": None,
        "entitlements": {
            "max_users": 50,
            "max_devices": 500,
            "max_zones": 30,
            "max_rules": 100,
            "max_reports_per_month": 12,
            "max_critical_layers": 12,
            "municipality_limit": 79,
            "report_frequency": "quincenal",
            "support_level": "prioritario",
            "api_access": False,
            "audit_export": True,
            "custom_models": False,
            "sla": False,
            "community_reports": True,
            "operational_alerts": True,
            "included_modules": ["core"],
        },
    },
    "enterprise": {
        "name": "Enterprise minero / energético",
        "description": "SLA, integraciones, API, auditoría, modelos y evidencia personalizada.",
        "price_min_usd": 12000,
        "price_max_usd": None,
        "billing_period": "monthly",
        "duration_days": None,
        "entitlements": {
            "max_users": 250,
            "max_devices": 5000,
            "max_zones": 250,
            "max_rules": 1000,
            "max_reports_per_month": 100,
            "max_critical_layers": 50,
            "municipality_limit": 79,
            "report_frequency": "personalizada",
            "support_level": "dedicado",
            "api_access": True,
            "audit_export": True,
            "custom_models": True,
            "sla": True,
            "community_reports": True,
            "operational_alerts": True,
            "included_modules": ["core", "fire_smoke", "forestry_pests"],
        },
    },
    "academy": {
        "name": "Academia EcoNexo",
        "description": "Capacitación operativa, manuales, certificación interna y simulacros.",
        "price_min_usd": 2000,
        "price_max_usd": 6000,
        "billing_period": "cohort",
        "duration_days": 45,
        "entitlements": {
            "max_users": 40,
            "max_devices": 0,
            "max_zones": 1,
            "max_rules": 0,
            "max_reports_per_month": 2,
            "max_critical_layers": 1,
            "municipality_limit": 1,
            "report_frequency": "simulación",
            "support_level": "cohorte",
            "api_access": False,
            "audit_export": False,
            "custom_models": False,
            "sla": False,
            "community_reports": True,
            "operational_alerts": False,
            "included_modules": ["core"],
        },
    },
}

RESOURCE_TABLES = {
    "max_users": ("users", "is_active"),
    "max_devices": ("devices", None),
    "max_zones": ("risk_zones", None),
    "max_rules": ("rules", None),
}


def _json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        return json.loads(value)
    return value


def merged_entitlements(row: Any) -> dict[str, Any]:
    base = _json(row["plan_entitlements"], {})
    custom = _json(row["custom_entitlements"], {})
    return {**base, **custom}


async def seed_plan_catalog(conn: Any | None = None) -> None:
    executor = conn or db.pool()
    for key, plan in PLAN_DEFINITIONS.items():
        await executor.execute(
            """
            INSERT INTO subscription_plans
              (plan_key, display_name, description, price_min_usd, price_max_usd,
               billing_period, duration_days, entitlements, active)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,true)
            ON CONFLICT (plan_key) DO UPDATE SET
              display_name=EXCLUDED.display_name,
              description=EXCLUDED.description,
              price_min_usd=EXCLUDED.price_min_usd,
              price_max_usd=EXCLUDED.price_max_usd,
              billing_period=EXCLUDED.billing_period,
              duration_days=EXCLUDED.duration_days,
              entitlements=EXCLUDED.entitlements,
              active=true,
              updated_at=now()
            """,
            key,
            plan["name"],
            plan["description"],
            plan["price_min_usd"],
            plan["price_max_usd"],
            plan["billing_period"],
            plan["duration_days"],
            json.dumps(plan["entitlements"], ensure_ascii=False),
        )


async def ensure_subscription(
    org_id: UUID,
    user_id: UUID | None = None,
    *,
    plan_key: str = "sandbox",
    conn: Any | None = None,
) -> None:
    executor = conn or db.pool()
    await seed_plan_catalog(executor)
    plan = PLAN_DEFINITIONS[plan_key]
    duration = plan["duration_days"]
    await executor.execute(
        """
        INSERT INTO organization_subscriptions
          (org_id, plan_key, status, starts_at, expires_at, custom_entitlements,
           activated_by, activation_source)
        VALUES (
          $1,$2,'trial',now(),
          CASE WHEN $3::int IS NULL THEN NULL ELSE now() + make_interval(days => $3::int) END,
          '{}'::jsonb,$4,'automatic_registration'
        )
        ON CONFLICT (org_id) DO NOTHING
        """,
        org_id,
        plan_key,
        duration,
        user_id,
    )


async def subscription_row(org_id: UUID) -> Any:
    await ensure_subscription(org_id)
    return await db.pool().fetchrow(
        """
        SELECT os.*, sp.display_name, sp.description, sp.price_min_usd,
               sp.price_max_usd, sp.billing_period, sp.duration_days,
               sp.entitlements AS plan_entitlements, now() AS database_now
        FROM organization_subscriptions os
        JOIN subscription_plans sp ON sp.plan_key=os.plan_key
        WHERE os.org_id=$1
        """,
        org_id,
    )


def is_active(row: Any) -> bool:
    if row["status"] not in {"trial", "active"}:
        return False
    return row["expires_at"] is None or row["expires_at"] > row["database_now"]


async def require_active_subscription(org_id: UUID) -> Any:
    row = await subscription_row(org_id)
    if row is None or not is_active(row):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "La licencia de la organización está vencida, suspendida o pendiente de activación.",
        )
    return row


async def usage_snapshot(org_id: UUID) -> dict[str, int]:
    row = await db.pool().fetchrow(
        """
        SELECT
          (SELECT count(*) FROM users WHERE org_id=$1 AND is_active) AS users,
          (SELECT count(*) FROM devices WHERE org_id=$1) AS devices,
          (SELECT count(*) FROM risk_zones WHERE org_id=$1) AS zones,
          (SELECT count(*) FROM rules WHERE org_id=$1) AS rules,
          (SELECT count(*) FROM impact_reports WHERE org_id=$1
             AND created_at >= date_trunc('month', now())) AS reports_this_month
        """,
        org_id,
    )
    return {key: int(value or 0) for key, value in dict(row).items()}


async def enforce_resource_limit(org_id: UUID, limit_key: str) -> None:
    subscription = await require_active_subscription(org_id)
    entitlements = merged_entitlements(subscription)
    limit = entitlements.get(limit_key)
    if limit is None:
        return
    table, condition = RESOURCE_TABLES[limit_key]
    query = f"SELECT count(*) FROM {table} WHERE org_id=$1"
    if condition:
        query += f" AND {condition}"
    current = int(await db.pool().fetchval(query, org_id) or 0)
    if current >= int(limit):
        label = {
            "max_users": "usuarios activos",
            "max_devices": "dispositivos",
            "max_zones": "geocercas",
            "max_rules": "reglas",
        }.get(limit_key, "recursos")
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Tu licencia permite hasta {limit} {label}. Solicitá una ampliación desde Admin Core > Suscripción.",
        )


async def enforce_monthly_report_limit(org_id: UUID) -> None:
    subscription = await require_active_subscription(org_id)
    entitlements = merged_entitlements(subscription)
    limit = entitlements.get("max_reports_per_month")
    if limit is None:
        return
    current = int(
        await db.pool().fetchval(
            """
            SELECT count(*) FROM impact_reports
            WHERE org_id=$1 AND created_at >= date_trunc('month', now())
            """,
            org_id,
        )
        or 0
    )
    if current >= int(limit):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"La licencia alcanzó el límite de {limit} informes del mes.",
        )


async def module_included_by_plan(org_id: UUID, module_key: str) -> bool:
    row = await require_active_subscription(org_id)
    included = merged_entitlements(row).get("included_modules", ["core"])
    return module_key in included


async def sync_modules(org_id: UUID, user_id: UUID | None = None) -> None:
    row = await subscription_row(org_id)
    included = set(merged_entitlements(row).get("included_modules", ["core"]))
    expiry = row["expires_at"]
    for module_key, display_name in {
        "core": "Plataforma EcoNexo",
        "fire_smoke": "Focos de incendio forestal y humo",
        "forestry_pests": "Vigilancia de plagas forestales",
    }.items():
        default_status = "active" if module_key in included else "suspended"
        await db.pool().execute(
            """
            INSERT INTO organization_modules
              (org_id, module_key, status, plan_name, starts_at, expires_at, config, created_by)
            VALUES ($1,$2,$3,$4,now(),$5,'{}'::jsonb,$6)
            ON CONFLICT (org_id,module_key) DO UPDATE SET
              status=CASE
                WHEN organization_modules.status='active' AND $2 <> 'core' THEN organization_modules.status
                ELSE EXCLUDED.status
              END,
              plan_name=EXCLUDED.plan_name,
              expires_at=CASE
                WHEN organization_modules.status='active' AND $2 <> 'core' THEN organization_modules.expires_at
                ELSE EXCLUDED.expires_at
              END,
              updated_at=now()
            """,
            org_id,
            module_key,
            default_status,
            display_name,
            expiry if module_key in included else None,
            user_id,
        )


def expiry_state(row: Any) -> str:
    if row["expires_at"] is None:
        return "sin vencimiento"
    remaining = row["expires_at"] - datetime.now(timezone.utc)
    if remaining.total_seconds() <= 0:
        return "vencida"
    return f"{max(1, remaining.days)} días restantes"
