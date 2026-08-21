"""Informes institucionales y de impacto, exportables y compartibles."""
from __future__ import annotations

import json
from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status

from .. import db
from ..config import get_settings
from ..deps import CurrentUser, current_user, require_role
from ..schemas import (
    ImpactReportCreateIn,
    ImpactReportOut,
    ImpactReportPublishOut,
    PublicImpactReportOut,
)
from ..security import new_token, token_digest
from ..subscriptions import require_active_subscription

router = APIRouter(prefix="/impact-reports", tags=["impact-reports"])

_SELECT = """
SELECT ir.id, ir.org_id, o.name AS org_name, ir.report_kind,
       ir.environmental_snapshot_id, ir.methodology_version, ir.official_metadata,
       ir.title, ir.recipient_type, ir.recipient_name, ir.period_start,
       ir.period_end, ir.executive_summary, ir.metrics, ir.highlights,
       ir.recommendations, ir.status, ir.published_at, ir.created_at, ir.updated_at
FROM impact_reports ir
JOIN organizations o ON o.id=ir.org_id
"""


def _json(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, str):
        return json.loads(value)
    return value


def _out(row) -> ImpactReportOut:
    data = dict(row)
    data["metrics"] = _json(data.get("metrics"), {})
    data["highlights"] = _json(data.get("highlights"), [])
    data["recommendations"] = _json(data.get("recommendations"), [])
    data["official_metadata"] = _json(data.get("official_metadata"), {})
    return ImpactReportOut(**data)


async def _period_metrics(org_id: UUID, start: date, end: date) -> dict:
    row = await db.pool().fetchrow(
        """
        SELECT
          o.baseline_response_s,
          (SELECT count(*) FROM devices d WHERE d.org_id=o.id AND econexo_inside_misiones(d.location)) AS devices_total,
          (SELECT count(*) FROM devices d WHERE d.org_id=o.id AND d.status='online' AND econexo_inside_misiones(d.location)) AS devices_online,
          (SELECT count(*) FROM alerts a WHERE a.org_id=o.id
             AND econexo_inside_misiones(a.location) AND a.detected_at::date BETWEEN $2 AND $3) AS alerts_total,
          (SELECT count(*) FROM alerts a WHERE a.org_id=o.id AND a.severity='critica'
             AND econexo_inside_misiones(a.location) AND a.detected_at::date BETWEEN $2 AND $3) AS critical_alerts,
          (SELECT count(*) FROM alerts a WHERE a.org_id=o.id AND a.status='confirmada'
             AND econexo_inside_misiones(a.location) AND a.detected_at::date BETWEEN $2 AND $3) AS alerts_confirmed,
          (SELECT count(*) FROM alerts a WHERE a.org_id=o.id AND a.status='descartada'
             AND econexo_inside_misiones(a.location) AND a.detected_at::date BETWEEN $2 AND $3) AS alerts_discarded,
          (SELECT AVG(EXTRACT(EPOCH FROM (a.acknowledged_at-a.detected_at)))
             FROM alerts a WHERE a.org_id=o.id AND a.acknowledged_at IS NOT NULL
             AND econexo_inside_misiones(a.location) AND a.detected_at::date BETWEEN $2 AND $3) AS avg_response_s,
          (SELECT AVG(EXTRACT(EPOCH FROM (a.detected_at-r.ts)))
             FROM alerts a
             JOIN LATERAL (
               SELECT rr.ts FROM readings rr
               WHERE rr.device_id=a.device_id AND rr.ts<=a.detected_at
               ORDER BY rr.ts DESC LIMIT 1
             ) r ON true
             WHERE a.org_id=o.id AND a.device_id IS NOT NULL
             AND econexo_inside_misiones(a.location)
             AND a.detected_at::date BETWEEN $2 AND $3) AS avg_detection_s,
          (SELECT count(*) FROM citizen_reports cr WHERE cr.org_id=o.id
             AND econexo_inside_misiones(cr.location) AND cr.created_at::date BETWEEN $2 AND $3) AS citizen_reports_total,
          (SELECT count(*) FROM citizen_reports cr WHERE cr.org_id=o.id AND cr.status='verificado'
             AND econexo_inside_misiones(cr.location) AND cr.created_at::date BETWEEN $2 AND $3) AS citizen_reports_verified,
          (SELECT count(*) FROM citizen_reports cr WHERE cr.org_id=o.id AND cr.status='rechazado'
             AND econexo_inside_misiones(cr.location) AND cr.created_at::date BETWEEN $2 AND $3) AS citizen_reports_rejected
        FROM organizations o WHERE o.id=$1
        """,
        org_id, start, end,
    )
    if row is None:
        raise HTTPException(404, "Organizacion no encontrada")
    confirmed = int(row["alerts_confirmed"] or 0)
    discarded = int(row["alerts_discarded"] or 0)
    moderated = confirmed + discarded
    verified = int(row["citizen_reports_verified"] or 0)
    rejected = int(row["citizen_reports_rejected"] or 0)
    response = float(row["avg_response_s"]) if row["avg_response_s"] is not None else None
    baseline = int(row["baseline_response_s"])
    return {
        "devices_total": int(row["devices_total"] or 0),
        "devices_online": int(row["devices_online"] or 0),
        "alerts_total": int(row["alerts_total"] or 0),
        "critical_alerts": int(row["critical_alerts"] or 0),
        "alerts_confirmed": confirmed,
        "model_precision": round(confirmed / moderated, 3) if moderated else None,
        "average_detection_seconds": round(float(row["avg_detection_s"]), 1)
        if row["avg_detection_s"] is not None else None,
        "average_response_seconds": round(response, 1) if response is not None else None,
        "response_time_reduction": round(1 - response / baseline, 3)
        if response is not None and baseline else None,
        "citizen_reports_total": int(row["citizen_reports_total"] or 0),
        "citizen_reports_verified": verified,
        "valid_reports_rate": round(verified / (verified + rejected), 3)
        if verified + rejected else None,
    }


def _highlights(metrics: dict) -> list[str]:
    values: list[str] = []
    if metrics["devices_total"]:
        online = round(metrics["devices_online"] / metrics["devices_total"] * 100)
        values.append(f"Disponibilidad de la red de sensores: {online}%.")
    if metrics["average_detection_seconds"] is not None:
        values.append(
            f"Tiempo medio de deteccion: {metrics['average_detection_seconds']:.0f} segundos."
        )
    if metrics["response_time_reduction"] is not None:
        values.append(
            "Reduccion estimada del tiempo de respuesta frente al baseline: "
            f"{metrics['response_time_reduction'] * 100:.0f}%."
        )
    if metrics["citizen_reports_total"]:
        values.append(
            f"Se recibieron {metrics['citizen_reports_total']} reportes ciudadanos; "
            f"{metrics['citizen_reports_verified']} fueron verificados."
        )
    if metrics["critical_alerts"]:
        values.append(
            f"El periodo registro {metrics['critical_alerts']} alertas criticas priorizadas."
        )
    return values[:6] or ["Periodo sin eventos suficientes para calcular tendencias concluyentes."]


@router.post("", response_model=ImpactReportOut, status_code=201)
async def create_report(
    body: ImpactReportCreateIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> ImpactReportOut:
    # La licencia sigue siendo obligatoria; lo que ya no existe es un tope
    # mensual de informes.
    await require_active_subscription(user.org_id)
    metrics = await _period_metrics(user.org_id, body.period_start, body.period_end)
    snapshot_row = None
    if body.environmental_snapshot_id is not None:
        snapshot_row = await db.pool().fetchrow(
            """
            SELECT id, methodology_version, snapshot, created_at
            FROM environmental_snapshots
            WHERE id=$1 AND org_id=$2
            """,
            body.environmental_snapshot_id,
            user.org_id,
        )
        if snapshot_row is None:
            raise HTTPException(404, "Snapshot ambiental no encontrado")
    elif body.report_kind != "desempeno_operativo":
        snapshot_row = await db.pool().fetchrow(
            """
            SELECT id, methodology_version, snapshot, created_at
            FROM environmental_snapshots
            WHERE org_id=$1 ORDER BY created_at DESC LIMIT 1
            """,
            user.org_id,
        )

    snapshot = _json(snapshot_row["snapshot"], {}) if snapshot_row is not None else None
    methodology_version = str(snapshot_row["methodology_version"]) if snapshot_row is not None else None
    org = await db.pool().fetchrow(
        """
        SELECT name, province, department, municipality, territory_scope
        FROM organizations WHERE id=$1
        """,
        user.org_id,
    )
    if org is None:
        raise HTTPException(404, "Organizacion no encontrada")
    document_code = f"ECX-MIS-{date.today():%Y%m%d}-{uuid4().hex[:8].upper()}"
    official_metadata = {
        "document_code": document_code,
        "document_class": body.report_kind,
        "document_version": "1.0",
        "territorial_version": "Misiones 2026-07-27",
        "province": org["province"] or "Misiones",
        "department": org["department"],
        "municipality": org["municipality"],
        "territory_scope": org["territory_scope"] or "provincial",
        "coordinate_reference_system": "WGS 84 / EPSG:4326",
        "issued_by_user_id": str(user.id),
        "issuing_area": body.issuing_area.strip() or "Centro de comando EcoNexo",
        "reviewed_by": body.reviewed_by.strip() or None,
        "laboratory_name": body.laboratory_name.strip() or None,
        "protocol_reference": body.protocol_reference.strip() or None,
        "sample_reference": body.sample_reference.strip() or None,
        "technical_notes": body.technical_notes.strip() or None,
        "verification_status": "revisado" if body.reviewed_by.strip() else "pendiente_revision_humana",
        "data_cutoff_at": str(snapshot_row["created_at"]) if snapshot_row is not None else f"{body.period_end}T23:59:59-03:00",
        "snapshot_created_at": str(snapshot_row["created_at"]) if snapshot_row is not None else None,
        "spaceai": snapshot,
        "emergency_channel": "911",
        "disclaimer": (
            "Documento emitido y versionado por EcoNexo para el territorio de Misiones. "
            "No constituye certificacion de una autoridad publica, diagnostico clinico, "
            "resultado de laboratorio ni sustituto de normativa o validacion presencial."
        ),
    }
    summary = body.executive_summary.strip() or (
        "EcoNexo consolido para la provincia de Misiones telemetria IoT, detecciones "
        "satelitales, contexto meteorologico y reportes ciudadanos. La lectura se limita "
        "al territorio provincial y requiere verificacion humana para decisiones oficiales."
    )
    recs = [item.strip() for item in body.recommendations if item.strip()][:12]
    if not recs:
        recs = [
            "Revisar las alertas criticas y documentar la accion institucional adoptada.",
            "Mantener calibrados los nodos con menor disponibilidad o bateria.",
            "Validar trimestralmente los indicadores con una fuente independiente.",
        ]
    highlights = _highlights(metrics)
    if snapshot:
        highlights = [
            f"Health Threat Index: {snapshot.get('overall_level', 's/d')} · {snapshot.get('overall_score', 's/d')}/100.",
            f"Snapshot ambiental: {snapshot.get('generated_at', snapshot_row['created_at'])}.",
            *highlights,
        ][:8]
    row = await db.pool().fetchrow(
        """
        INSERT INTO impact_reports (
          org_id, created_by, report_kind, environmental_snapshot_id,
          methodology_version, official_metadata, title, recipient_type,
          recipient_name, period_start, period_end, executive_summary, metrics,
          highlights, recommendations
        ) VALUES (
          $1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10,$11,$12,$13::jsonb,$14::jsonb,$15::jsonb
        )
        RETURNING id
        """,
        user.org_id,
        user.id,
        body.report_kind,
        snapshot_row["id"] if snapshot_row is not None else None,
        methodology_version,
        json.dumps(official_metadata, ensure_ascii=False, default=str),
        body.title.strip(),
        body.recipient_type,
        body.recipient_name.strip(),
        body.period_start,
        body.period_end,
        summary,
        json.dumps(metrics),
        json.dumps(highlights, ensure_ascii=False),
        json.dumps(recs, ensure_ascii=False),
    )
    created = await db.pool().fetchrow(
        _SELECT + " WHERE ir.id=$1 AND ir.org_id=$2", row["id"], user.org_id
    )
    return _out(created)


@router.get("", response_model=list[ImpactReportOut])
async def list_reports(user: CurrentUser = Depends(current_user)) -> list[ImpactReportOut]:
    rows = await db.pool().fetch(
        _SELECT + " WHERE ir.org_id=$1 ORDER BY ir.created_at DESC LIMIT 100",
        user.org_id,
    )
    return [_out(row) for row in rows]


@router.get("/{report_id}", response_model=ImpactReportOut)
async def get_report(
    report_id: UUID, user: CurrentUser = Depends(current_user)
) -> ImpactReportOut:
    row = await db.pool().fetchrow(
        _SELECT + " WHERE ir.id=$1 AND ir.org_id=$2", report_id, user.org_id
    )
    if row is None:
        raise HTTPException(404, "Informe no encontrado")
    return _out(row)


@router.post("/{report_id}/publish", response_model=ImpactReportPublishOut)
async def publish_report(
    report_id: UUID,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> ImpactReportPublishOut:
    raw_token = new_token(32)
    digest = token_digest(raw_token)
    row = await db.pool().fetchrow(
        """
        UPDATE impact_reports
        SET status='publicado', public_token_hash=$3, published_at=now(), updated_at=now()
        WHERE id=$1 AND org_id=$2
        RETURNING id
        """,
        report_id, user.org_id, digest,
    )
    if row is None:
        raise HTTPException(404, "Informe no encontrado")
    await db.pool().execute(
        """
        INSERT INTO audit_events (org_id,user_id,action,resource,resource_id)
        VALUES ($1,$2,'publish','impact_report',$3)
        """,
        user.org_id, user.id, report_id,
    )
    report_row = await db.pool().fetchrow(
        _SELECT + " WHERE ir.id=$1 AND ir.org_id=$2", report_id, user.org_id
    )
    base = get_settings().public_app_url.rstrip("/")
    return ImpactReportPublishOut(
        report=_out(report_row),
        share_url=f"{base}/informe?token={raw_token}",
        public_token=raw_token,
    )


@router.post("/{report_id}/revoke", response_model=ImpactReportOut)
async def revoke_report(
    report_id: UUID,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> ImpactReportOut:
    updated = await db.pool().fetchrow(
        """
        UPDATE impact_reports
        SET status='borrador', public_token_hash=NULL, published_at=NULL, updated_at=now()
        WHERE id=$1 AND org_id=$2 RETURNING id
        """,
        report_id, user.org_id,
    )
    if updated is None:
        raise HTTPException(404, "Informe no encontrado")
    row = await db.pool().fetchrow(
        _SELECT + " WHERE ir.id=$1 AND ir.org_id=$2", report_id, user.org_id
    )
    return _out(row)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: UUID,
    user: CurrentUser = Depends(require_role("admin")),
) -> Response:
    result = await db.pool().execute(
        "DELETE FROM impact_reports WHERE id=$1 AND org_id=$2", report_id, user.org_id
    )
    if result == "DELETE 0":
        raise HTTPException(404, "Informe no encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/public/view/{token}", response_model=PublicImpactReportOut)
async def public_report(token: str, response: Response) -> PublicImpactReportOut:
    if len(token) < 32 or len(token) > 256:
        raise HTTPException(404, "Informe no encontrado")
    row = await db.pool().fetchrow(
        """
        SELECT ir.report_kind, ir.environmental_snapshot_id,
               ir.methodology_version, ir.official_metadata,
               o.name AS org_name, o.vertical::text AS org_vertical,
               o.primary_color, ir.title, ir.recipient_type, ir.recipient_name,
               ir.period_start, ir.period_end, ir.executive_summary, ir.metrics,
               ir.highlights, ir.recommendations, ir.published_at
        FROM impact_reports ir
        JOIN organizations o ON o.id=ir.org_id
        WHERE ir.public_token_hash=$1 AND ir.status='publicado'
        """,
        token_digest(token),
    )
    if row is None:
        raise HTTPException(404, "Informe no encontrado o enlace revocado")
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    data = dict(row)
    data["metrics"] = _json(data.get("metrics"), {})
    data["highlights"] = _json(data.get("highlights"), [])
    data["recommendations"] = _json(data.get("recommendations"), [])
    data["official_metadata"] = _json(data.get("official_metadata"), {})
    return PublicImpactReportOut(**data)
