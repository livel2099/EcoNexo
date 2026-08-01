"""Feed en tiempo real (WebSocket) alimentado por MQTT.

El adaptador MQTT puede deshabilitarse en despliegues iniciales de Render con
MQTT_ENABLED=false. El resto del API y los WebSockets siguen disponibles.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

import aiomqtt
from fastapi import WebSocket

from .config import get_settings

log = logging.getLogger("econexo.ws")

TOPIC_READINGS = "econexo/internal/+/readings"
TOPIC_ALERTS = "econexo/internal/+/alerts"
TOPIC_PIPELINE = "econexo/internal/+/pipeline"


class ConnectionManager:
    """WebSockets vivos agrupados por org_id."""

    def __init__(self) -> None:
        self._conns: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, org_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._conns[org_id].add(ws)

    def disconnect(self, org_id: str, ws: WebSocket) -> None:
        self._conns[org_id].discard(ws)

    async def broadcast(self, org_id: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._conns.get(org_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(org_id, ws)


manager = ConnectionManager()


async def mqtt_bridge(stop: asyncio.Event) -> None:
    """Puente MQTT -> WebSocket. Reconecta si el broker no esta listo."""
    settings = get_settings()
    if not settings.mqtt_enabled:
        log.info("MQTT deshabilitado por configuracion")
        return

    while not stop.is_set():
        try:
            async with aiomqtt.Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
            ) as client:
                await client.subscribe(TOPIC_READINGS)
                await client.subscribe(TOPIC_ALERTS)
                await client.subscribe(TOPIC_PIPELINE)
                log.info(
                    "MQTT bridge conectado a %s:%s",
                    settings.mqtt_host,
                    settings.mqtt_port,
                )
                async for msg in client.messages:
                    await _dispatch(str(msg.topic), msg.payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("MQTT bridge reintentando: %s", exc)
            try:
                await asyncio.wait_for(stop.wait(), timeout=5)
            except TimeoutError:
                pass


async def _dispatch(topic: str, payload: bytes) -> None:
    parts = topic.split("/")
    if len(parts) < 4:
        return
    org_id, kind = parts[2], parts[3]
    try:
        data = json.loads(payload.decode())
    except Exception:
        return
    await manager.broadcast(org_id, {"kind": kind, "data": data})


async def publish(topic: str, data: dict) -> None:
    """Entrega el evento al WebSocket local y, si existe, tambien a MQTT.

    Esto mantiene el Command Core en tiempo real en Render aunque MQTT_ENABLED
    sea false. MQTT queda como bus opcional para hardware y microservicios.
    """
    parts = topic.split("/")
    if len(parts) >= 4:
        await manager.broadcast(parts[2], {"kind": parts[3], "data": data})

    settings = get_settings()
    if not settings.mqtt_enabled:
        return
    try:
        async with aiomqtt.Client(
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
        ) as client:
            await client.publish(topic, json.dumps(data, default=str))
    except Exception as exc:
        log.warning("publish fallo (%s): %s", topic, exc)
