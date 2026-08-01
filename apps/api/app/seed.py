"""Datos semilla de EcoNexo.

Crea 3 organizaciones de Misiones (municipio, forestal y energética),
usuarios (argon2), tipos de dispositivo, zonas de riesgo
(poligonos PostGIS), ~38 nodos, 30 dias de historial con ciclos diurnos y
anomalias inyectadas, reglas precargadas y alertas historicas para KPIs.

Uso:  docker compose run --rm api python -m app.seed   (idempotente)
"""
from __future__ import annotations

import asyncio
import json
import math
import random
from datetime import datetime, timedelta, timezone

import asyncpg

from .config import get_settings
from .security import hash_secret, new_token

random.seed(42)
NOW = datetime.now(timezone.utc)

ORGS = [
    ("Municipalidad de Posadas - Demo", "municipalidad-posadas-demo", "municipio", "#2E7D5B", -27.3621, -55.9007, "POS", "Capital", "Posadas", "municipal"),
    ("Corredor Verde Yabotí - Demo", "corredor-yaboti-demo", "forestal", "#1F6F43", -26.82, -54.45, "YAB", "San Pedro", "San Pedro", "area_operativa"),
    ("Red Energética Oberá - Demo", "red-energetica-obera-demo", "energetica", "#0F766E", -27.4871, -55.1199, "OBE", "Oberá", "Oberá", "departamental"),
]

VARS = {
    "municipio": [
        ("temp", "C", 22, 8, 33, 38, ">"),
        ("humidity", "%", 55, 20, 30, 20, "<"),
        ("pm25", "ug/m3", 25, 15, 55, 75, ">"),
    ],
    "forestal": [
        ("temp", "C", 26, 10, 38, 42, ">"),
        ("humidity", "%", 45, 22, 25, 18, "<"),
        ("mq4", "ppm", 200, 60, 350, 500, ">"),
    ],
    "energetica": [
        ("temp", "C", 16, 9, 30, 36, ">"),
        ("nivel", "m", 4.5, 1.2, 7, 8.5, ">"),
        ("turbidez", "NTU", 40, 20, 90, 120, ">"),
    ],
}

NODES_PER_ORG = {"municipio": 12, "forestal": 14, "energetica": 12}


async def main() -> None:
    conn = await asyncpg.connect(get_settings().dsn)
    try:
        await _reset(conn)
        for row in ORGS:
            await _seed_org(conn, *row)
        print("Seed completo.")
    finally:
        await conn.close()


async def _reset(conn: asyncpg.Connection) -> None:
    await conn.execute(
        "TRUNCATE organizations, users, device_types, devices, readings, risk_zones, "
        "citizens, citizen_reports, satellite_detections, rules, alerts, alert_sources, "
        "alert_events, notifications, impact_reports, audit_events RESTART IDENTITY CASCADE"
    )


async def _seed_org(
    conn, name, slug, vertical, color, lat, lon, prefix, department, municipality, territory_scope
) -> None:
    org_id = await conn.fetchval(
        "INSERT INTO organizations "
        "(name, slug, vertical, primary_color, baseline_response_s, province, department, municipality, territory_scope) "
        "VALUES ($1,$2,$3,$4,3600,'Misiones',$5,$6,$7) RETURNING id",
        name, slug, vertical, color, department, municipality, territory_scope,
    )
    email_domain = "misiones.econexo.ar" if slug == "municipalidad-posadas-demo" else f"{slug}.econexo.ar"
    for email_role, role in [("admin", "admin"), ("operador", "operador")]:
        await conn.execute(
            "INSERT INTO users (org_id, email, name, role, password_hash) VALUES ($1,$2,$3,$4,$5)",
            org_id, f"{email_role}@{email_domain}", f"{email_role.title()} {name}",
            role, hash_secret("econexo123"),
        )

    var_defs = VARS[vertical]
    dtype_id = await conn.fetchval(
        "INSERT INTO device_types (org_id, name, variables) VALUES ($1,$2,$3::jsonb) RETURNING id",
        org_id, f"Nodo {vertical}", _json_vars(var_defs),
    )

    kind = "incendio" if vertical == "forestal" else ("hidrica" if vertical == "energetica" else "general")
    await conn.execute(
        "INSERT INTO risk_zones (org_id, name, kind, area, center, radius_m) VALUES "
        "($1,$2,$3, ST_MakePolygon(ST_GeomFromText($4, 4326))::geography, "
        "ST_Centroid(ST_MakePolygon(ST_GeomFromText($4, 4326)))::geography, $5)",
        org_id, f"Zona prioritaria Misiones · {name}", kind, _square_wkt(lat, lon, 0.06), 5000.0,
    )

    n = NODES_PER_ORG[vertical]
    device_ids = []
    for i in range(n):
        dlat = lat + random.uniform(-0.05, 0.05)
        dlon = lon + random.uniform(-0.05, 0.05)
        # Mantener los nodos demo dentro del límite provincial: si el punto cae
        # fuera de Misiones, se regenera con un desvío cada vez menor hasta entrar.
        for _attempt in range(20):
            if await conn.fetchval(
                "SELECT econexo_inside_misiones(ST_MakePoint($1,$2)::geography)", dlon, dlat
            ):
                break
            jitter = 0.03 / (_attempt + 1)
            dlat = lat + random.uniform(-jitter, jitter)
            dlon = lon + random.uniform(-jitter, jitter)
        did = await conn.fetchval(
            "INSERT INTO devices (org_id, device_type_id, name, external_id, location, "
            "status, battery, rssi, tags, mqtt_username, mqtt_password_hash, last_seen) "
            "VALUES ($1,$2,$3,$4, ST_MakePoint($6,$5)::geography, 'online', $7, $8, $9, $10, $11, $12) "
            "RETURNING id",
            org_id, dtype_id, f"{prefix}-{i+1:02d}", f"{prefix.lower()}-{i+1:02d}",
            dlat, dlon, round(random.uniform(45, 100), 1), random.randint(-95, -55),
            _tags(vertical, i), f"dev-{prefix.lower()}-{i+1:02d}", hash_secret(new_token()),
            NOW - timedelta(minutes=random.randint(0, 8)),
        )
        device_ids.append((did, dlat, dlon))

    await _seed_readings(conn, org_id, device_ids, var_defs, device_ids[0])
    await _seed_rules(conn, org_id, vertical)
    await _seed_history(conn, org_id, vertical, device_ids)
    print(f"  org {slug}: {n} nodos, reglas y KPIs cargados")


async def _seed_readings(conn, org_id, device_ids, var_defs, anomalous_node) -> None:
    records = []
    for did, dlat, dlon in device_ids:
        for var, unit, base, amp, warn, crit, op in var_defs:
            for h in range(30 * 24):
                ts = NOW - timedelta(hours=(30 * 24 - h))
                diurnal = amp * math.sin((ts.hour - 6) / 24 * 2 * math.pi)
                val = base + diurnal + random.gauss(0, amp * 0.15)
                if did == anomalous_node[0] and h > 30 * 24 - 20:
                    val = (crit + random.uniform(1, 4)) if op == ">" else (crit - random.uniform(1, 4))
                records.append((org_id, did, var, round(val, 2), ts))
    await conn.copy_records_to_table(
        "readings", columns=["org_id", "device_id", "variable", "value", "ts"], records=records
    )


async def _seed_rules(conn, org_id, vertical) -> None:
    rules = []
    if vertical == "forestal":
        rules.append((
            "Incendio forestal (temp alta + humedad baja)", "incendio",
            '[{"variable":"temp","operator":">","threshold":42},'
            '{"variable":"humidity","operator":"<","threshold":18}]',
            "AND", 300, "critica", True, '["notify","escalate"]',
        ))
    if vertical == "energetica":
        rules.append((
            "Anomalia hidrica critica (nivel/turbidez)", "anomalia_hidrica",
            '[{"variable":"nivel","operator":">","threshold":8},'
            '{"variable":"turbidez","operator":">","threshold":120}]',
            "OR", 600, "alta", False, '["notify"]',
        ))
    if vertical == "municipio":
        rules.append((
            "Calidad de aire critica (PM2.5)", "anomalia",
            '[{"variable":"pm25","operator":">","threshold":75}]',
            "AND", 900, "media", False, '["notify"]',
        ))
    for name, atype, conds, logic, win, sev, req_sat, actions in rules:
        await conn.execute(
            "INSERT INTO rules (org_id, name, alert_type, conditions, condition_logic, "
            "window_seconds, severity, require_satellite, actions) "
            "VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7,$8,$9::jsonb)",
            org_id, name, atype, conds, logic, win, sev, req_sat, actions,
        )


async def _seed_history(conn, org_id, vertical, device_ids) -> None:
    atype = {"forestal": "incendio", "energetica": "anomalia_hidrica", "municipio": "anomalia"}[vertical]
    for k in range(4):
        did, dlat, dlon = random.choice(device_ids)
        detected = NOW - timedelta(days=random.randint(1, 20), minutes=random.randint(0, 300))
        ack = detected + timedelta(seconds=random.randint(120, 600))
        status = "confirmada" if k % 3 != 0 else "descartada"
        sev = random.choice(["alta", "critica", "media"])
        aid = await conn.fetchval(
            "INSERT INTO alerts (org_id, type, severity, status, location, confidence, title, "
            "device_id, detected_at, acknowledged_at, resolved_at) "
            "VALUES ($1,$2,$3,$4, ST_MakePoint($6,$5)::geography,$7,$8,$9,$10,$11,$11) RETURNING id",
            org_id, atype, sev, status, dlat, dlon, round(random.uniform(0.7, 0.95), 3),
            f"Evento historico {k+1}", did, detected, ack,
        )
        await conn.execute(
            "INSERT INTO alert_sources (alert_id, source_type, weight) VALUES ($1,'sensor',0.4)", aid
        )


def _json_vars(var_defs) -> str:
    return json.dumps([
        {"key": v[0], "unit": v[1], "warn": v[4], "crit": v[5], "operator": v[6]}
        for v in var_defs
    ])


def _tags(vertical: str, i: int) -> list[str]:
    base = {"municipio": ["urbano"], "forestal": ["monte"], "energetica": ["planta"]}[vertical]
    return base + (["norte"] if i % 2 == 0 else ["sur"])


def _square_wkt(lat: float, lon: float, d: float) -> str:
    pts = [
        (lon - d, lat - d), (lon + d, lat - d), (lon + d, lat + d),
        (lon - d, lat + d), (lon - d, lat - d),
    ]
    ring = ", ".join(f"{x} {y}" for x, y in pts)
    return f"LINESTRING({ring})"


if __name__ == "__main__":
    asyncio.run(main())
