"""Reportes ciudadanos + moderacion institucional con controles antiabuso."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from .. import db
from ..audit import record_audit
from ..config import get_settings
from ..correlation import update_reputation
from ..deps import CurrentUser, current_user, require_role
from ..rate_limit import enforce_rate_limit
from ..schemas import CitizenSessionOut, ReportModerateIn, ReportOut
from ..security import create_citizen_token, decode_citizen_token
from ..storage import put_photo, resolve_photo_url, validate_image
from ..territory import ensure_in_misiones, local_context
from ..ws import publish

router = APIRouter(prefix="/reports", tags=["reports"])

_COLS = (
    "id, type, description, photo_url, ST_Y(location::geometry) AS lat, "
    "ST_X(location::geometry) AS lon, status, correlation_score, reputation_score, created_at"
)
_ALLOWED_TYPES = {"humo", "incendio", "inundacion", "vertido", "otro"}


def _out(row) -> ReportOut:
    data = dict(row)
    data["photo_url"] = resolve_photo_url(data.get("photo_url"))
    return ReportOut(**data)


async def _correlation_score(org_id: UUID, lat: float, lon: float) -> float:
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


@router.get("/citizen-session", response_model=CitizenSessionOut)
async def citizen_session(request: Request) -> CitizenSessionOut:
    await enforce_rate_limit(
        request, bucket="citizen-session", limit=8, window_seconds=60 * 60
    )
    settings = get_settings()
    return CitizenSessionOut(
        token=create_citizen_token(), expires_in_days=settings.citizen_token_days
    )


@router.post("", response_model=ReportOut, status_code=201)
async def create_report(
    request: Request,
    org_id: UUID = Form(...),
    type: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    citizen_token: str = Form(...),
    description: str | None = Form(None),
    privacy_accepted: bool = Form(False),
    website: str = Form(""),  # honeypot invisible para bots
    photo: UploadFile | None = File(None),
) -> ReportOut:
    await enforce_rate_limit(
        request, bucket="public-report", limit=10, window_seconds=60 * 60
    )
    if website:
        raise HTTPException(400, "Solicitud invalida")
    if not privacy_accepted:
        raise HTTPException(422, "Debes aceptar el tratamiento de datos del reporte")
    if type not in _ALLOWED_TYPES:
        raise HTTPException(422, "Tipo de incidente invalido")
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise HTTPException(422, "Coordenadas invalidas")
    try:
        ensure_in_misiones(lat, lon)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if description is not None and len(description.strip()) > 1000:
        raise HTTPException(422, "La descripcion excede 1000 caracteres")
    citizen_id = decode_citizen_token(citizen_token)
    if citizen_id is None:
        raise HTTPException(401, "Sesion ciudadana invalida o expirada")

    p = db.pool()
    if not await p.fetchval("SELECT EXISTS(SELECT 1 FROM organizations WHERE id=$1)", org_id):
        raise HTTPException(404, "Organizacion no encontrada")
    citizen = await p.fetchrow(
        """
        INSERT INTO citizens (token) VALUES ($1)
        ON CONFLICT (token) DO UPDATE SET token = EXCLUDED.token
        RETURNING id, valid_count, invalid_count
        """,
        citizen_id,
    )
    reputation = update_reputation(citizen["valid_count"], citizen["invalid_count"])

    photo_reference = None
    if photo is not None:
        settings = get_settings()
        data = await photo.read(settings.max_report_photo_bytes + 1)
        if len(data) > settings.max_report_photo_bytes:
            raise HTTPException(413, "La imagen supera el limite de 8 MB")
        if not data:
            raise HTTPException(422, "La imagen esta vacia")
        try:
            extension = validate_image(data, photo.content_type or "")
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        photo_reference = put_photo(data, photo.content_type or "image/jpeg", extension)

    corr = await _correlation_score(org_id, lat, lon)
    row = await p.fetchrow(
        f"""
        INSERT INTO citizen_reports
            (org_id, citizen_id, type, description, photo_url, location,
             correlation_score, reputation_score)
        VALUES ($1,$2,$3,$4,$5, ST_MakePoint($7,$6)::geography, $8, $9)
        RETURNING {_COLS}
        """,
        org_id, citizen["id"], type, description.strip() if description else None,
        photo_reference, lat, lon, corr, reputation,
    )
    await publish(
        f"econexo/internal/{org_id}/reports",
        {"id": str(row["id"]), "type": type, "lat": lat, "lon": lon},
    )
    return _out(row)


@router.post("/internal", response_model=ReportOut, status_code=201)
async def create_internal_report(
    type: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    description: str | None = Form(None),
    photo: UploadFile | None = File(None),
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> ReportOut:
    """Carga institucional desde el panel o la app movil.

    Se registra en la misma cola de moderacion que los reportes comunitarios,
    pero queda asociado a una sesion autenticada mediante auditoria. No reemplaza
    una llamada a emergencias ni confirma por si solo un incendio.
    """
    if type not in _ALLOWED_TYPES:
        raise HTTPException(422, "Tipo de incidente invalido")
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise HTTPException(422, "Coordenadas invalidas")
    try:
        ensure_in_misiones(lat, lon)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    cleaned = description.strip() if description else None
    if cleaned is not None and len(cleaned) > 1000:
        raise HTTPException(422, "La descripcion excede 1000 caracteres")

    photo_reference = None
    if photo is not None:
        settings = get_settings()
        data = await photo.read(settings.max_report_photo_bytes + 1)
        if len(data) > settings.max_report_photo_bytes:
            raise HTTPException(413, "La imagen supera el limite de 8 MB")
        if not data:
            raise HTTPException(422, "La imagen esta vacia")
        try:
            extension = validate_image(data, photo.content_type or "")
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        photo_reference = put_photo(data, photo.content_type or "image/jpeg", extension)

    corr = await _correlation_score(user.org_id, lat, lon)
    row = await db.pool().fetchrow(
        f"""
        INSERT INTO citizen_reports
            (org_id, citizen_id, type, description, photo_url, location,
             correlation_score, reputation_score)
        VALUES ($1,NULL,$2,$3,$4,ST_MakePoint($6,$5)::geography,$7,1.000)
        RETURNING {_COLS}
        """,
        user.org_id,
        type,
        cleaned,
        photo_reference,
        lat,
        lon,
        corr,
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="reporte_interno_creado",
        resource="citizen_report",
        resource_id=row["id"],
        metadata={"type": type, "lat": lat, "lon": lon, "source": "authenticated", "territory": local_context(lat, lon)},
    )
    await publish(
        f"econexo/internal/{user.org_id}/reports",
        {"id": str(row["id"]), "type": type, "lat": lat, "lon": lon, "source": "internal"},
    )
    return _out(row)


@router.get("", response_model=list[ReportOut])
async def list_reports(
    status: str | None = None, user: CurrentUser = Depends(current_user)
) -> list[ReportOut]:
    rows = await db.pool().fetch(
        f"SELECT {_COLS} FROM citizen_reports WHERE org_id=$1 AND econexo_inside_misiones(location) "
        "AND ($2::text IS NULL OR status=$2::report_status) ORDER BY created_at DESC",
        user.org_id, status,
    )
    return [_out(row) for row in rows]


@router.post("/{report_id}/moderate", response_model=ReportOut)
async def moderate(
    report_id: UUID,
    body: ReportModerateIn,
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
    if rep["citizen_id"] is not None:
        col = "valid_count" if body.status == "verificado" else "invalid_count"
        citizen = await p.fetchrow(
            f"UPDATE citizens SET {col} = {col} + 1 WHERE id=$1 "
            "RETURNING valid_count, invalid_count",
            rep["citizen_id"],
        )
        await p.execute(
            "UPDATE citizens SET reputation=$2 WHERE id=$1",
            rep["citizen_id"],
            update_reputation(citizen["valid_count"], citizen["invalid_count"]),
        )
    return _out({key: rep[key] for key in rep.keys() if key != "citizen_id"})
