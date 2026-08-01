"""Persistencia de snapshots SpaceAI y activacion de alertas ambientales."""
from __future__ import annotations

import json
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from .. import db
from ..audit import record_audit
from ..copernicus import public_status
from ..deps import CurrentUser, current_user, require_role
from ..environment import alert_type_for_domain, should_activate
from ..schemas import EnvironmentalSnapshot, EnvironmentalSnapshotRecordOut, EnvironmentalSourceSettingsOut
from ..ws import publish

router = APIRouter(prefix="/environment", tags=["environment"])


def _decode(value):
    return json.loads(value) if isinstance(value, str) else value


def _record_out(row) -> EnvironmentalSnapshotRecordOut:
    data = dict(row)
    data["snapshot"] = EnvironmentalSnapshot.model_validate(_decode(data["snapshot"]))
    return EnvironmentalSnapshotRecordOut(**data)


async def _settings(org_id: UUID) -> tuple[bool, str]:
    row = await db.pool().fetchrow(
        """
        INSERT INTO environmental_source_settings (
          org_id, copernicus_enabled, copernicus_use_system_default
        )
        VALUES ($1,true,true)
        ON CONFLICT (org_id) DO NOTHING
        RETURNING auto_activate_alerts, operational_alert_min_level
        """,
        org_id,
    )
    if row is None:
        row = await db.pool().fetchrow(
            "SELECT auto_activate_alerts, operational_alert_min_level FROM environmental_source_settings WHERE org_id=$1",
            org_id,
        )
    return bool(row["auto_activate_alerts"]), str(row["operational_alert_min_level"])


async def _activate_alerts(
    *,
    snapshot_id: UUID,
    snapshot: EnvironmentalSnapshot,
    org_id: UUID,
    user_id: UUID,
    minimum_level: str,
) -> int:
    p = db.pool()
    created = 0
    for model_alert in snapshot.alerts:
        if not should_activate(model_alert, minimum_level):
            continue
        alert_type = alert_type_for_domain(model_alert.domain)
        duplicate = await p.fetchval(
            """
            SELECT EXISTS(
              SELECT 1 FROM alerts
              WHERE org_id=$1
                AND type=$2::alert_type
                AND title=$3
                AND status IN ('nueva','confirmada','escalada','asignada')
                AND detected_at > now() - interval '2 hours'
                AND ST_DWithin(location, ST_MakePoint($5,$4)::geography, 5000)
            )
            """,
            org_id,
            alert_type,
            model_alert.title,
            snapshot.latitude,
            snapshot.longitude,
        )
        if duplicate:
            continue
        row = await p.fetchrow(
            """
            INSERT INTO alerts (
              org_id, type, severity, status, location, confidence, title, detected_at
            ) VALUES (
              $1,$2::alert_type,$3::alert_severity,'nueva',
              ST_MakePoint($5,$4)::geography,$6,$7,now()
            )
            RETURNING id
            """,
            org_id,
            alert_type,
            model_alert.severity,
            snapshot.latitude,
            snapshot.longitude,
            model_alert.confidence,
            model_alert.title,
        )
        detail = {
            "domain": model_alert.domain,
            "level": model_alert.level,
            "summary": model_alert.summary,
            "action": model_alert.action,
            "source": model_alert.source,
            "methodology_version": snapshot.methodology_version,
            "overall_level": snapshot.overall_level,
            "overall_score": snapshot.overall_score,
        }
        await p.execute(
            """
            INSERT INTO alert_sources (alert_id, source_type, ref_id, weight, detail)
            VALUES ($1,'modelo',$2,$3,$4::jsonb)
            """,
            row["id"],
            snapshot_id,
            model_alert.confidence,
            json.dumps(detail, ensure_ascii=False),
        )
        await p.execute(
            "INSERT INTO environmental_alert_links (snapshot_id, alert_id, domain) VALUES ($1,$2,$3)",
            snapshot_id,
            row["id"],
            model_alert.domain,
        )
        await p.execute(
            """
            INSERT INTO alert_events (alert_id, user_id, action, payload)
            VALUES ($1,$2,'activar_desde_spaceai',$3::jsonb)
            """,
            row["id"],
            user_id,
            json.dumps({"snapshot_id": str(snapshot_id), "level": model_alert.level}),
        )
        await p.execute(
            """
            INSERT INTO notifications (org_id, alert_id, title, body)
            VALUES ($1,$2,$3,$4)
            """,
            org_id,
            row["id"],
            f"{model_alert.level} · {model_alert.title}",
            model_alert.action,
        )
        await publish(
            f"econexo/internal/{org_id}/alerts",
            {
                "id": str(row["id"]),
                "title": model_alert.title,
                "confidence": model_alert.confidence,
                "source": "spaceai",
            },
        )
        created += 1
    if created:
        await p.execute(
            "UPDATE environmental_snapshots SET activated_alerts=activated_alerts+$2 WHERE id=$1",
            snapshot_id,
            created,
        )
    return created


@router.get("/source-settings", response_model=EnvironmentalSourceSettingsOut)
async def source_settings(
    user: CurrentUser = Depends(current_user),
) -> EnvironmentalSourceSettingsOut:
    """Configuracion operativa visible para todos los usuarios autenticados.

    Expone banderas y parametros, nunca credenciales de proveedores.
    """
    row = await db.pool().fetchrow(
        """
        INSERT INTO environmental_source_settings (
          org_id, copernicus_enabled, copernicus_use_system_default
        )
        VALUES ($1,true,true)
        ON CONFLICT (org_id) DO NOTHING
        RETURNING *
        """,
        user.org_id,
    )
    if row is None:
        row = await db.pool().fetchrow(
            "SELECT * FROM environmental_source_settings WHERE org_id=$1",
            user.org_id,
        )
    data = dict(row)
    data.pop("updated_by", None)
    data.pop("created_at", None)
    data["firms_map_key_configured"] = bool(os.getenv("NASA_FIRMS_KEY", "").strip())
    state = public_status(data)
    data.update(
        copernicus_configured=state["configured"],
        copernicus_provider=state["provider"],
        copernicus_process_configured=state["process_configured"],
        copernicus_wms_configured=state["wms_configured"],
        copernicus_system_default=state["system_default"],
        copernicus_effective_wms_url=state["effective_wms_url"],
        copernicus_last_test_at=state["last_test_at"],
        copernicus_last_test_ok=state["last_test_ok"],
        copernicus_last_error=state["last_error"],
        copernicus_available_layers=state["available_layers"],
    )
    return EnvironmentalSourceSettingsOut(**data)


@router.post("/snapshots", response_model=EnvironmentalSnapshotRecordOut, status_code=201)
async def create_snapshot(
    body: EnvironmentalSnapshot,
    activate_alerts: bool | None = Query(default=None),
    origin: str = Query(default="observatorio_web", min_length=2, max_length=80),
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> EnvironmentalSnapshotRecordOut:
    automatic, minimum_level = await _settings(user.org_id)
    should_create_alerts = automatic if activate_alerts is None else activate_alerts
    row = await db.pool().fetchrow(
        """
        INSERT INTO environmental_snapshots (
          org_id, created_by, methodology_version, overall_level, overall_score,
          location, origin, snapshot
        ) VALUES (
          $1,$2,$3,$4,$5,ST_MakePoint($7,$6)::geography,$8,$9::jsonb
        )
        RETURNING id, org_id, created_by, origin, activated_alerts, snapshot, created_at
        """,
        user.org_id,
        user.id,
        body.methodology_version,
        body.overall_level,
        body.overall_score,
        body.latitude,
        body.longitude,
        origin,
        json.dumps(body.model_dump(mode="json"), ensure_ascii=False),
    )
    created = 0
    if should_create_alerts:
        created = await _activate_alerts(
            snapshot_id=row["id"],
            snapshot=body,
            org_id=user.org_id,
            user_id=user.id,
            minimum_level=minimum_level,
        )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="create",
        resource="environmental_snapshot",
        resource_id=row["id"],
        metadata={
            "overall_level": body.overall_level,
            "overall_score": body.overall_score,
            "activated_alerts": created,
            "origin": origin,
        },
    )
    row = dict(row)
    row["activated_alerts"] = created
    return _record_out(row)


@router.get("/snapshots", response_model=list[EnvironmentalSnapshotRecordOut])
async def list_snapshots(
    limit: int = Query(default=50, ge=1, le=250),
    user: CurrentUser = Depends(current_user),
) -> list[EnvironmentalSnapshotRecordOut]:
    rows = await db.pool().fetch(
        """
        SELECT id, org_id, created_by, origin, activated_alerts, snapshot, created_at
        FROM environmental_snapshots
        WHERE org_id=$1 AND econexo_inside_misiones(location)
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user.org_id,
        limit,
    )
    return [_record_out(row) for row in rows]


@router.get("/snapshots/latest", response_model=EnvironmentalSnapshotRecordOut)
async def latest_snapshot(
    user: CurrentUser = Depends(current_user),
) -> EnvironmentalSnapshotRecordOut:
    row = await db.pool().fetchrow(
        """
        SELECT id, org_id, created_by, origin, activated_alerts, snapshot, created_at
        FROM environmental_snapshots
        WHERE org_id=$1 AND econexo_inside_misiones(location)
        ORDER BY created_at DESC
        LIMIT 1
        """,
        user.org_id,
    )
    if row is None:
        raise HTTPException(404, "No hay snapshots ambientales registrados")
    return _record_out(row)


@router.post("/snapshots/{snapshot_id}/activate", response_model=EnvironmentalSnapshotRecordOut)
async def activate_snapshot_alerts(
    snapshot_id: UUID,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> EnvironmentalSnapshotRecordOut:
    row = await db.pool().fetchrow(
        """
        SELECT id, org_id, created_by, origin, activated_alerts, snapshot, created_at
        FROM environmental_snapshots
        WHERE id=$1 AND org_id=$2
        """,
        snapshot_id,
        user.org_id,
    )
    if row is None:
        raise HTTPException(404, "Snapshot no encontrado")
    snapshot = EnvironmentalSnapshot.model_validate(_decode(row["snapshot"]))
    _, minimum_level = await _settings(user.org_id)
    created = await _activate_alerts(
        snapshot_id=snapshot_id,
        snapshot=snapshot,
        org_id=user.org_id,
        user_id=user.id,
        minimum_level=minimum_level,
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="activate_alerts",
        resource="environmental_snapshot",
        resource_id=snapshot_id,
        metadata={"created": created, "minimum_level": minimum_level},
    )
    refreshed = await db.pool().fetchrow(
        """
        SELECT id, org_id, created_by, origin, activated_alerts, snapshot, created_at
        FROM environmental_snapshots WHERE id=$1
        """,
        snapshot_id,
    )
    return _record_out(refreshed)


@router.delete("/snapshots/{snapshot_id}", status_code=204)
async def delete_snapshot(
    snapshot_id: UUID,
    user: CurrentUser = Depends(require_role("admin")),
) -> Response:
    result = await db.pool().execute(
        "DELETE FROM environmental_snapshots WHERE id=$1 AND org_id=$2",
        snapshot_id,
        user.org_id,
    )
    if result.endswith("0"):
        raise HTTPException(404, "Snapshot no encontrado")
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="delete",
        resource="environmental_snapshot",
        resource_id=snapshot_id,
    )
    return Response(status_code=204)
