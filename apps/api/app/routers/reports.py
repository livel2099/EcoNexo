"""Reportes ciudadanos (PWA publica) + backoffice de moderacion con filtro IA."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from .. import db
from ..correlation import update_reputation
from ..deps import CurrentUser, current_user, require_role
from ..schemas import ReportModerateIn, ReportOut
from ..storage import put_photo
from ..ws import publish

router = APIRouter(prefix="/reports", tags=["reports"])

_COLS = (
    "id, type, description, photo_url, ST_Y(location::geometry) AS lat, "
    "ST_X(location::geometry) AS lon, status, correlation_score, reputation_score, created_at"
)


async def _correlation_score(org_id: UUID, lat: float, lon: float) -> float:
    """Cercania a lecturas/satelite anomalos: 0..1 segun evidencia proxima."""
    row = await db.pool().fetchrow(
        """
        SELECT
          (SELECT count(*) FROM satellite_detections
             WHERE ST_DWithin(location, ST_MakePoint($2,$1)::geography, 2000)
               AND acquired_at > now() - interval '6 hours') AS sat,
          (SELECT count(*) FROM alerts
             WHERE org_id=$3 AND status IN ('nueva','confirmada','escalada')
               AND ST_DWithin(location, ST_MakePoint($2,$1)::geography, 2000)) AS al
        """,
        lat, lon, org_id,
    )
    score = min(1.0, 0.35 * float(row["sat"]) + 0.5 * float(row["al"]))
    return round(score, 3)


@router.post("", response_model=ReportOut, status_code=201)
async def create_report(
    org_id: UUID = Form(...),
    type: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    citizen_token: str = Form(...),
    description: str | None = Form(None),
    photo: UploadFile | None = File(None),
) -> ReportOut:
    """Endpoint publico (sin auth): la PWA ciudadana envia el reporte."""
    p = db.pool()
    citizen = await p.fetchrow(
        """
        INSERT INTO citizens (token) VALUES ($1)
        ON CONFLICT (token) DO UPDATE SET token = EXCLUDED.token
        RETURNING id, valid_count, invalid_count
        """,
        citizen_token,
    )
    reputation = update_reputation(citizen["valid_count"], citizen["invalid_count"])

    photo_url = None
    if photo is not None:
        photo_url = put_photo(await photo.read(), photo.content_type or "image/jpeg")

    corr = await _correlation_score(org_id, lat, lon)
    row = await p.fetchrow(
        f"""
        INSERT INTO citizen_reports
            (org_id, citizen_id, type, description, photo_url, location,
             correlation_score, reputation_score)
        VALUES ($1,$2,$3,$4,$5, ST_MakePoint($7,$6)::geography, $8, $9)
        RETURNING {_COLS}
        """,
        org_id, citizen["id"], type, description, photo_url, lat, lon, corr, reputation,
    )
    await publish(f"econexo/internal/{org_id}/reports",
                  {"id": str(row["id"]), "type": type, "lat": lat, "lon": lon})
    return ReportOut(**dict(row))


@router.get("", response_model=list[ReportOut])
async def list_reports(
    status: str | None = None, user: CurrentUser = Depends(current_user)
) -> list[ReportOut]:
    rows = await db.pool().fetch(
        f"SELECT {_COLS} FROM citizen_reports WHERE org_id=$1 "
        "AND ($2::text IS NULL OR status=$2::report_status) ORDER BY created_at DESC",
        user.org_id, status,
    )
    return [ReportOut(**dict(r)) for r in rows]


@router.post("/{report_id}/moderate", response_model=ReportOut)
async def moderate(
    report_id: UUID, body: ReportModerateIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> ReportOut:
    p = db.pool()
    rep = await p.fetchrow(
        f"UPDATE citizen_reports SET status=$3::report_status WHERE id=$1 AND org_id=$2 "
        f"RETURNING {_COLS}, citizen_id",
        report_id, user.org_id, body.status,
    )
    if rep is None:
        raise HTTPException(404, "Reporte no encontrado")
    # actualizar reputacion dinamica del emisor
    if rep["citizen_id"] is not None:
        col = "valid_count" if body.status == "verificado" else "invalid_count"
        c = await p.fetchrow(
            f"UPDATE citizens SET {col} = {col} + 1 WHERE id=$1 "
            "RETURNING valid_count, invalid_count",
            rep["citizen_id"],
        )
        await p.execute(
            "UPDATE citizens SET reputation=$2 WHERE id=$1",
            rep["citizen_id"], update_reputation(c["valid_count"], c["invalid_count"]),
        )
    return ReportOut(**{k: rep[k] for k in rep.keys() if k != "citizen_id"})
