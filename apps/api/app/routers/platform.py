"""Consola oculta del administrador general de la plataforma EcoNexo."""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import db
from ..audit import record_audit
from ..config import get_settings
from ..deps import CurrentUser, require_platform_admin
from ..schemas import (
    PlatformAuditOut,
    PlatformOrganizationOut,
    PlatformOrganizationUpdateIn,
    PlatformPasswordResetIn,
    PlatformSummaryOut,
    PlatformUserCreateIn,
    PlatformUserOut,
    PlatformUserUpdateIn,
)
from ..security import hash_secret
from ..subscriptions import enforce_resource_limit

router = APIRouter(prefix="/platform", tags=["platform-admin"], include_in_schema=False)


async def _user_out(target_id: UUID) -> PlatformUserOut:
    row = await db.pool().fetchrow(
        """
        SELECT u.id, u.org_id, o.name AS org_name, u.name, u.email, u.role,
               u.is_active, o.is_active AS organization_active, u.auth_provider,
               u.email_verified, u.must_change_password, u.last_login_at,
               u.created_at, u.updated_at
        FROM users u JOIN organizations o ON o.id=u.org_id
        WHERE u.id=$1
        """,
        target_id,
    )
    if row is None:
        raise HTTPException(404, "Usuario no encontrado")
    return PlatformUserOut(**dict(row))


async def _organization_out(org_id: UUID) -> PlatformOrganizationOut:
    row = await db.pool().fetchrow(
        """
        SELECT o.id, o.name, o.slug, o.vertical::text AS vertical, o.province,
               o.municipality, o.is_active,
               count(u.id)::int AS users_total,
               (count(u.id) FILTER (WHERE u.is_active))::int AS users_active,
               os.plan_key, sp.display_name AS plan_name,
               os.status AS subscription_status,
               o.created_at, o.updated_at
        FROM organizations o
        LEFT JOIN users u ON u.org_id=o.id
        LEFT JOIN organization_subscriptions os ON os.org_id=o.id
        LEFT JOIN subscription_plans sp ON sp.plan_key=os.plan_key
        WHERE o.id=$1
        GROUP BY o.id, os.plan_key, sp.display_name, os.status
        """,
        org_id,
    )
    if row is None:
        raise HTTPException(404, "Organización no encontrada")
    return PlatformOrganizationOut(**dict(row))


@router.get("/summary", response_model=PlatformSummaryOut)
async def summary(
    user: CurrentUser = Depends(require_platform_admin),
) -> PlatformSummaryOut:
    del user
    row = await db.pool().fetchrow(
        """
        SELECT
          (SELECT count(*) FROM organizations) AS organizations_total,
          (SELECT count(*) FROM organizations WHERE is_active) AS organizations_active,
          (SELECT count(*) FROM users) AS users_total,
          (SELECT count(*) FROM users WHERE is_active) AS users_active,
          (SELECT count(*) FROM users
             WHERE is_active AND role='admin'
               AND lower(email)=ANY($1::text[])) AS platform_admins,
          (SELECT count(*) FROM license_requests WHERE status='pending') AS pending_license_requests,
          (SELECT count(*) FROM users WHERE last_login_at > now() - interval '24 hours') AS logins_24h
        """,
        get_settings().platform_admin_list,
    )
    return PlatformSummaryOut(**dict(row))


@router.post("/users", response_model=PlatformUserOut, status_code=201)
async def create_user(
    body: PlatformUserCreateIn,
    user: CurrentUser = Depends(require_platform_admin),
) -> PlatformUserOut:
    organization = await db.pool().fetchrow(
        "SELECT id, is_active FROM organizations WHERE id=$1",
        body.org_id,
    )
    if organization is None:
        raise HTTPException(404, "Organización no encontrada")
    if not organization["is_active"]:
        raise HTTPException(409, "La organización está suspendida")
    if await db.pool().fetchval(
        "SELECT EXISTS(SELECT 1 FROM users WHERE lower(email)=lower($1))",
        str(body.email),
    ):
        raise HTTPException(409, "El correo ya está registrado")
    await enforce_resource_limit(body.org_id, "max_users")
    row = await db.pool().fetchrow(
        """
        INSERT INTO users (
            org_id,email,name,role,password_hash,auth_provider,email_verified,
            must_change_password,password_changed_at
        ) VALUES ($1,lower($2),$3,$4::user_role,$5,'password',false,true,NULL)
        RETURNING id
        """,
        body.org_id,
        str(body.email),
        body.name.strip(),
        body.role,
        hash_secret(body.temporary_password),
    )
    await record_audit(
        org_id=body.org_id,
        user_id=user.id,
        action="platform_create_user",
        resource="user",
        resource_id=row["id"],
        metadata={"email": str(body.email).lower(), "role": body.role, "force_change": True},
    )
    return await _user_out(row["id"])


@router.get("/users", response_model=list[PlatformUserOut])
async def users(
    search: str = Query(default="", max_length=160),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(require_platform_admin),
) -> list[PlatformUserOut]:
    del user
    term = search.strip()
    rows = await db.pool().fetch(
        """
        SELECT u.id, u.org_id, o.name AS org_name, u.name, u.email, u.role,
               u.is_active, o.is_active AS organization_active, u.auth_provider,
               u.email_verified, u.must_change_password, u.last_login_at,
               u.created_at, u.updated_at
        FROM users u
        JOIN organizations o ON o.id=u.org_id
        WHERE ($1='' OR u.name ILIKE '%' || $1 || '%'
                     OR u.email ILIKE '%' || $1 || '%'
                     OR o.name ILIKE '%' || $1 || '%')
        ORDER BY u.is_active DESC, u.last_login_at DESC NULLS LAST, u.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        term,
        limit,
        offset,
    )
    return [PlatformUserOut(**dict(row)) for row in rows]


@router.patch("/users/{target_id}", response_model=PlatformUserOut)
async def update_user(
    target_id: UUID,
    body: PlatformUserUpdateIn,
    user: CurrentUser = Depends(require_platform_admin),
) -> PlatformUserOut:
    if not body.model_fields_set:
        raise HTTPException(422, "No se recibieron cambios")
    current = await db.pool().fetchrow(
        """
        SELECT u.id, u.org_id, u.email, u.role, u.is_active
        FROM users u WHERE u.id=$1
        """,
        target_id,
    )
    if current is None:
        raise HTTPException(404, "Usuario no encontrado")
    next_role = body.role or current["role"]
    next_active = current["is_active"] if body.is_active is None else body.is_active
    target_email = str(current["email"]).lower()
    if target_id == user.id and (not next_active or next_role != "admin"):
        raise HTTPException(409, "No podés quitar tu propio acceso de administrador general")
    if target_email in get_settings().platform_admin_list and (
        not next_active or next_role != "admin"
    ):
        raise HTTPException(409, "Un administrador general configurado debe permanecer activo y con rol admin")

    await db.pool().execute(
        """
        UPDATE users SET name=COALESCE($2,name), role=COALESCE($3::user_role,role),
                         is_active=COALESCE($4,is_active), updated_at=now()
        WHERE id=$1
        """,
        target_id,
        body.name.strip() if body.name else None,
        body.role,
        body.is_active,
    )
    await record_audit(
        org_id=current["org_id"],
        user_id=user.id,
        action="platform_update_user",
        resource="user",
        resource_id=target_id,
        metadata=body.model_dump(exclude_none=True),
    )
    return await _user_out(target_id)


@router.post("/users/{target_id}/reset-password")
async def reset_password(
    target_id: UUID,
    body: PlatformPasswordResetIn,
    user: CurrentUser = Depends(require_platform_admin),
) -> dict[str, object]:
    if target_id == user.id:
        raise HTTPException(409, "No restablezcas tu propia contraseña desde una sesión activa")
    target = await db.pool().fetchrow(
        "SELECT id, org_id, email FROM users WHERE id=$1",
        target_id,
    )
    if target is None:
        raise HTTPException(404, "Usuario no encontrado")
    await db.pool().execute(
        """
        UPDATE users SET password_hash=$2, auth_provider='password', is_active=true,
            must_change_password=true, password_changed_at=NULL, updated_at=now()
        WHERE id=$1
        """,
        target_id,
        hash_secret(body.temporary_password),
    )
    await record_audit(
        org_id=target["org_id"],
        user_id=user.id,
        action="platform_reset_password",
        resource="user",
        resource_id=target_id,
        metadata={"email": target["email"], "force_change": True},
    )
    return {"status": "ok", "must_change_password": True}


@router.get("/organizations", response_model=list[PlatformOrganizationOut])
async def organizations(
    search: str = Query(default="", max_length=160),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(require_platform_admin),
) -> list[PlatformOrganizationOut]:
    del user
    rows = await db.pool().fetch(
        """
        SELECT o.id, o.name, o.slug, o.vertical::text AS vertical, o.province,
               o.municipality, o.is_active,
               count(u.id)::int AS users_total,
               (count(u.id) FILTER (WHERE u.is_active))::int AS users_active,
               os.plan_key, sp.display_name AS plan_name,
               os.status AS subscription_status,
               o.created_at, o.updated_at
        FROM organizations o
        LEFT JOIN users u ON u.org_id=o.id
        LEFT JOIN organization_subscriptions os ON os.org_id=o.id
        LEFT JOIN subscription_plans sp ON sp.plan_key=os.plan_key
        WHERE ($1='' OR o.name ILIKE '%' || $1 || '%'
                     OR o.slug ILIKE '%' || $1 || '%'
                     OR COALESCE(o.municipality,'') ILIKE '%' || $1 || '%')
        GROUP BY o.id, os.plan_key, sp.display_name, os.status
        ORDER BY o.is_active DESC, o.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        search.strip(),
        limit,
        offset,
    )
    return [PlatformOrganizationOut(**dict(row)) for row in rows]


@router.patch("/organizations/{org_id}", response_model=PlatformOrganizationOut)
async def update_organization(
    org_id: UUID,
    body: PlatformOrganizationUpdateIn,
    user: CurrentUser = Depends(require_platform_admin),
) -> PlatformOrganizationOut:
    if not body.model_fields_set:
        raise HTTPException(422, "No se recibieron cambios")
    if org_id == user.org_id and body.is_active is False:
        raise HTTPException(409, "No podés suspender la organización de tu propia cuenta")
    if body.is_active is False:
        protected = await db.pool().fetchval(
            """
            SELECT EXISTS(
              SELECT 1 FROM users
              WHERE org_id=$1 AND lower(email)=ANY($2::text[])
            )
            """,
            org_id,
            get_settings().platform_admin_list,
        )
        if protected:
            raise HTTPException(409, "La organización contiene un administrador general protegido")
    row = await db.pool().fetchrow(
        """
        UPDATE organizations SET name=COALESCE($2,name),
            is_active=COALESCE($3,is_active), updated_at=now()
        WHERE id=$1 RETURNING id
        """,
        org_id,
        body.name.strip() if body.name else None,
        body.is_active,
    )
    if row is None:
        raise HTTPException(404, "Organización no encontrada")
    await record_audit(
        org_id=org_id,
        user_id=user.id,
        action="platform_update_organization",
        resource="organization",
        resource_id=org_id,
        metadata=body.model_dump(exclude_none=True),
    )
    return await _organization_out(org_id)


@router.get("/audit", response_model=list[PlatformAuditOut])
async def audit(
    limit: int = Query(default=150, ge=1, le=500),
    user: CurrentUser = Depends(require_platform_admin),
) -> list[PlatformAuditOut]:
    del user
    rows = await db.pool().fetch(
        """
        SELECT ae.id, ae.org_id, o.name AS org_name, ae.user_id,
               u.name AS actor_name, ae.action, ae.resource, ae.resource_id,
               ae.metadata, ae.created_at
        FROM audit_events ae
        LEFT JOIN organizations o ON o.id=ae.org_id
        LEFT JOIN users u ON u.id=ae.user_id
        ORDER BY ae.created_at DESC
        LIMIT $1
        """,
        limit,
    )
    result: list[PlatformAuditOut] = []
    for row in rows:
        data = dict(row)
        if isinstance(data.get("metadata"), str):
            data["metadata"] = json.loads(data["metadata"])
        result.append(PlatformAuditOut(**data))
    return result
