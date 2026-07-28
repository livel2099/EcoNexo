// ingest-service — consumidor MQTT de telemetria de nodos ESP32.
// Topics:
//   econexo/{org_id}/{external_id}/telemetry  (JSON: battery, rssi, y variables)
//   econexo/{org_id}/{external_id}/status     (JSON: { online: bool })
// Persiste lecturas en PostGIS, actualiza estado del dispositivo y republica
// la lectura normalizada al bus interno econexo/internal/{org_id}/readings.

const mqtt = require("mqtt");
const { Pool } = require("pg");

const pool = new Pool(
  process.env.DATABASE_URL
    ? { connectionString: process.env.DATABASE_URL }
    : {
        host: process.env.POSTGRES_HOST || "localhost",
        port: +(process.env.POSTGRES_PORT || 5432),
        database: process.env.POSTGRES_DB || "econexo",
        user: process.env.POSTGRES_USER || "econexo",
        password: process.env.POSTGRES_PASSWORD || "econexo_dev_pw",
      }
);

const url = process.env.MQTT_URL ||
  `mqtt://${process.env.MQTT_HOST || "localhost"}:${process.env.MQTT_PORT || 1883}`;
const client = mqtt.connect(url, { reconnectPeriod: 3000 });

const META = new Set(["battery", "rssi", "ts"]);

client.on("connect", () => {
  console.log(`[ingest] conectado a ${url}`);
  client.subscribe("econexo/+/+/telemetry");
  client.subscribe("econexo/+/+/status");
});

client.on("error", (e) => console.error("[ingest] mqtt error:", e.message));

client.on("message", async (topic, payload) => {
  const parts = topic.split("/"); // econexo/{org}/{ext}/{kind}
  if (parts.length !== 4) return;
  const [, orgId, externalId, kind] = parts;
  let msg;
  try { msg = JSON.parse(payload.toString()); } catch { return; }

  try {
    const dev = await pool.query(
      "SELECT id, org_id FROM devices WHERE org_id=$1 AND external_id=$2",
      [orgId, externalId]
    );
    if (dev.rowCount === 0) return;
    const deviceId = dev.rows[0].id;

    if (kind === "status") {
      const online = msg.online !== false;
      await pool.query(
        "UPDATE devices SET status=$2, last_seen=now() WHERE id=$1",
        [deviceId, online ? "online" : "offline"]
      );
      return;
    }

    // telemetry
    const variables = Object.entries(msg).filter(([k, v]) => !META.has(k) && typeof v === "number");
    for (const [variable, value] of variables) {
      await pool.query(
        "INSERT INTO readings (org_id, device_id, variable, value) VALUES ($1,$2,$3,$4)",
        [orgId, deviceId, variable, value]
      );
    }
    await pool.query(
      "UPDATE devices SET last_seen=now(), status='online', " +
        "battery=COALESCE($2, battery), rssi=COALESCE($3, rssi) WHERE id=$1",
      [deviceId, msg.battery ?? null, msg.rssi ?? null]
    );

    // republicar al bus interno para el feed WebSocket del dashboard
    client.publish(
      `econexo/internal/${orgId}/readings`,
      JSON.stringify({ device_id: deviceId, external_id: externalId, readings: Object.fromEntries(variables), ts: msg.ts || new Date().toISOString() })
    );
  } catch (e) {
    console.error("[ingest] error procesando:", e.message);
  }
});
