"""Pronósticos, verificación independiente y gestión de modelos por tenant."""
from typing import Literal
from uuid import UUID

import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator

from .. import db
from ..deps import CurrentUser, current_user, require_role
from ..predictive_service import decode, evaluate_org, issue_forecasts, train_org
from ..rate_limit import enforce_rate_limit

router = APIRouter(prefix="/predictions", tags=["predictions"])
Horizon = Literal[6, 24, 72]
Hazard = Literal["fire", "hydric", "health_heat", "health_air"]


def checked_horizon(horizon_hours: int = Query(24, description="Horizonte: 6, 24 o 72 horas")) -> int:
    if horizon_hours not in (6, 24, 72):
        raise HTTPException(422, "El horizonte debe ser 6, 24 o 72 horas")
    return horizon_hours


class ObservationIn(BaseModel):
    hazard: Hazard = "fire"
    device_id: UUID
    outcome: Literal["event", "no_event"]
    start_at: AwareDatetime
    end_at: AwareDatetime
    source: Literal["field_report", "official_record", "sensor_verified"]
    reference: str = Field(min_length=3, max_length=160)
    notes: str = Field(min_length=10, max_length=2000)
    coverage_verified: Literal[True]

    @field_validator("reference", "notes", mode="before")
    @classmethod
    def trim_evidence(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def dates(self):
        if self.end_at < self.start_at:
            raise ValueError("La fecha final debe ser posterior a la inicial")
        if self.outcome == "event" and self.end_at != self.start_at:
            raise ValueError("Un incidente registra su instante de inicio")
        if self.outcome == "no_event" and self.end_at <= self.start_at:
            raise ValueError("La ausencia de incidente requiere un período verificado")
        if any(not text.strip() for text in (self.source, self.reference, self.notes)):
            raise ValueError("La fuente y referencia deben identificar evidencia real")
        return self


class TrainIn(BaseModel):
    hazard: Hazard = "fire"
    horizon_hours: Horizon = 24
    days: int = Field(default=180, ge=30, le=730)


class DeploymentIn(BaseModel):
    hazard: Hazard = "fire"
    horizon_hours: Horizon = 24
    model_id: UUID | None = None
    enabled: bool = False
    external_weather_consent: bool = False


@router.get("")
async def list_predictions(horizon_hours: int = Depends(checked_horizon), limit: int = Query(100, ge=1, le=500), hazard: Hazard = "fire",
                           user: CurrentUser = Depends(current_user)):
    rows = await db.pool().fetch("""SELECT * FROM predictions WHERE org_id=$1 AND horizon_hours=$2 AND hazard=$4
        ORDER BY issued_at DESC,id DESC LIMIT $3""", user.org_id, horizon_hours, limit, hazard)
    return [decode(row) for row in rows]


@router.post("/run")
async def run(request: Request, hazard: Hazard | None = None, horizon_hours: int | None = Query(None), user: CurrentUser = Depends(require_role("admin", "operador"))):
    if horizon_hours is not None and horizon_hours not in (6, 24, 72):
        raise HTTPException(422, "El horizonte debe ser 6, 24 o 72 horas")
    await enforce_rate_limit(request, bucket=f"predictive-run:{user.org_id}", limit=10, window_seconds=3600)
    try:
        return await issue_forecasts(user.org_id, user.id, hazard, horizon_hours)
    except (RuntimeError, TimeoutError, httpx.HTTPError) as exc:
        raise HTTPException(503, "No se pudo emitir el pronóstico. Revisá la fuente meteorológica y reintentá.") from exc


@router.get("/evaluation")
async def evaluate(horizon_hours: int = Depends(checked_horizon), days: int = Query(90, ge=1, le=730), hazard: Hazard = "fire",
                   user: CurrentUser = Depends(current_user)):
    return await evaluate_org(user.org_id, days, horizon_hours, hazard)


@router.get("/observations")
async def observations(limit: int = Query(100, ge=1, le=500), hazard: Hazard = "fire", user: CurrentUser = Depends(current_user)):
    return [dict(row) for row in await db.pool().fetch("SELECT * FROM predictive_observations WHERE org_id=$1 AND hazard=$3 ORDER BY verified_at DESC LIMIT $2", user.org_id, limit, hazard)]


@router.post("/observations", status_code=201)
async def observe(body: ObservationIn, user: CurrentUser = Depends(require_role("admin", "operador"))):
    try:
        async with db.pool().acquire() as conn:
            async with conn.transaction():
                device = await conn.fetchrow("SELECT id,ST_Y(location::geometry) AS lat,ST_X(location::geometry) AS lon FROM devices WHERE id=$1 AND org_id=$2 FOR UPDATE", body.device_id, user.org_id)
                if device is None:
                    raise HTTPException(404, "Nodo no encontrado en tu organización")
                now = await conn.fetchval("SELECT clock_timestamp()")
                if body.end_at > now:
                    raise HTTPException(422, "No se pueden verificar resultados futuros")
                conflict = await conn.fetchval("""SELECT EXISTS(SELECT 1 FROM predictive_observations
                    WHERE org_id=$1 AND device_id=$2 AND outcome<>$3
                    AND latitude=$6 AND longitude=$7 AND hazard=$8 AND
                    CASE WHEN $3='event' THEN start_at <= $4 AND end_at > $4
                         ELSE start_at >= $4 AND start_at < $5 END)""",
                    user.org_id, body.device_id, body.outcome, body.start_at, body.end_at, device["lat"], device["lon"], body.hazard)
                if conflict:
                    raise HTTPException(409, "La observación contradice evidencia ya verificada")
                row = await conn.fetchrow("""INSERT INTO predictive_observations(org_id,device_id,outcome,start_at,end_at,source,reference,notes,verified_by,latitude,longitude,verified_at,hazard)
                  VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,clock_timestamp(),$12) RETURNING *""",
                    user.org_id, body.device_id, body.outcome, body.start_at, body.end_at,
                    body.source.strip(), body.reference.strip(), body.notes.strip(), user.id, device["lat"], device["lon"], body.hazard)
                await conn.execute("INSERT INTO audit_events(org_id,user_id,action,resource,resource_id) VALUES($1,$2,'predictive_verify','predictive_observation',$3)", user.org_id, user.id, row["id"])
                return dict(row)
    except asyncpg.UniqueViolationError as exc:
        raise HTTPException(409, "Esa fuente y referencia ya están registradas") from exc


@router.post("/models/train", status_code=201)
async def train(body: TrainIn, request: Request, user: CurrentUser = Depends(require_role("admin"))):
    await enforce_rate_limit(request, bucket=f"predictive-train:{user.org_id}", limit=2, window_seconds=3600)
    return await train_org(user.org_id, user.id, body.days, body.horizon_hours, body.hazard)


@router.get("/settings")
async def settings(user: CurrentUser = Depends(current_user)):
    return [dict(row) for row in await db.pool().fetch("SELECT * FROM predictive_settings WHERE org_id=$1 ORDER BY horizon_hours", user.org_id)]


@router.post("/models/deploy")
async def deploy(body: DeploymentIn, user: CurrentUser = Depends(require_role("admin"))):
    if body.enabled and not body.external_weather_consent:
        raise HTTPException(422, "Habilitar pronósticos requiere autorizar el envío de coordenadas de nodos a Open-Meteo")
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            if body.model_id:
                model = await conn.fetchrow("SELECT * FROM predictive_models WHERE id=$1 AND org_id=$2 AND horizon_hours=$3 AND hazard=$4", body.model_id, user.org_id, body.horizon_hours, body.hazard)
                if model is None:
                    raise HTTPException(404, "Modelo no encontrado para este territorio y horizonte")
                if not model["eligible"]:
                    raise HTTPException(409, "El modelo no supera las puertas de evaluación temporal")
            await conn.execute("""INSERT INTO predictive_settings(org_id,horizon_hours,active_model_id,enabled,hazard)
                VALUES($1,$2,$3,$4,$5) ON CONFLICT(org_id,horizon_hours,hazard) DO UPDATE
                SET active_model_id=EXCLUDED.active_model_id,enabled=EXCLUDED.enabled""",
                user.org_id, body.horizon_hours, body.model_id, body.enabled, body.hazard)
            await conn.execute("INSERT INTO audit_events(org_id,user_id,action,resource,resource_id,metadata) VALUES($1,$2,'predictive_deploy','predictive_model',$3,jsonb_build_object('horizon_hours',$4::int,'enabled',$5::boolean,'external_weather_consent',$6::boolean,'provider','open-meteo','hazard',$7::text))",
                               user.org_id, user.id, body.model_id, body.horizon_hours, body.enabled, body.external_weather_consent, body.hazard)
    return dict(hazard=body.hazard, model_id=body.model_id, horizon_hours=body.horizon_hours, enabled=body.enabled,
                mode="shadow", automatic_response=False)
