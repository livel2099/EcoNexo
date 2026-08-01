"""Panel administrativo y operaciones ABM por organizacion."""
from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET

import httpx
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from .. import db
from ..audit import record_audit
from ..deps import CurrentUser, require_role
from ..schemas import (
    AdminSummaryOut,
    AdminUserCreateIn,
    AdminUserOut,
    AdminUserUpdateIn,
    AuditEventOut,
    CopernicusWmsTestIn,
    CopernicusWmsTestOut,
    EnvironmentalSourceSettingsIn,
    EnvironmentalSourceSettingsOut,
    OrgOut,
    OrgUpdateIn,
)
from ..security import hash_secret
from ..subscriptions import enforce_resource_limit

router = APIRouter(prefix="/admin", tags=["admin"])


async def _active_admin_count(org_id: UUID) -> int:
    return int(
        await db.pool().fetchval(
            "SELECT count(*) FROM users WHERE org_id=$1 AND role='admin' AND is_active",
            org_id,
        )
        or 0
    )


def _user_out(row) -> AdminUserOut:
    return AdminUserOut(**dict(row))


async def _settings_row(org_id: UUID, user_id: UUID | None = None):
    return await db.pool().fetchrow(
        """
        INSERT INTO environmental_source_settings (org_id, updated_by)
        VALUES ($1,$2)
        ON CONFLICT (org_id) DO UPDATE
          SET updated_by=COALESCE(environmental_source_settings.updated_by, EXCLUDED.updated_by)
        RETURNING *
        """,
        org_id,
        user_id,
    )


def _settings_out(row) -> EnvironmentalSourceSettingsOut:
    data = dict(row)
    data.pop("updated_by", None)
    data.pop("created_at", None)
    data["firms_map_key_configured"] = bool(os.getenv("NASA_FIRMS_KEY", "").strip())
    data["copernicus_configured"] = bool((data.get("copernicus_wms_url") or "").strip())
    return EnvironmentalSourceSettingsOut(**data)


@router.get("/summary", response_model=AdminSummaryOut)
async def summary(user: CurrentUser = Depends(require_role("admin"))) -> AdminSummaryOut:
    row = await db.pool().fetchrow(
        """
        SELECT
          (SELECT count(*) FROM users WHERE org_id=$1) AS users_total,
          (SELECT count(*) FROM users WHERE org_id=$1 AND is_active) AS users_active,
          (SELECT count(*) FROM devices WHERE org_id=$1 AND econexo_inside_misiones(location)) AS devices_total,
          (SELECT count(*) FROM devices WHERE org_id=$1 AND status='online' AND econexo_inside_misiones(location)) AS devices_online,
          (SELECT count(*) FROM risk_zones WHERE org_id=$1 AND econexo_inside_misiones(center)) AS zones_total,
          (SELECT count(*) FROM rules WHERE org_id=$1) AS rules_total,
          (SELECT count(*) FROM rules WHERE org_id=$1 AND enabled) AS rules_enabled,
          (SELECT count(*) FROM citizen_reports WHERE org_id=$1 AND status='pendiente' AND econexo_inside_misiones(location)) AS reports_pending,
          (SELECT count(*) FROM alerts WHERE org_id=$1 AND status IN ('nueva','confirmada','escalada','asignada') AND econexo_inside_misiones(location)) AS alerts_active,
          (SELECT count(*) FROM environmental_snapshots WHERE org_id=$1 AND created_at > now() - interval '24 hours' AND econexo_inside_misiones(location)) AS snapshots_24h,
          (SELECT overall_level FROM environmental_snapshots WHERE org_id=$1 ORDER BY created_at DESC LIMIT 1) AS last_snapshot_level,
          (SELECT overall_score FROM environmental_snapshots WHERE org_id=$1 ORDER BY created_at DESC LIMIT 1) AS last_snapshot_score,
          (SELECT created_at FROM environmental_snapshots WHERE org_id=$1 ORDER BY created_at DESC LIMIT 1) AS last_snapshot_at
        """,
        user.org_id,
    )
    return AdminSummaryOut(**dict(row))


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(user: CurrentUser = Depends(require_role("admin"))) -> list[AdminUserOut]:
    rows = await db.pool().fetch(
        """
        SELECT id, name, email, role, is_active, auth_provider, email_verified,
               avatar_url, last_login_at, created_at, updated_at
        FROM users WHERE org_id=$1
        ORDER BY is_active DESC, role, name
        """,
        user.org_id,
    )
    return [_user_out(row) for row in rows]


@router.post("/users", response_model=AdminUserOut, status_code=201)
async def create_user(
    body: AdminUserCreateIn,
    user: CurrentUser = Depends(require_role("admin")),
) -> AdminUserOut:
    await enforce_resource_limit(user.org_id, "max_users")
    p = db.pool()
    if await p.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE lower(email)=lower($1))", str(body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya esta registrado")
    row = await p.fetchrow(
        """
        INSERT INTO users (org_id, email, name, role, password_hash, auth_provider, email_verified)
        VALUES ($1,lower($2),$3,$4::user_role,$5,'password',false)
        RETURNING id, name, email, role, is_active, auth_provider, email_verified,
                  avatar_url, last_login_at, created_at, updated_at
        """,
        user.org_id,
        str(body.email),
        body.name.strip(),
        body.role,
        hash_secret(body.password),
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="create",
        resource="user",
        resource_id=row["id"],
        metadata={"email": row["email"], "role": row["role"]},
    )
    return _user_out(row)


@router.patch("/users/{target_id}", response_model=AdminUserOut)
async def update_user(
    target_id: UUID,
    body: AdminUserUpdateIn,
    user: CurrentUser = Depends(require_role("admin")),
) -> AdminUserOut:
    p = db.pool()
    current = await p.fetchrow(
        "SELECT id, role, is_active FROM users WHERE id=$1 AND org_id=$2",
        target_id,
        user.org_id,
    )
    if current is None:
        raise HTTPException(404, "Usuario no encontrado")
    next_role = body.role or current["role"]
    next_active = current["is_active"] if body.is_active is None else body.is_active
    removes_admin = current["role"] == "admin" and current["is_active"] and (
        next_role != "admin" or not next_active
    )
    if removes_admin and await _active_admin_count(user.org_id) <= 1:
        raise HTTPException(409, "La organizacion debe conservar al menos un administrador activo")
    if target_id == user.id and not next_active:
        raise HTTPException(409, "No puedes desactivar tu propia cuenta")
    if not current["is_active"] and next_active:
        await enforce_resource_limit(user.org_id, "max_users")

    row = await p.fetchrow(
        """
        UPDATE users
        SET name=COALESCE($3,name), role=COALESCE($4::user_role,role),
            is_active=COALESCE($5,is_active)
        WHERE id=$1 AND org_id=$2
        RETURNING id, name, email, role, is_active, auth_provider, email_verified,
                  avatar_url, last_login_at, created_at, updated_at
        """,
        target_id,
        user.org_id,
        body.name.strip() if body.name else None,
        body.role,
        body.is_active,
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="update",
        resource="user",
        resource_id=target_id,
        metadata=body.model_dump(exclude_none=True),
    )
    return _user_out(row)


@router.delete("/users/{target_id}", status_code=204)
async def deactivate_user(
    target_id: UUID,
    user: CurrentUser = Depends(require_role("admin")),
) -> Response:
    if target_id == user.id:
        raise HTTPException(409, "No puedes desactivar tu propia cuenta")
    row = await db.pool().fetchrow(
        "SELECT role, is_active FROM users WHERE id=$1 AND org_id=$2",
        target_id,
        user.org_id,
    )
    if row is None:
        raise HTTPException(404, "Usuario no encontrado")
    if row["role"] == "admin" and row["is_active"] and await _active_admin_count(user.org_id) <= 1:
        raise HTTPException(409, "La organizacion debe conservar al menos un administrador activo")
    await db.pool().execute(
        "UPDATE users SET is_active=false WHERE id=$1 AND org_id=$2",
        target_id,
        user.org_id,
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="deactivate",
        resource="user",
        resource_id=target_id,
    )
    return Response(status_code=204)


@router.patch("/organization", response_model=OrgOut)
async def update_organization(
    body: OrgUpdateIn,
    user: CurrentUser = Depends(require_role("admin")),
) -> OrgOut:
    if not body.model_fields_set:
        raise HTTPException(422, "No se recibieron cambios")
    row = await db.pool().fetchrow(
        """
        UPDATE organizations
        SET name=COALESCE($2,name), primary_color=COALESCE($3,primary_color),
            baseline_response_s=COALESCE($4,baseline_response_s),
            department=COALESCE($5,department), municipality=COALESCE($6,municipality),
            territory_scope=COALESCE($7,territory_scope)
        WHERE id=$1
        RETURNING id, name, slug, vertical, primary_color, baseline_response_s,
                  province, department, municipality, territory_scope
        """,
        user.org_id,
        body.name.strip() if body.name else None,
        body.primary_color,
        body.baseline_response_s,
        body.department,
        body.municipality,
        body.territory_scope,
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="update",
        resource="organization",
        resource_id=user.org_id,
        metadata=body.model_dump(exclude_none=True),
    )
    return OrgOut(**dict(row))


@router.get("/source-settings", response_model=EnvironmentalSourceSettingsOut)
async def get_source_settings(
    user: CurrentUser = Depends(require_role("admin")),
) -> EnvironmentalSourceSettingsOut:
    return _settings_out(await _settings_row(user.org_id, user.id))


@router.patch("/source-settings", response_model=EnvironmentalSourceSettingsOut)
async def update_source_settings(
    body: EnvironmentalSourceSettingsIn,
    user: CurrentUser = Depends(require_role("admin")),
) -> EnvironmentalSourceSettingsOut:
    row = await db.pool().fetchrow(
        """
        INSERT INTO environmental_source_settings (
          org_id, default_latitude, default_longitude, open_meteo_enabled,
          air_quality_enabled, flood_enabled, firms_enabled, copernicus_enabled,
          copernicus_wms_url, copernicus_true_color_layer, copernicus_ndvi_layer,
          copernicus_moisture_layer, copernicus_burn_layer, forestry_pest_enabled,
          sinarame_radar_enabled, refresh_minutes, fire_radius_km,
          operational_alert_min_level, auto_activate_alerts, updated_by
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20)
        ON CONFLICT (org_id) DO UPDATE SET
          default_latitude=EXCLUDED.default_latitude,
          default_longitude=EXCLUDED.default_longitude,
          open_meteo_enabled=EXCLUDED.open_meteo_enabled,
          air_quality_enabled=EXCLUDED.air_quality_enabled,
          flood_enabled=EXCLUDED.flood_enabled,
          firms_enabled=EXCLUDED.firms_enabled,
          copernicus_enabled=EXCLUDED.copernicus_enabled,
          copernicus_wms_url=EXCLUDED.copernicus_wms_url,
          copernicus_true_color_layer=EXCLUDED.copernicus_true_color_layer,
          copernicus_ndvi_layer=EXCLUDED.copernicus_ndvi_layer,
          copernicus_moisture_layer=EXCLUDED.copernicus_moisture_layer,
          copernicus_burn_layer=EXCLUDED.copernicus_burn_layer,
          forestry_pest_enabled=EXCLUDED.forestry_pest_enabled,
          sinarame_radar_enabled=EXCLUDED.sinarame_radar_enabled,
          refresh_minutes=EXCLUDED.refresh_minutes,
          fire_radius_km=EXCLUDED.fire_radius_km,
          operational_alert_min_level=EXCLUDED.operational_alert_min_level,
          auto_activate_alerts=EXCLUDED.auto_activate_alerts,
          updated_by=EXCLUDED.updated_by,
          updated_at=now()
        RETURNING *
        """,
        user.org_id,
        body.default_latitude,
        body.default_longitude,
        body.open_meteo_enabled,
        body.air_quality_enabled,
        body.flood_enabled,
        body.firms_enabled,
        body.copernicus_enabled,
        body.copernicus_wms_url,
        body.copernicus_true_color_layer,
        body.copernicus_ndvi_layer,
        body.copernicus_moisture_layer,
        body.copernicus_burn_layer,
        body.forestry_pest_enabled,
        body.sinarame_radar_enabled,
        body.refresh_minutes,
        body.fire_radius_km,
        body.operational_alert_min_level,
        body.auto_activate_alerts,
        user.id,
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="update",
        resource="environmental_source_settings",
        resource_id=user.org_id,
        metadata=body.model_dump(mode="json"),
    )
    return _settings_out(row)


@router.post("/copernicus/test", response_model=CopernicusWmsTestOut)
async def test_copernicus_wms(
    body: CopernicusWmsTestIn,
    user: CurrentUser = Depends(require_role("admin")),
) -> CopernicusWmsTestOut:
    """Prueba GetCapabilities sin aceptar destinos arbitrarios."""
    capabilities_url = f"{body.url}?SERVICE=WMS&REQUEST=GetCapabilities"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.get(capabilities_url, headers={"User-Agent": "EcoNexo-Misiones/1.0"})
        response.raise_for_status()
        root = ET.fromstring(response.content)
        title = None
        layers: list[str] = []
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "Title" and title is None and element.text:
                title = element.text.strip()
            elif tag == "Name" and element.text:
                value = element.text.strip()
                if value and value not in layers and value.upper() != "WMS":
                    layers.append(value)
        await record_audit(
            org_id=user.org_id,
            user_id=user.id,
            action="test",
            resource="copernicus_wms",
            resource_id=user.org_id,
            metadata={"host": "sh.dataspace.copernicus.eu", "layers": layers[:30]},
        )
        return CopernicusWmsTestOut(
            ok=True,
            service_title=title,
            layers=layers[:100],
            detail=f"Conexión correcta. {len(layers)} capas informadas por GetCapabilities.",
        )
    except (httpx.HTTPError, ET.ParseError) as exc:
        return CopernicusWmsTestOut(ok=False, detail=f"No se pudo validar la instancia WMS: {type(exc).__name__}")


@router.get("/audit", response_model=list[AuditEventOut])
async def list_audit(
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = Depends(require_role("admin")),
) -> list[AuditEventOut]:
    rows = await db.pool().fetch(
        """
        SELECT a.id, a.user_id, u.name AS actor_name, a.action, a.resource,
               a.resource_id, a.metadata, a.created_at
        FROM audit_events a
        LEFT JOIN users u ON u.id=a.user_id
        WHERE a.org_id=$1
        ORDER BY a.created_at DESC
        LIMIT $2
        """,
        user.org_id,
        limit,
    )
    output: list[AuditEventOut] = []
    for row in rows:
        data = dict(row)
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        data["metadata"] = metadata or {}
        output.append(AuditEventOut(**data))
    return output
