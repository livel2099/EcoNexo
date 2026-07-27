"""Historia de demo end-to-end de EcoNexo (make demo).

Secuencia (org forestal):
  satelite detecta foco -> 2 nodos confirman (spike de sensores) ->
  ciudadano reporta con foto -> correlacion espacial + score IA =
  alerta critica confianza alta -> operador confirma -> KPI se actualiza.

Se ejecuta dentro de la imagen api:  docker compose run --rm api python -m app.demo
Publica en el bus MQTT para que el dashboard lo muestre en vivo.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from . import db
from .correlation import Source
from .pipeline import anomaly_score, create_alert

NOW = datetime.now(timezone.utc)


async def main() -> None:
    await db.connect()
    p = db.pool()

    org = await p.fetchrow("SELECT id, name FROM organizations WHERE vertical='forestal'")
    org_id = org["id"]
    node = await p.fetchrow(
        "SELECT id, external_id, ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon "
        "FROM devices WHERE org_id=$1 ORDER BY external_id LIMIT 1",
        org_id,
    )
    lat, lon = node["lat"], node["lon"]
    print(f"\n=== DEMO EcoNexo — {org['name']} ===")
    print(f"Nodo epicentro: {node['external_id']} ({lat:.4f}, {lon:.4f})\n")

    # 1) Satelite detecta foco de calor
    await p.execute(
        "INSERT INTO satellite_detections (org_id, source, location, brightness, confidence, frp, acquired_at) "
        "VALUES ($1,'FIRMS_VIIRS', ST_MakePoint($3,$2)::geography, 342.5, 0.90, 45.2, $4)",
        org_id, lat + 0.002, lon + 0.001, NOW - timedelta(minutes=4),
    )
    print("[1] Satelite FIRMS: foco de calor a ~250m (confianza 0.90)")

    # 2) Dos nodos confirman con spike de temperatura + gas
    for var, val in [("temp", 46.5), ("humidity", 14.0), ("mq4", 520.0)]:
        await p.execute(
            "INSERT INTO readings (org_id, device_id, variable, value, ts) VALUES ($1,$2,$3,$4,$5)",
            org_id, node["id"], var, val, NOW - timedelta(minutes=3),
        )
    score = await anomaly_score(str(node["id"]), "temp", 46.5)
    print(f"[2] Nodos ESP32 confirman: temp 46.5C, hum 14%, MQ-4 520ppm | score IA={score:.2f}")

    # 3) Ciudadano reporta con foto (reputacion alta)
    cit = await p.fetchrow(
        "INSERT INTO citizens (token, valid_count, reputation) VALUES ('demo-ciudadano', 12, 0.80) "
        "ON CONFLICT (token) DO UPDATE SET reputation=0.80 RETURNING id, reputation"
    )
    await p.execute(
        "INSERT INTO citizen_reports (org_id, citizen_id, type, description, location, "
        "correlation_score, reputation_score, status) "
        "VALUES ($1,$2,'incendio','Veo humo denso en el monte', ST_MakePoint($4,$3)::geography, "
        "0.85, $5, 'verificado')",
        org_id, cit["id"], lat, lon + 0.0015, float(cit["reputation"]),
    )
    print(f"[3] Ciudadano reporta con foto (reputacion {float(cit['reputation']):.2f})")

    # 4) Correlacion multi-fuente -> alerta critica
    alert = await create_alert(
        org_id=org_id, alert_type="incendio", severity="critica",
        lat=lat, lon=lon, title="Incendio forestal — confirmacion multi-fuente",
        sensor_source=Source("sensor", lat, lon, score), device_id=str(node["id"]),
    )
    print(f"\n[4] >>> ALERTA CRITICA creada | confianza IA = {alert['confidence']*100:.0f}%")
    print(f"        fuentes correlacionadas: {', '.join(alert['source_types'])}")

    # 5) Operador confirma (respuesta rapida) -> KPI de respuesta mejora
    await p.execute(
        "UPDATE alerts SET status='confirmada', acknowledged_at=now(), resolved_at=now() WHERE id=$1",
        alert["id"],
    )
    await p.execute(
        "INSERT INTO alert_events (alert_id, action) VALUES ($1,'confirmar')", alert["id"]
    )
    print("[5] Operador CONFIRMA la alerta -> KPI de tiempo de respuesta actualizado\n")
    print("Demo completa. Abrir el dashboard: http://localhost:3000")
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
