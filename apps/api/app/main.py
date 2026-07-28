"""EcoNexo API core (FastAPI).

Sistema de decision en tiempo real: auth, orgs, dispositivos, alertas,
reglas, reportes ciudadanos, KPIs y feed WebSocket alimentado por MQTT.
OpenAPI/Swagger auto en /docs.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import JSONResponse

from . import db
from .config import get_settings
from .platform_admin import ensure_platform_admin
from .routers import (
    admin,
    alerts,
    auth,
    copernicus,
    devices,
    environment,
    impact_reports,
    kpis,
    modules,
    notifications,
    orgs,
    platform,
    pipeline,
    reports,
    rules,
    satellite,
    subscriptions,
    territory,
    zones,
)
from .security import decode_token
from .telemetry_pipeline import pipeline_scheduler
from .ws import manager, mqtt_bridge

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    insecure = settings.insecure_production_values()
    if insecure:
        raise RuntimeError(
            "Configuracion insegura para produccion: " + ", ".join(insecure)
        )

    await db.connect()
    await ensure_platform_admin()
    stop = asyncio.Event()
    bridge: asyncio.Task[None] | None = None
    if settings.mqtt_enabled:
        bridge = asyncio.create_task(mqtt_bridge(stop), name="mqtt-bridge")
    scheduler = asyncio.create_task(pipeline_scheduler(stop), name="telemetry-pipeline-scheduler")

    try:
        yield
    finally:
        stop.set()
        tasks = [task for task in (bridge, scheduler) if task is not None]
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await db.disconnect()


app = FastAPI(
    title="EcoNexo API",
    description="Inteligencia bioclimatica activa — sistema de decision en tiempo real.",
    version=get_settings().release_version,
    lifespan=lifespan,
)

s = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=s.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Copernicus-Layer", "X-Copernicus-Provider"],
    max_age=86400,
)

app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(copernicus.router)
app.include_router(platform.router)
app.include_router(pipeline.router)
app.include_router(devices.router)
app.include_router(alerts.router)
app.include_router(rules.router)
app.include_router(reports.router)
app.include_router(impact_reports.router)
app.include_router(kpis.router)
app.include_router(modules.router)
app.include_router(subscriptions.router)
app.include_router(notifications.router)
app.include_router(satellite.router)
app.include_router(territory.router)
app.include_router(environment.router)
app.include_router(zones.router)
app.include_router(admin.router)


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """Evita respuestas 500 opacas y conserva CORS para el frontend oficial."""
    logging.exception("Error no controlado en %s %s", request.method, request.url.path)
    response = JSONResponse(
        status_code=500,
        content={"detail": "Error interno de EcoNexo. El evento fue registrado."},
    )
    origin = request.headers.get("origin", "").rstrip("/")
    if origin and origin in s.cors_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.get("/", tags=["meta"], include_in_schema=False)
async def root() -> dict:
    return {
        "name": "EcoNexo API",
        "status": "online",
        "release": s.release_version,
        "environment": s.environment,
        "territory": "Misiones",
        "documentation": "/docs",
        "health": "/health",
        "readiness": "/ready",
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {
        "status": "ok",
        "service": "econexo-api",
        "release": s.release_version,
        "environment": s.environment,
        "territory": "Misiones",
        "features": {
            "mqtt": s.mqtt_enabled,
            "object_storage": s.s3_enabled,
            "anomaly_service": s.anomaly_enabled,
            "google_oauth": bool(s.google_audiences),
            "copernicus_default_mode": s.copernicus_mode_normalized,
            "copernicus_process_configured": s.copernicus_process_configured,
            "copernicus_wms_configured": bool(s.copernicus_instance_id.strip() or s.copernicus_wms_url.strip()),
            "telemetry_pipeline": True,
            "firms_inline": s.firms_inline_enabled,
            "firms_configured": bool(s.nasa_firms_key.strip()),
        },
        "frontend_origins": s.cors_list,
    }


@app.get("/ready", tags=["meta"])
async def ready(response: Response) -> dict:
    """Readiness para balanceadores y control previo a lanzamiento."""
    checks: dict[str, object] = {
        "database": False,
        "postgis": False,
        "territorial_guard": False,
        "territory_boundary": False,
        "official_georef_boundary": False,
        "external_data_audit": False,
        "external_data_clean": False,
        "external_rows": None,
        "official_boundary_required": s.is_production,
        "environment": s.environment,
        "territory": "Misiones",
        "municipalities": 79,
        "departments": 17,
    }
    try:
        row = await db.pool().fetchrow(
            """
            SELECT current_database() AS db,
                   postgis_version() AS postgis,
                   to_regprocedure('econexo_inside_misiones(geography)') IS NOT NULL AS guard,
                   to_regclass('public.territory_boundaries') IS NOT NULL AS boundary_table,
                   CASE WHEN to_regclass('public.territory_boundaries') IS NULL THEN false
                        ELSE EXISTS(SELECT 1 FROM territory_boundaries WHERE province='Misiones') END AS boundary_available,
                   CASE WHEN to_regclass('public.territory_boundaries') IS NULL THEN false
                        ELSE EXISTS(SELECT 1 FROM territory_boundaries WHERE province='Misiones' AND is_official) END AS official_boundary
            """
        )
        checks["database"] = bool(row and row["db"])
        checks["postgis"] = bool(row and row["postgis"])
        checks["territorial_guard"] = bool(row and row["guard"])
        checks["territory_boundary"] = bool(row and row["boundary_table"] and row["boundary_available"])
        checks["official_georef_boundary"] = bool(row and row["official_boundary"])
        try:
            external_rows = await db.pool().fetchval(
                "SELECT COALESCE(sum(external_rows), 0)::bigint FROM misiones_external_data_audit"
            )
            checks["external_data_audit"] = True
            checks["external_rows"] = int(external_rows or 0)
            checks["external_data_clean"] = checks["external_rows"] == 0
        except Exception:
            checks["external_data_audit"] = False
    except Exception as exc:  # pragma: no cover - depende del runtime
        logging.exception("Readiness de base de datos fallida")
        checks["error"] = exc.__class__.__name__
    ready_state = bool(
        checks["database"]
        and checks["postgis"]
        and checks["territorial_guard"]
        and checks["territory_boundary"]
        and checks["external_data_audit"]
        and checks["external_data_clean"]
        and (checks["official_georef_boundary"] or not s.is_production)
    )
    if not ready_state:
        response.status_code = 503
    return {"status": "ready" if ready_state else "not_ready", "checks": checks}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str = Query(default="")) -> None:
    """Feed en vivo por organizacion. Auth via ?token=<jwt>."""
    payload = decode_token(token)
    if payload is None:
        await websocket.close(code=4401)
        return
    row = await db.pool().fetchrow(
        """
        SELECT u.org_id, u.is_active, u.must_change_password,
               o.is_active AS organization_active
        FROM users u JOIN organizations o ON o.id=u.org_id
        WHERE u.id=$1::uuid AND u.org_id=$2::uuid
        """,
        payload["sub"],
        payload["org_id"],
    )
    if row is None or not row["is_active"] or not row["organization_active"] or row["must_change_password"]:
        await websocket.close(code=4403)
        return
    org_id = str(row["org_id"])
    await manager.connect(org_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keepalive; el server solo emite
    except WebSocketDisconnect:
        manager.disconnect(org_id, websocket)
