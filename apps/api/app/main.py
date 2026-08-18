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
from starlette.middleware.base import BaseHTTPMiddleware

from . import db
from .config import get_settings
from .routers import (
    admin,
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
from .security import decode_token
from .ws import manager, mqtt_bridge

logging.basicConfig(level=logging.INFO)
_stop = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    bridge = asyncio.create_task(mqtt_bridge(_stop))
    yield
    _stop.set()
    bridge.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await bridge
    await db.disconnect()


app = FastAPI(
    title="EcoNexo API",
    description="Inteligencia bioclimatica activa — sistema de decision en tiempo real.",
    version="0.1.0",
    lifespan=lifespan,
)

s = get_settings()


class UnhandledErrorMiddleware(BaseHTTPMiddleware):
    """Convierte errores no controlados en 500 JSON *dentro* del stack CORS.

    Sin esto el 500 lo emite ``ServerErrorMiddleware``, que corre por fuera de
    ``CORSMiddleware``: la respuesta sale sin ``Access-Control-Allow-Origin`` y
    el navegador reporta un falso error de CORS en vez del error real.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logging.getLogger("econexo.api").exception(
                "Error no controlado en %s %s", request.method, request.url.path, exc_info=exc
            )
            return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


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
    return {"status": "ok", "service": "econexo-api"}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str = Query(default="")) -> None:
    """Feed en vivo por organizacion. Auth via ?token=<jwt>."""
    payload = decode_token(token)
    if payload is None:
        await websocket.close(code=4401)
        return
    org_id = payload["org_id"]
    await manager.connect(org_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keepalive; el server solo emite
    except WebSocketDisconnect:
        manager.disconnect(org_id, websocket)
