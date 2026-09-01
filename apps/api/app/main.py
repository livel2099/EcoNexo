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

from fastapi import Depends, FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .config import get_settings
from .routers import (
    admin,
    agro,
    alerts,
    auth,
    copernicus,
    devices,
    environment,
    foi,
    impact_reports,
    kpis,
    modules,
    notifications,
    orgs,
    pipeline,
    platform,
    reports,
    rules,
    satellite,
    subscriptions,
    territory,
    zones,
)
from .platform_admin import ensure_platform_admin
from .security import decode_token
from .telemetry_pipeline import pipeline_scheduler
from .ws import manager, mqtt_bridge

logging.basicConfig(level=logging.INFO)

# Antes se definia despues de `lifespan`, que lo usa. Funcionaba porque
# `lifespan` corre en runtime, pero cualquier reordenamiento lo rompia.
s = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cada ciclo de vida conserva su propio evento: evita tareas heredadas en reinicios.
    stop = asyncio.Event()
    await db.connect()
    # ensure_platform_admin existia desde el bootstrap del proyecto pero no la
    # invocaba nadie: la cuenta de administracion general nunca se creaba y el
    # login respondia "Credenciales invalidas" con la configuracion correcta.
    # Es idempotente y no hace nada si PLATFORM_ADMIN_BOOTSTRAP_ENABLED es false.
    try:
        await ensure_platform_admin()
    except Exception:
        # Un fallo aca no puede impedir que la API atienda: el resto del sistema
        # funciona sin la cuenta de plataforma. Se registra completo para que no
        # vuelva a pasar en silencio.
        logging.getLogger("econexo.api").exception(
            "No se pudo asegurar el administrador general"
        )
    workers = [asyncio.create_task(mqtt_bridge(stop), name="mqtt-bridge")]
    if s.pipeline_scheduler_enabled:
        workers.append(
            asyncio.create_task(pipeline_scheduler(stop), name="telemetry-pipeline-scheduler")
        )
    try:
        yield
    finally:
        stop.set()
        for worker in workers:
            worker.cancel()
        for worker in workers:
            with contextlib.suppress(asyncio.CancelledError):
                await worker
        await db.disconnect()


app = FastAPI(
    title="EcoNexo API",
    description="Inteligencia bioclimatica activa — sistema de decision en tiempo real.",
    version="0.1.0",
    lifespan=lifespan,
)


class UnhandledErrorMiddleware:
    """Convierte errores no controlados en 500 JSON *dentro* del stack CORS.

    Sin esto el 500 lo emite ``ServerErrorMiddleware``, que corre por fuera de
    ``CORSMiddleware``: la respuesta sale sin ``Access-Control-Allow-Origin`` y
    el navegador reporta un falso error de CORS en vez del error real.

    Es ASGI puro a proposito. ``BaseHTTPMiddleware`` propaga sus propios
    ``anyio.EndOfStream`` en lugar de la excepcion original, y el traceback
    que queda en el log no dice nada sobre la causa real.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logging.getLogger("econexo.api").exception(
                "Error no controlado en %s %s",
                scope.get("method", "?"),
                scope.get("path", "?"),
            )
            if response_started:
                # Ya se enviaron headers: no se puede reemplazar la respuesta.
                raise
            response = JSONResponse(
                status_code=500, content={"detail": "Error interno del servidor"}
            )
            await response(scope, receive, send)


# El orden importa: el ultimo middleware agregado es el mas externo, por lo que
# CORSMiddleware debe registrarse despues para poder anotar los 500 anteriores.
app.add_middleware(UnhandledErrorMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=s.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agro.router)
app.include_router(foi.router)
app.include_router(orgs.router)
app.include_router(devices.router)
app.include_router(alerts.router)
app.include_router(rules.router)
app.include_router(reports.router)
app.include_router(kpis.router)
app.include_router(satellite.router)
app.include_router(copernicus.router)
app.include_router(environment.router)
app.include_router(zones.router)
app.include_router(pipeline.router)
app.include_router(territory.router)
app.include_router(impact_reports.router)
app.include_router(modules.router)
app.include_router(subscriptions.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(platform.router)


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("econexo.api").exception(
        "Error no controlado en %s %s", request.method, request.url.path, exc_info=exc
    )
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "service": "econexo-api", "territory": "Misiones"}


@app.get("/ready", tags=["meta"])
async def ready() -> JSONResponse:
    """Readiness real: base accesible, PostGIS cargado y guarda territorial viva.

    El panel publico de Estado consulta este endpoint. Mientras no existio,
    reportaba "Readiness incompleto" de forma permanente aunque todo estuviera
    funcionando.
    """
    checks: dict[str, bool] = {"database": False, "postgis": False, "territory_guard": False}
    try:
        pool = db.pool()
        checks["database"] = bool(await pool.fetchval("SELECT true"))
        # to_regproc devuelve NULL con funciones sobrecargadas como ST_MakePoint,
        # asi que se consultan los catalogos directamente.
        checks["postgis"] = bool(
            await pool.fetchval("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis')")
        )
        checks["territory_guard"] = bool(
            await pool.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname='econexo_inside_misiones')"
            )
        )
    except Exception as exc:
        logging.getLogger("econexo.api").warning("Readiness incompleto: %s", exc)

    ok = all(checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "degraded", "checks": checks},
    )


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str = Query(default="")) -> None:
    """Feed en vivo por organizacion. Auth via ?token=<jwt>."""
    payload = decode_token(token)
    # Un token ciudadano valida la firma pero no trae org_id: sin este chequeo
    # el handler explotaba con KeyError en vez de cerrar el socket.
    org_id = str(payload.get("org_id") or "") if payload else ""
    if not org_id:
        await websocket.close(code=4401)
        return
    await manager.connect(org_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keepalive; el server solo emite
    except WebSocketDisconnect:
        pass
    finally:
        # En finally para que un error inesperado tampoco deje la conexion
        # registrada en el manager y transmitiendo a un socket muerto.
        manager.disconnect(org_id, websocket)
