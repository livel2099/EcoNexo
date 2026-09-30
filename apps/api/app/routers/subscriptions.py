"""Suscripciones comerciales y límites por licencia."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import db
from ..admin_notifications import create_notification
from ..audit import record_audit
from ..config import get_settings
from ..deps import CurrentUser, current_user, require_platform_admin, require_role
from ..schemas import (
    LicenseRequestIn,
    LicenseRequestOut,
    PlatformSubscriptionRowOut,
    PlatformSubscriptionUpdateIn,
    SubscriptionMeOut,
    SubscriptionPlanOut,
    SubscriptionUsageOut,
)
from ..subscriptions import (
    PLAN_DEFINITIONS,
    ensure_subscription,
    expiry_state,
    is_active,
    merged_entitlements,
    seed_plan_catalog,
    subscription_row,
    sync_modules,
    usage_snapshot,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _plan_out(row) -> SubscriptionPlanOut:
    data = dict(row)
    entitlements = data.get("entitlements")
    if isinstance(entitlements, str):
        entitlements = json.loads(entitlements)
    return SubscriptionPlanOut(
        plan_key=data["plan_key"],
        display_name=data["display_name"],
        description=data["description"],
        price_min_usd=float(data["price_min_usd"]) if data["price_min_usd"] is not None else None,
        price_max_usd=float(data["price_max_usd"]) if data["price_max_usd"] is not None else None,
        billing_period=data["billing_period"],
        duration_days=data["duration_days"],
        entitlements=entitlements or {},
    )


@router.get("/plans", response_model=list[SubscriptionPlanOut])
async def plans(user: CurrentUser = Depends(current_user)) -> list[SubscriptionPlanOut]:
    del user
    await seed_plan_catalog()
    rows = await db.pool().fetch(
        """
        SELECT plan_key, display_name, description, price_min_usd, price_max_usd,
               billing_period, duration_days, entitlements
        FROM subscription_plans WHERE active
        ORDER BY CASE plan_key
          WHEN 'sandbox' THEN 0 WHEN 'diagnostic' THEN 1 WHEN 'pilot_8_weeks' THEN 2
          WHEN 'municipal' THEN 3 WHEN 'province_pro' THEN 4 WHEN 'enterprise' THEN 5 ELSE 6 END
        """
    )
    return [_plan_out(row) for row in rows]


@router.get("/me", response_model=SubscriptionMeOut)
async def my_subscription(user: CurrentUser = Depends(current_user)) -> SubscriptionMeOut:
    await ensure_subscription(user.org_id, user.id)
    row = await subscription_row(user.org_id)
    plan = SubscriptionPlanOut(
        plan_key=row["plan_key"],
        display_name=row["display_name"],
        description=row["description"],
        price_min_usd=float(row["price_min_usd"]) if row["price_min_usd"] is not None else None,
        price_max_usd=float(row["price_max_usd"]) if row["price_max_usd"] is not None else None,
        billing_period=row["billing_period"],
        duration_days=row["duration_days"],
        entitlements=merged_entitlements(row),
    )
    return SubscriptionMeOut(
        plan=plan,
        status=row["status"],
        starts_at=row["starts_at"],
        expires_at=row["expires_at"],
        available=is_active(row),
        expiry_label=expiry_state(row),
        entitlements=merged_entitlements(row),
        usage=SubscriptionUsageOut(**await usage_snapshot(user.org_id)),
        platform_admin=user.platform_admin,
        sales_email=get_settings().sales_email or None,
    )


@router.post("/request-change", response_model=LicenseRequestOut, status_code=201)
async def request_change(
    body: LicenseRequestIn,
    user: CurrentUser = Depends(require_role("admin")),
) -> LicenseRequestOut:
    await seed_plan_catalog()
    if body.requested_plan == "sandbox":
        raise HTTPException(422, "Seleccioná un plan comercial distinto del sandbox")
    duplicate = await db.pool().fetchval(
        """
        SELECT EXISTS(
          SELECT 1 FROM license_requests
          WHERE org_id=$1 AND requested_plan=$2 AND status='pending'
        )
        """,
        user.org_id,
        body.requested_plan,
    )
    if duplicate:
        raise HTTPException(409, "Ya existe una solicitud pendiente para ese plan")
    row = await db.pool().fetchrow(
        """
        INSERT INTO license_requests (org_id, requested_by, requested_plan, message)
        VALUES ($1,$2,$3,$4)
        RETURNING id, org_id, requested_by, requested_plan, message, status, created_at, reviewed_at
        """,
        user.org_id,
        user.id,
        body.requested_plan,
        body.message.strip() or None,
    )
    org_name = await db.pool().fetchval("SELECT name FROM organizations WHERE id=$1", user.org_id)
    await create_notification(
        org_id=user.org_id,
        kind="license_request",
        visibility="platform_admins",
        severity="warning",
        title="Nueva solicitud de licencia",
        message=f"{org_name} solicitó el plan {PLAN_DEFINITIONS[body.requested_plan]['name']}.",
        actor_user_id=user.id,
        actor_email=user.email,
        metadata={"requested_plan": body.requested_plan, "request_id": str(row["id"])},
    )
    await create_notification(
        org_id=user.org_id,
        kind="license_request_created",
        visibility="org_admins",
        severity="success",
        title="Solicitud enviada",
        message=f"La solicitud para {PLAN_DEFINITIONS[body.requested_plan]['name']} quedó registrada.",
        actor_user_id=user.id,
        actor_email=user.email,
        metadata={"requested_plan": body.requested_plan, "request_id": str(row["id"])},
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="request",
        resource="subscription",
        resource_id=row["id"],
        metadata={"requested_plan": body.requested_plan},
    )
    return LicenseRequestOut(**dict(row), org_name=org_name, requester_email=user.email)


@router.get("/requests", response_model=list[LicenseRequestOut])
async def list_my_requests(
    user: CurrentUser = Depends(require_role("admin")),
) -> list[LicenseRequestOut]:
    rows = await db.pool().fetch(
        """
        SELECT lr.id, lr.org_id, o.name AS org_name, lr.requested_by,
               u.name AS requester_name, u.email AS requester_email,
               lr.requested_plan, lr.message, lr.status, lr.created_at, lr.reviewed_at
        FROM license_requests lr
        JOIN organizations o ON o.id=lr.org_id
        LEFT JOIN users u ON u.id=lr.requested_by
        WHERE lr.org_id=$1
        ORDER BY lr.created_at DESC
        """,
        user.org_id,
    )
    return [LicenseRequestOut(**dict(row)) for row in rows]


@router.get("/platform/requests", response_model=list[LicenseRequestOut])
async def platform_requests(
    status_filter: str | None = Query(default="pending", alias="status"),
    user: CurrentUser = Depends(require_platform_admin),
) -> list[LicenseRequestOut]:
    del user
    rows = await db.pool().fetch(
        """
        SELECT lr.id, lr.org_id, o.name AS org_name, lr.requested_by,
               u.name AS requester_name, u.email AS requester_email,
               lr.requested_plan, lr.message, lr.status, lr.created_at, lr.reviewed_at
        FROM license_requests lr
        JOIN organizations o ON o.id=lr.org_id
        LEFT JOIN users u ON u.id=lr.requested_by
        WHERE ($1::text IS NULL OR lr.status=$1)
        ORDER BY lr.created_at DESC LIMIT 200
        """,
        status_filter,
    )
    return [LicenseRequestOut(**dict(row)) for row in rows]


@router.get("/platform/organizations", response_model=list[PlatformSubscriptionRowOut])
async def platform_organizations(
    user: CurrentUser = Depends(require_platform_admin),
) -> list[PlatformSubscriptionRowOut]:
    del user
    rows = await db.pool().fetch(
        """
        SELECT o.id AS org_id, o.name AS org_name, o.municipality,
               COALESCE(os.plan_key,'sandbox') AS plan_key,
               COALESCE(sp.display_name,'Sin licencia asignada') AS display_name,
               COALESCE(os.status,'pending') AS status,
               COALESCE(os.starts_at,o.created_at) AS starts_at,
               os.expires_at, COALESCE(os.updated_at,o.updated_at) AS updated_at
        FROM organizations o
        LEFT JOIN organization_subscriptions os ON os.org_id=o.id
        LEFT JOIN subscription_plans sp ON sp.plan_key=os.plan_key
        ORDER BY os.updated_at DESC, o.name
        """
    )
    return [PlatformSubscriptionRowOut(**dict(row)) for row in rows]


@router.post("/platform/{org_id}/cancel")
async def cancel_platform_subscription(
    org_id: UUID,
    user: CurrentUser = Depends(require_platform_admin),
) -> dict[str, str]:
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            current = await conn.fetchrow(
                "SELECT plan_key, status FROM organization_subscriptions WHERE org_id=$1 FOR UPDATE", org_id,
            )
            if current is None:
                raise HTTPException(404, "La organización no tiene una licencia asignada")
            if current["status"] == "cancelled":
                return {"status": "cancelled"}
            await conn.execute(
                """UPDATE organization_subscriptions SET status='cancelled', auto_renew=false,
                          updated_at=now(), activated_by=$2, activation_source='platform_admin'
                   WHERE org_id=$1""", org_id, user.id,
            )
            await conn.execute(
                "UPDATE organization_modules SET status='suspended', updated_at=now() WHERE org_id=$1", org_id,
            )
            await conn.execute(
                """INSERT INTO subscription_events
                     (org_id,previous_plan,next_plan,previous_status,next_status,actor_user_id,metadata)
                   VALUES ($1,$2,$2,$3,'cancelled',$4,'{}'::jsonb)""",
                org_id, current["plan_key"], current["status"], user.id,
            )
            await conn.execute(
                """INSERT INTO audit_events (org_id,user_id,action,resource,resource_id,metadata)
                   VALUES ($1,$2,'cancel','subscription',$1,'{}'::jsonb)""", org_id, user.id,
            )
    return {"status": "cancelled"}


@router.patch("/platform/{org_id}", response_model=SubscriptionMeOut)
async def update_platform_subscription(
    org_id: UUID,
    body: PlatformSubscriptionUpdateIn,
    user: CurrentUser = Depends(require_platform_admin),
) -> SubscriptionMeOut:
    if not await db.pool().fetchval("SELECT EXISTS(SELECT 1 FROM organizations WHERE id=$1)", org_id):
        raise HTTPException(404, "Organización no encontrada")
    await seed_plan_catalog()
    current = await subscription_row(org_id)
    if current is None:
        raise HTTPException(404, "Organización no encontrada")
    plan = PLAN_DEFINITIONS[body.plan_key]
    if body.active_modules is not None:
        body.custom_entitlements["included_modules"] = list(dict.fromkeys(["core", *body.active_modules]))
    expires_at = body.expires_at
    if expires_at is None and plan["duration_days"] is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=int(plan["duration_days"]))
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            current = await conn.fetchrow(
                "SELECT * FROM organization_subscriptions WHERE org_id=$1 FOR UPDATE", org_id,
            )
            await conn.execute(
                """
                INSERT INTO subscription_events
                  (org_id, previous_plan, next_plan, previous_status, next_status,
                   actor_user_id, metadata)
                VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb)
                """,
                org_id,
                current["plan_key"],
                body.plan_key,
                current["status"],
                body.status,
                user.id,
                json.dumps({"notes": body.notes, "custom_entitlements": body.custom_entitlements}, ensure_ascii=False),
            )
            await conn.execute(
                """
                UPDATE organization_subscriptions SET
                  plan_key=$2, status=$3, starts_at=CASE WHEN plan_key<>$2 THEN now() ELSE starts_at END,
                  expires_at=$4, auto_renew=$5, custom_entitlements=$6::jsonb,
                  notes=NULLIF($7,''), activated_by=$8, activation_source='platform_admin'
                WHERE org_id=$1
                """,
                org_id,
                body.plan_key,
                body.status,
                expires_at,
                body.auto_renew,
                json.dumps(body.custom_entitlements, ensure_ascii=False),
                body.notes.strip(),
                user.id,
            )
            updated = await conn.fetchrow(
                """SELECT os.*, sp.entitlements AS plan_entitlements, now() AS database_now
                   FROM organization_subscriptions os JOIN subscription_plans sp USING (plan_key)
                   WHERE os.org_id=$1""", org_id,
            )
            await sync_modules(org_id, user.id, conn=conn, subscription=updated)
            if body.active_modules is not None:
                requested = set(body.active_modules)
                for module_key in ("core", "fire_smoke", "forestry_pests", "agro", "ecocampo"):
                    module_status = "active" if is_active(updated) and (module_key in requested or module_key == "core") else "suspended"
                    await conn.execute(
                        """
                        UPDATE organization_modules
                        SET status=$3,
                            -- El cast es obligatorio: dentro de un CASE, Postgres
                            -- resuelve el tipo por las ramas y no por la columna
                            -- destino, asi que un parametro nulo se toma como text y
                            -- la sentencia falla. Pasa con todo plan sin vencimiento
                            -- (municipal, provincia, enterprise, agro_productor).
                            expires_at=CASE WHEN $3='active' THEN $4::timestamptz ELSE NULL END,
                            updated_at=now()
                        WHERE org_id=$1 AND module_key=$2
                        """,
                        org_id,
                        module_key,
                        module_status,
                        expires_at,
                    )
            if body.request_id is not None:
                await conn.execute(
                    """
                    UPDATE license_requests SET status='approved', reviewed_by=$2,
                           reviewed_at=now() WHERE id=$1 AND org_id=$3
                    """,
                    body.request_id,
                    user.id,
                    org_id,
                )
    await create_notification(
        org_id=org_id,
        kind="subscription_updated",
        visibility="org_admins",
        severity="success" if body.status in {"active", "trial"} else "warning",
        title="Licencia actualizada",
        message=f"EcoNexo actualizó la organización al plan {plan['name']} con estado {body.status}.",
        actor_user_id=user.id,
        actor_email=user.email,
        metadata={"plan_key": body.plan_key, "status": body.status},
    )
    await record_audit(
        org_id=org_id,
        user_id=user.id,
        action="update",
        resource="subscription",
        resource_id=org_id,
        metadata={"plan_key": body.plan_key, "status": body.status, "platform_admin": user.email},
    )
    row = await subscription_row(org_id)
    return SubscriptionMeOut(
        plan=SubscriptionPlanOut(
            plan_key=row["plan_key"], display_name=row["display_name"],
            description=row["description"],
            price_min_usd=float(row["price_min_usd"]) if row["price_min_usd"] is not None else None,
            price_max_usd=float(row["price_max_usd"]) if row["price_max_usd"] is not None else None,
            billing_period=row["billing_period"], duration_days=row["duration_days"],
            entitlements=merged_entitlements(row),
        ),
        status=row["status"], starts_at=row["starts_at"], expires_at=row["expires_at"],
        available=is_active(row), expiry_label=expiry_state(row),
        entitlements=merged_entitlements(row), usage=SubscriptionUsageOut(**await usage_snapshot(org_id)),
        platform_admin=True, sales_email=get_settings().sales_email or None,
    )
