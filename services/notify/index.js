// notify-service — escucha alertas del bus y despacha notificaciones.
const crypto = require("crypto");
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

const serviceToken = process.env.INTERNAL_SERVICE_TOKEN || "";
const allowedOrigin = process.env.CORS_ORIGIN || "http://localhost:3000";
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

function authorized(req) {
  const provided = String(req.headers.authorization || "").replace(/^Bearer\s+/i, "");
  if (!serviceToken || provided.length !== serviceToken.length) return false;
  return crypto.timingSafeEqual(Buffer.from(provided), Buffer.from(serviceToken));
}

// HTTP interno: health publico para orquestador; datos protegidos por token.
const server = http.createServer(async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", allowedOrigin);
  res.setHeader("Vary", "Origin");
  res.setHeader("X-Content-Type-Options", "nosniff");
  if (req.method === "OPTIONS") {
    res.setHeader("Access-Control-Allow-Headers", "Authorization, Content-Type");
    res.writeHead(204); return res.end();
  }
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({ status: "ok" }));
  }
  if (!authorized(req)) {
    res.writeHead(401, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({ detail: "Credencial interna invalida" }));
  }
  const match = req.url.match(/^\/notifications\/([0-9a-f-]+)$/i);
  if (match) {
    try {
      const result = await pool.query(
        "SELECT id, alert_id, title, body, read, created_at FROM notifications WHERE org_id=$1 ORDER BY created_at DESC LIMIT 50",
        [match[1]]
      );
      res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
      return res.end(JSON.stringify(result.rows));
    } catch (e) {
      res.writeHead(500, { "Content-Type": "application/json" });
      return res.end(JSON.stringify({ detail: "Error interno" }));
    }
  }
  res.writeHead(404); res.end();
});
server.listen(+(process.env.PORT || 8200), () => console.log(`[notify] http en :${process.env.PORT || 8200}`));
