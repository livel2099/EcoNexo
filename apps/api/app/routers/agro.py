"""EcoNexo AG: lotes agricolas e inteligencia agronomica sobre datos reales.

El endpoint que hace el trabajo es ``POST /agro/lots/{id}/refresh``: baja la
serie historica y el pronostico de Open-Meteo para la coordenada del lote,
calcula los indicadores agronomicos y guarda tanto la serie como las
recomendaciones que se desprenden de ella.

Cada recomendacion se persiste con el ``payload`` de numeros que la justifica.
La idea es que un agronomo pueda discutirla, no solo acatarla.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from .. import agro, db
from ..audit import record_audit
from ..deps import CurrentUser, current_user, require_role
from ..schemas import (
    AgroAdvisoryOut,
    AgroDailyOut,
    AgroLotIn,
    AgroLotOut,
    AgroLotUpdateIn,
    AgroRefreshOut,
    AgroSummaryOut,
)
from ..subscriptions import (
    module_included_by_plan,
    require_active_subscription,
    sync_modules,
)

router = APIRouter(prefix="/agro", tags=["agro"])

MODULE_KEY = "agro"
HISTORY_DAYS_DEFAULT = 120
FORECAST_DAYS = 7


async def _module_status(org_id: UUID) -> str | None:
    return await db.pool().fetchval(
        "SELECT status FROM organization_modules WHERE org_id=$1 AND module_key=$2",
        org_id,
        MODULE_KEY,
    )


async def require_agro_module(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """Exige licencia activa y el modulo agro habilitado para la organizacion.

    Si el plan incluye el modulo pero la fila todavia figura suspendida, se
    sincroniza en el momento. Pasa cuando la organizacion nunca paso por
    ``GET /modules/me``, que es el otro lugar donde corre ``sync_modules``: sin
    esto, entrar directo a EcoNexo AG daria 402 con una licencia que si lo
    habilita.
    """
    await require_active_subscription(user.org_id)
    estado = await _module_status(user.org_id)
    if estado not in {"active", "trial"} and await module_included_by_plan(user.org_id, MODULE_KEY):
        await sync_modules(user.org_id, user.id)
        estado = await _module_status(user.org_id)
    if estado not in {"active", "trial"}:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "EcoNexo AG no está habilitado para tu organización. "
            "Pedí la activación del módulo desde Admin Core > Suscripción.",
        )
    return user


def _decode(value: Any) -> dict:
    if isinstance(value, str):
        return json.loads(value)
    return value or {}


def _advisory_out(row: Any) -> AgroAdvisoryOut:
    datos = dict(row)
    datos["payload"] = _decode(datos.get("payload"))
    return AgroAdvisoryOut(**datos)


async def _lot_or_404(lot_id: UUID, org_id: UUID) -> Any:
    row = await db.pool().fetchrow(
        """
        SELECT l.*, ST_Y(l.location::geometry) AS lat, ST_X(l.location::geometry) AS lon
        FROM agro_lots l WHERE l.id=$1 AND l.org_id=$2
        """,
        lot_id,
        org_id,
    )
    if row is None:
        raise HTTPException(404, "Lote no encontrado")
    return row


async def _lot_out(row: Any) -> AgroLotOut:
    crop = agro.CROPS.get(row["crop_key"])
    ultimo = await db.pool().fetchrow(
        """
        SELECT gdd_accum, stage_name FROM agro_lot_daily
        WHERE lot_id=$1 AND NOT is_forecast
        ORDER BY day DESC LIMIT 1
        """,
        row["id"],
    )
    balance = await db.pool().fetchval(
        """
        SELECT round(sum(balance_mm)::numeric, 1) FROM agro_lot_daily
        WHERE lot_id=$1 AND day > current_date - 14 AND day <= current_date
        """,
        row["id"],
    )
    avisos = await db.pool().fetch(
        """
        SELECT a.*, l.name AS lot_name FROM agro_advisories a
        JOIN agro_lots l ON l.id=a.lot_id
        WHERE a.lot_id=$1 AND (a.valid_to IS NULL OR a.valid_to > now())
        ORDER BY CASE a.level WHEN 'alto' THEN 0 WHEN 'medio' THEN 1 ELSE 2 END,
                 a.created_at DESC
        LIMIT 12
        """,
        row["id"],
    )
    return AgroLotOut(
        id=row["id"],
        name=row["name"],
        crop_key=row["crop_key"],
        crop_name=crop.name if crop else row["crop_key"],
        sowing_date=row["sowing_date"],
        area_ha=float(row["area_ha"]),
        lat=float(row["lat"]),
        lon=float(row["lon"]),
        zone_id=row["zone_id"],
        notes=row["notes"],
        is_active=row["is_active"],
        last_refresh_at=row["last_refresh_at"],
        last_refresh_status=row["last_refresh_status"],
        stage_name=ultimo["stage_name"] if ultimo else None,
        gdd_accum=float(ultimo["gdd_accum"]) if ultimo and ultimo["gdd_accum"] is not None else None,
        balance_14d_mm=float(balance) if balance is not None else None,
        advisories=[_advisory_out(a) for a in avisos],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# --------------------------------------------------------------------------
# Catalogo y resumen
# --------------------------------------------------------------------------

@router.get("/crops")
async def crops(user: CurrentUser = Depends(require_agro_module)) -> list[dict]:
    """Catalogo de cultivos con sus coeficientes a la vista."""
    del user
    return agro.catalog()


@router.get("/summary", response_model=AgroSummaryOut)
async def summary(user: CurrentUser = Depends(require_agro_module)) -> AgroSummaryOut:
    row = await db.pool().fetchrow(
        """
        SELECT
          count(*)::int AS lots_total,
          count(*) FILTER (WHERE is_active)::int AS lots_active,
          COALESCE(sum(area_ha) FILTER (WHERE is_active), 0)::float AS area_ha,
          count(*) FILTER (WHERE last_refresh_at IS NULL)::int AS lots_never_refreshed,
          max(last_refresh_at) AS last_refresh_at
        FROM agro_lots WHERE org_id=$1
        """,
        user.org_id,
    )
    avisos = await db.pool().fetchrow(
        """
        SELECT
          count(*) FILTER (WHERE level='alto')::int AS altos,
          count(*) FILTER (WHERE level='medio')::int AS medios
        FROM agro_advisories
        WHERE org_id=$1 AND (valid_to IS NULL OR valid_to > now())
        """,
        user.org_id,
    )
    return AgroSummaryOut(
        **dict(row),
        advisories_high=avisos["altos"],
        advisories_medium=avisos["medios"],
    )


# --------------------------------------------------------------------------
# ABM de lotes
# --------------------------------------------------------------------------

@router.get("/lots", response_model=list[AgroLotOut])
async def list_lots(
    include_inactive: bool = Query(default=False),
    user: CurrentUser = Depends(require_agro_module),
) -> list[AgroLotOut]:
    rows = await db.pool().fetch(
        """
        SELECT l.*, ST_Y(l.location::geometry) AS lat, ST_X(l.location::geometry) AS lon
        FROM agro_lots l
        WHERE l.org_id=$1 AND ($2 OR l.is_active)
        ORDER BY l.is_active DESC, l.name
        """,
        user.org_id,
        include_inactive,
    )
    return [await _lot_out(row) for row in rows]


@router.post("/lots", response_model=AgroLotOut, status_code=201)
async def create_lot(
    body: AgroLotIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> AgroLotOut:
    await require_agro_module(user)
    agro.crop_or_404(body.crop_key)
    if body.zone_id is not None:
        existe = await db.pool().fetchval(
            "SELECT EXISTS(SELECT 1 FROM risk_zones WHERE id=$1 AND org_id=$2)",
            body.zone_id,
            user.org_id,
        )
        if not existe:
            raise HTTPException(404, "Zona no encontrada")
    duplicado = await db.pool().fetchval(
        "SELECT EXISTS(SELECT 1 FROM agro_lots WHERE org_id=$1 AND lower(name)=lower($2))",
        user.org_id,
        body.name.strip(),
    )
    if duplicado:
        raise HTTPException(409, "Ya existe un lote con ese nombre")
    row = await db.pool().fetchrow(
        """
        INSERT INTO agro_lots
          (org_id,name,crop_key,sowing_date,area_ha,location,zone_id,notes,created_by)
        VALUES ($1,$2,$3,$4,$5,ST_MakePoint($7,$6)::geography,$8,$9,$10)
        RETURNING id
        """,
        user.org_id, body.name.strip(), body.crop_key, body.sowing_date,
        body.area_ha, body.lat, body.lon, body.zone_id,
        body.notes.strip() if body.notes else None, user.id,
    )
    await record_audit(
        org_id=user.org_id, user_id=user.id, action="agro_create_lot",
        resource="agro_lot", resource_id=row["id"],
        metadata={"crop": body.crop_key, "area_ha": body.area_ha},
    )
    return await _lot_out(await _lot_or_404(row["id"], user.org_id))


@router.patch("/lots/{lot_id}", response_model=AgroLotOut)
async def update_lot(
    lot_id: UUID,
    body: AgroLotUpdateIn,
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> AgroLotOut:
    await require_agro_module(user)
    if not body.model_fields_set:
        raise HTTPException(422, "No se recibieron cambios")
    await _lot_or_404(lot_id, user.org_id)
    if body.crop_key is not None:
        agro.crop_or_404(body.crop_key)
    await db.pool().execute(
        """
        UPDATE agro_lots SET
          name=COALESCE($3,name),
          crop_key=COALESCE($4,crop_key),
          sowing_date=CASE WHEN $5::boolean THEN $6::date ELSE sowing_date END,
          area_ha=COALESCE($7,area_ha),
          notes=CASE WHEN $8::boolean THEN $9::text ELSE notes END,
          is_active=COALESCE($10,is_active)
        WHERE id=$1 AND org_id=$2
        """,
        lot_id, user.org_id,
        body.name.strip() if body.name else None,
        body.crop_key,
        "sowing_date" in body.model_fields_set, body.sowing_date,
        body.area_ha,
        "notes" in body.model_fields_set,
        body.notes.strip() if body.notes else None,
        body.is_active,
    )
    # Cambiar cultivo o fecha de siembra invalida la serie: los grados dia
    # acumulados y las etapas se calcularon con los parametros anteriores.
    if body.crop_key is not None or "sowing_date" in body.model_fields_set:
        await db.pool().execute("DELETE FROM agro_lot_daily WHERE lot_id=$1", lot_id)
        await db.pool().execute("DELETE FROM agro_advisories WHERE lot_id=$1", lot_id)
        await db.pool().execute(
            "UPDATE agro_lots SET last_refresh_at=NULL, last_refresh_status=NULL WHERE id=$1",
            lot_id,
        )
    await record_audit(
        org_id=user.org_id, user_id=user.id, action="agro_update_lot",
        resource="agro_lot", resource_id=lot_id,
        metadata=body.model_dump(exclude_unset=True, mode="json"),
    )
    return await _lot_out(await _lot_or_404(lot_id, user.org_id))


@router.delete("/lots/{lot_id}", status_code=204, response_class=Response)
async def delete_lot(
    lot_id: UUID,
    user: CurrentUser = Depends(require_role("admin")),
) -> Response:
    await require_agro_module(user)
    await _lot_or_404(lot_id, user.org_id)
    await db.pool().execute("DELETE FROM agro_lots WHERE id=$1 AND org_id=$2", lot_id, user.org_id)
    await record_audit(
        org_id=user.org_id, user_id=user.id, action="agro_delete_lot",
        resource="agro_lot", resource_id=lot_id, metadata={},
    )
    return Response(status_code=204)


# --------------------------------------------------------------------------
# Procesamiento de datos reales
# --------------------------------------------------------------------------

def _build_advisories(crop: agro.Crop, observado: list[agro.DailyPoint],
                      pronostico_diario: list[dict], pronostico_horario: list[dict],
                      ) -> list[dict[str, Any]]:
    """Traduce los indicadores a recomendaciones accionables.

    ``observado`` son solo los dias con dato medido, sin el tramo de
    pronostico. La distincion importa: los indicadores retrospectivos (balance
    hidrico, etapa fenologica) tienen que describir donde esta el lote hoy, no
    donde va a estar en una semana. Mezclarlos hacia que la ficha del lote y la
    recomendacion informaran etapas distintas para el mismo lote.
    """
    avisos: list[dict[str, Any]] = []
    hoy = datetime.now(timezone.utc)

    helada = agro.frost_outlook(crop, pronostico_diario)
    if helada["eventos"]:
        primero = helada["eventos"][0]
        avisos.append({
            "kind": "helada", "level": helada["nivel"],
            "title": f"Riesgo de helada el {primero['dia'].isoformat()}",
            "detail": (
                f"Mínima pronosticada de {primero['tmin']} °C frente a un umbral de daño de "
                f"{crop.frost_c} °C para {crop.name}. La temperatura es del aire a 2 m: "
                "sobre el suelo y en el canopeo bajo puede ser varios grados menor."
            ),
            "payload": {**helada, "eventos": [
                {**e, "dia": e["dia"].isoformat()} for e in helada["eventos"]]},
            "valid_to": hoy + timedelta(days=FORECAST_DAYS),
        })

    riego = agro.irrigation_outlook(observado)
    if riego["nivel"] in {"medio", "alto"}:
        avisos.append({
            "kind": "riego", "level": riego["nivel"],
            "title": f"Déficit hídrico de {abs(riego['balance_mm'])} mm en {riego['dias']} días",
            "detail": (
                f"Llovieron {riego['lluvia_mm']} mm contra una demanda del cultivo de "
                f"{riego['etc_mm']} mm (ET0 FAO-56 por el coeficiente de la etapa). "
                "Es un balance climático: no considera el agua almacenada en el perfil "
                "ni la profundidad de raíces."
            ),
            "payload": riego,
            "valid_to": hoy + timedelta(days=3),
        })

    ventanas = agro.spray_windows(pronostico_horario)
    if ventanas:
        primera = ventanas[0]
        avisos.append({
            "kind": "pulverizacion", "level": "bajo",
            "title": (
                f"Ventana de pulverización el {primera.start.strftime('%d/%m')} "
                f"de {primera.start.strftime('%H:%M')} a {primera.end.strftime('%H:%M')}"
            ),
            "detail": (
                f"{primera.hours} h con viento entre {primera.wind_min} y {primera.wind_max} km/h "
                f"y delta-T entre {primera.delta_t_min} y {primera.delta_t_max} °C. "
                "No reemplaza lo que indique la etiqueta del producto."
            ),
            "payload": {"ventanas": [
                {"desde": v.start.isoformat(), "hasta": v.end.isoformat(), "horas": v.hours,
                 "delta_t_min": v.delta_t_min, "delta_t_max": v.delta_t_max,
                 "viento_min": v.wind_min, "viento_max": v.wind_max}
                for v in ventanas[:6]
            ]},
            "valid_to": hoy + timedelta(days=3),
        })

    enfermedad = agro.disease_pressure(crop, pronostico_horario[:72])
    if enfermedad["nivel"] in {"medio", "alto"}:
        avisos.append({
            "kind": "enfermedad", "level": enfermedad["nivel"],
            "title": f"Presión de {enfermedad['enfermedad']}",
            "detail": (
                f"{enfermedad['racha_horas']} h seguidas con humedad relativa sobre "
                f"{enfermedad['umbral_hr']} % y temperatura entre {enfermedad['rango_c'][0]} y "
                f"{enfermedad['rango_c'][1]} °C. La humedad relativa se usa como sustituto del "
                "mojado foliar, que no se mide en el lote."
            ),
            "payload": enfermedad,
            "valid_to": hoy + timedelta(days=3),
        })

    calor = agro.heat_outlook(crop, pronostico_diario)
    if calor["eventos"]:
        avisos.append({
            "kind": "estres_termico", "level": calor["nivel"],
            "title": f"{len(calor['eventos'])} día(s) por encima de {crop.heat_c} °C",
            "detail": (
                "Temperaturas máximas en el rango de estrés térmico para "
                f"{crop.name}. Afecta cuaje y llenado si coincide con etapas críticas."
            ),
            "payload": {**calor, "eventos": [
                {**e, "dia": e["dia"].isoformat()} for e in calor["eventos"]]},
            "valid_to": hoy + timedelta(days=FORECAST_DAYS),
        })

    if observado and not crop.perennial:
        ultimo = observado[-1]
        if ultimo.stage_name:
            avisos.append({
                "kind": "fenologia", "level": "bajo",
                "title": f"Etapa estimada: {ultimo.stage_name}",
                "detail": (
                    f"{ultimo.gdd_accum} grados día acumulados desde la siembra, con base "
                    f"{crop.t_base} °C y techo {crop.t_cap} °C. La etapa es una estimación "
                    "térmica: no reemplaza la observación a campo."
                ),
                "payload": {"gdd_accum": ultimo.gdd_accum, "stage_key": ultimo.stage_key,
                            "t_base": crop.t_base, "t_cap": crop.t_cap},
                "valid_to": hoy + timedelta(days=7),
            })
    return avisos


@router.post("/lots/{lot_id}/refresh", response_model=AgroRefreshOut)
async def refresh_lot(
    lot_id: UUID,
    history_days: int = Query(default=HISTORY_DAYS_DEFAULT, ge=14, le=365),
    user: CurrentUser = Depends(require_role("admin", "operador")),
) -> AgroRefreshOut:
    """Baja datos reales, recalcula la serie y regenera las recomendaciones."""
    await require_agro_module(user)
    lote = await _lot_or_404(lot_id, user.org_id)
    crop = agro.crop_or_404(lote["crop_key"])
    lat, lon = float(lote["lat"]), float(lote["lon"])
    hoy = agro.today_local()

    desde = lote["sowing_date"] or (hoy - timedelta(days=history_days))
    if crop.perennial or desde > hoy:
        desde = hoy - timedelta(days=history_days)
    desde = max(desde, hoy - timedelta(days=365))

    try:
        historia = await agro.fetch_history(lat, lon, desde, hoy - timedelta(days=1))
        pron_diario, pron_horario = await agro.fetch_forecast(lat, lon, FORECAST_DAYS)
    except agro.OpenMeteoError as exc:
        # La causa concreta viaja al usuario y queda en el lote: "no se pudo"
        # no permite distinguir un limite de consultas de un corte de red.
        motivo = str(exc)
        await db.pool().execute(
            "UPDATE agro_lots SET last_refresh_at=now(), last_refresh_status=$2 WHERE id=$1",
            lot_id, f"error: {motivo[:200]}",
        )
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, motivo) from exc
    except Exception as exc:
        await db.pool().execute(
            "UPDATE agro_lots SET last_refresh_at=now(), last_refresh_status=$2 WHERE id=$1",
            lot_id, f"error: {type(exc).__name__}: {str(exc)[:160]}",
        )
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Falló la consulta meteorológica ({type(exc).__name__}). Reintentá en unos minutos.",
        ) from exc

    dias_archivo = {d["day"] for d in historia}
    serie = agro.build_daily_series(crop, historia + pron_diario)
    if not serie:
        raise HTTPException(502, "Open-Meteo no devolvió días utilizables para este lote")
    observado = [p for p in serie if p.day in dias_archivo]
    dias_pronostico = {p.day for p in serie if p.day not in dias_archivo}

    registros = [
        (lot_id, user.org_id, p.day, p.tmax, p.tmin, p.precipitation_mm, p.et0_mm,
         p.kc, p.etc_mm, p.gdd, p.gdd_accum, p.balance_mm, p.balance_accum_mm,
         p.stage_key, p.stage_name, "open-meteo", p.day in dias_pronostico)
        for p in serie
    ]
    avisos = _build_advisories(crop, observado, pron_diario, pron_horario)

    async with db.pool().acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM agro_lot_daily WHERE lot_id=$1", lot_id)
            await conn.copy_records_to_table(
                "agro_lot_daily",
                records=registros,
                columns=["lot_id", "org_id", "day", "tmax_c", "tmin_c", "precipitation_mm",
                         "et0_mm", "kc", "etc_mm", "gdd", "gdd_accum", "balance_mm",
                         "balance_accum_mm", "stage_key", "stage_name", "source", "is_forecast"],
            )
            # Las recomendaciones vigentes se reemplazan; el historico anterior
            # queda cerrado con valid_to para no perder la trazabilidad.
            await conn.execute(
                "UPDATE agro_advisories SET valid_to=now() WHERE lot_id=$1 "
                "AND (valid_to IS NULL OR valid_to > now())",
                lot_id,
            )
            for aviso in avisos:
                await conn.execute(
                    """
                    INSERT INTO agro_advisories
                      (org_id,lot_id,kind,level,title,detail,payload,valid_to)
                    VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
                    """,
                    user.org_id, lot_id, aviso["kind"], aviso["level"], aviso["title"],
                    aviso["detail"], json.dumps(aviso["payload"], ensure_ascii=False, default=str),
                    aviso["valid_to"],
                )
            await conn.execute(
                "UPDATE agro_lots SET last_refresh_at=now(), last_refresh_status=$2 WHERE id=$1",
                lot_id, f"ok: {len(serie)} días",
            )

    vigentes = await db.pool().fetch(
        """
        SELECT a.*, l.name AS lot_name FROM agro_advisories a
        JOIN agro_lots l ON l.id=a.lot_id
        WHERE a.lot_id=$1 AND (a.valid_to IS NULL OR a.valid_to > now())
        ORDER BY CASE a.level WHEN 'alto' THEN 0 WHEN 'medio' THEN 1 ELSE 2 END
        """,
        lot_id,
    )
    ultimo_real = observado[-1] if observado else serie[-1]
    await record_audit(
        org_id=user.org_id, user_id=user.id, action="agro_refresh_lot",
        resource="agro_lot", resource_id=lot_id,
        metadata={"dias": len(serie), "avisos": len(avisos), "fuente": "open-meteo"},
    )
    return AgroRefreshOut(
        lot_id=lot_id,
        days_processed=len(serie),
        history_days=len(observado),
        forecast_days=len(serie) - len(observado),
        gdd_accum=ultimo_real.gdd_accum,
        stage_name=ultimo_real.stage_name,
        advisories=[_advisory_out(a) for a in vigentes],
        sources=[
            "Open-Meteo Archive (reanálisis ERA5) · histórico diario",
            "Open-Meteo Forecast · pronóstico diario y horario",
            "ET0 FAO-56 Penman-Monteith calculada por Open-Meteo",
        ],
        detail=(
            f"{len(serie)} días procesados para {crop.name}: "
            f"{len(historia)} de histórico y {len(pron_diario)} de pronóstico."
        ),
    )


@router.get("/lots/{lot_id}/series", response_model=list[AgroDailyOut])
async def lot_series(
    lot_id: UUID,
    days: int = Query(default=90, ge=7, le=400),
    user: CurrentUser = Depends(require_agro_module),
) -> list[AgroDailyOut]:
    await _lot_or_404(lot_id, user.org_id)
    rows = await db.pool().fetch(
        """
        SELECT day, tmax_c, tmin_c, precipitation_mm, et0_mm, kc, etc_mm, gdd,
               gdd_accum, balance_mm, balance_accum_mm, stage_key, stage_name, is_forecast
        FROM agro_lot_daily
        WHERE lot_id=$1 AND day >= current_date - $2::int
        ORDER BY day
        """,
        lot_id,
        days,
    )
    return [AgroDailyOut(**dict(row)) for row in rows]


@router.get("/advisories", response_model=list[AgroAdvisoryOut])
async def advisories(
    level: str | None = Query(default=None, pattern="^(bajo|medio|alto)$"),
    limit: int = Query(default=100, ge=1, le=300),
    user: CurrentUser = Depends(require_agro_module),
) -> list[AgroAdvisoryOut]:
    rows = await db.pool().fetch(
        """
        SELECT a.*, l.name AS lot_name FROM agro_advisories a
        JOIN agro_lots l ON l.id=a.lot_id
        WHERE a.org_id=$1 AND (a.valid_to IS NULL OR a.valid_to > now())
          AND ($2::text IS NULL OR a.level=$2)
        ORDER BY CASE a.level WHEN 'alto' THEN 0 WHEN 'medio' THEN 1 ELSE 2 END,
                 a.created_at DESC
        LIMIT $3
        """,
        user.org_id,
        level,
        limit,
    )
    return [_advisory_out(row) for row in rows]
