// simulator — emula nodos ESP32 publicando telemetria realista por MQTT.
// Toma los dispositivos sembrados en PostGIS y publica cada PERIOD_MS a los
// topics econexo/{org_id}/{external_id}/telemetry con ciclo diurno + ruido y
// anomalias esporadicas. Es lo que da vida a la demo en tiempo real.

const mqtt = require("mqtt");
const { Pool } = require("pg");

const PERIOD_MS = +(process.env.PERIOD_MS || 5000);
const ANOMALY_PROB = +(process.env.ANOMALY_PROB || 0.02);

// base y amplitud diurna por variable (coincide con el seeder).
const MODELS = {
  temp: { base: 24, amp: 9, crit: 44, op: ">" },
  humidity: { base: 50, amp: 20, crit: 16, op: "<" },
  pm25: { base: 25, amp: 15, crit: 80, op: ">" },
  mq4: { base: 200, amp: 60, crit: 520, op: ">" },
  nivel: { base: 4.5, amp: 1.2, crit: 8.5, op: ">" },
  turbidez: { base: 40, amp: 20, crit: 125, op: ">" },
};

const pool = new Pool({
  host: process.env.POSTGRES_HOST || "localhost",
  port: +(process.env.POSTGRES_PORT || 5432),
  database: process.env.POSTGRES_DB || "econexo",
  user: process.env.POSTGRES_USER || "econexo",
  password: process.env.POSTGRES_PASSWORD || "econexo_dev_pw",
});

const url = `mqtt://${process.env.MQTT_HOST || "localhost"}:${process.env.MQTT_PORT || 1883}`;
const client = mqtt.connect(url, { reconnectPeriod: 3000 });

function value(v) {
  const m = MODELS[v] || { base: 10, amp: 2, crit: 100, op: ">" };
  const hour = new Date().getUTCHours() + new Date().getUTCMinutes() / 60;
  const diurnal = m.amp * Math.sin(((hour - 6) / 24) * 2 * Math.PI);
  let val = m.base + diurnal + (Math.random() - 0.5) * m.amp * 0.3;
  if (Math.random() < ANOMALY_PROB) {
    val = m.op === ">" ? m.crit + Math.random() * 3 : m.crit - Math.random() * 3;
  }
  return Math.round(val * 100) / 100;
}

async function loadNodes() {
  const r = await pool.query(
    `SELECT d.org_id, d.external_id,
            COALESCE((SELECT array_agg(x->>'key') FROM jsonb_array_elements(dt.variables) x), ARRAY['temp','humidity']) AS vars
     FROM devices d LEFT JOIN device_types dt ON dt.id = d.device_type_id`
  );
  return r.rows;
}

let nodes = [];
async function tick() {
  if (nodes.length === 0) {
    try { nodes = await loadNodes(); console.log(`[sim] ${nodes.length} nodos`); }
    catch (e) { console.error("[sim] db:", e.message); return; }
  }
  for (const n of nodes) {
    const payload = { battery: Math.round((60 + Math.random() * 40) * 10) / 10, rssi: -60 - Math.floor(Math.random() * 30), ts: new Date().toISOString() };
    for (const v of n.vars) payload[v] = value(v);
    client.publish(`econexo/${n.org_id}/${n.external_id}/telemetry`, JSON.stringify(payload));
  }
}

client.on("connect", () => {
  console.log(`[sim] conectado a ${url} (periodo ${PERIOD_MS}ms)`);
  setInterval(() => tick().catch((e) => console.error(e.message)), PERIOD_MS);
});
client.on("error", (e) => console.error("[sim] mqtt error:", e.message));
