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

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .config import get_settings
from .routers import alerts, auth, devices, kpis, orgs, reports, rules, satellite
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=s.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(devices.router)
app.include_router(alerts.router)
app.include_router(rules.router)
app.include_router(reports.router)
app.include_router(kpis.router)
app.include_router(satellite.router)


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
