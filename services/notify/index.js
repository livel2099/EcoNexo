// notify-service — escucha alertas del bus y despacha notificaciones.
const http = require("http");
const mqtt = require("mqtt");
const { Pool } = require("pg");
const { dispatchInApp } = require("./adapters");

const pool = new Pool({
  host: process.env.POSTGRES_HOST || "localhost",
  port: +(process.env.POSTGRES_PORT || 5432),
  database: process.env.POSTGRES_DB || "econexo",
  user: process.env.POSTGRES_USER || "econexo",
  password: process.env.POSTGRES_PASSWORD || "econexo_dev_pw",
});

const url = `mqtt://${process.env.MQTT_HOST || "localhost"}:${process.env.MQTT_PORT || 1883}`;
const client = mqtt.connect(url, { reconnectPeriod: 3000 });

client.on("connect", () => {
  console.log(`[notify] conectado a ${url}`);
  client.subscribe("econexo/internal/+/alerts");
});
client.on("error", (e) => console.error("[notify] mqtt error:", e.message));

client.on("message", async (topic, payload) => {
  const orgId = topic.split("/")[2];
  let a;
  try { a = JSON.parse(payload.toString()); } catch { return; }
  const title = `[${(a.severity || "").toUpperCase()}] ${a.title || "Alerta"}`;
  const body = `Confianza ${Math.round((a.confidence || 0) * 100)}% — fuentes: ${(a.source_types || []).join(", ")}`;
  try {
    await dispatchInApp(pool, { orgId, alertId: a.id, title, body });
    console.log(`[notify] in-app -> org ${orgId}: ${title}`);
  } catch (e) {
    console.error("[notify] error:", e.message);
  }
});

// HTTP: lista de notificaciones in-app por org + health.
const server = http.createServer(async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({ status: "ok" }));
  }
  const m = req.url.match(/^\/notifications\/([0-9a-f-]+)/i);
  if (m) {
    try {
      const r = await pool.query(
        "SELECT id, alert_id, title, body, read, created_at FROM notifications WHERE org_id=$1 ORDER BY created_at DESC LIMIT 50",
        [m[1]]
      );
      res.writeHead(200, { "Content-Type": "application/json" });
      return res.end(JSON.stringify(r.rows));
    } catch (e) {
      res.writeHead(500); return res.end(e.message);
    }
  }
  res.writeHead(404); res.end();
});
server.listen(+(process.env.PORT || 8200), () => console.log(`[notify] http en :${process.env.PORT || 8200}`));
