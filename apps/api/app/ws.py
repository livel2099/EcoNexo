"""Feed en tiempo real (WebSocket) alimentado por el bus MQTT.

El API se suscribe a los topics internos que publican los microservicios
(readings normalizados y alertas) y los reenvia por WebSocket al dashboard,
scopeados por organizacion.
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

# Topics internos del bus (publicados por ingest/api).
TOPIC_READINGS = "econexo/internal/+/readings"
TOPIC_ALERTS = "econexo/internal/+/alerts"


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
    s = get_settings()
    if not s.mqtt_enabled:
        log.info("MQTT bridge deshabilitado por configuración")
        await stop.wait()
        return
    while not stop.is_set():
        try:
            async with aiomqtt.Client(hostname=s.mqtt_host, port=s.mqtt_port) as client:
                await client.subscribe(TOPIC_READINGS)
                await client.subscribe(TOPIC_ALERTS)
                log.info("MQTT bridge conectado a %s:%s", s.mqtt_host, s.mqtt_port)
                async for msg in client.messages:
                    await _dispatch(str(msg.topic), msg.payload)
        except Exception as exc:  # broker caido / arrancando
            log.warning("MQTT bridge reintentando: %s", exc)
            await asyncio.sleep(3)


async def _dispatch(topic: str, payload: bytes) -> None:
    # topic: econexo/internal/{org_id}/{kind}
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
    """Publica en el bus MQTT (best-effort)."""
    s = get_settings()
    if not s.mqtt_enabled:
        return
    try:
        async with aiomqtt.Client(hostname=s.mqtt_host, port=s.mqtt_port) as client:
            await client.publish(topic, json.dumps(data, default=str))
    except Exception as exc:
        log.warning("publish fallo (%s): %s", topic, exc)
