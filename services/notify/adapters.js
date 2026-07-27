// Adapters de canales de notificacion.
// In-app: real (persistido en tabla notifications).
// email / sms / whatsapp: STUB documentado — el MVP registra la intencion de
// envio; en produccion se conecta a SES / SNS / WhatsApp Cloud API.

function dispatchInApp(pool, { orgId, alertId, title, body }) {
  return pool.query(
    "INSERT INTO notifications (org_id, alert_id, channel, title, body) VALUES ($1,$2,'in_app',$3,$4)",
    [orgId, alertId, title, body]
  );
}

// STUBS — reemplazar por integraciones reales en Fase 2.
async function dispatchEmail(to, subject, body) {
  console.log(`[notify][STUB email] -> ${to}: ${subject}`);
  return { channel: "email", status: "stubbed" };
}
async function dispatchSMS(to, body) {
  console.log(`[notify][STUB sms] -> ${to}: ${body}`);
  return { channel: "sms", status: "stubbed" };
}
async function dispatchWhatsApp(to, body) {
  console.log(`[notify][STUB whatsapp] -> ${to}: ${body}`);
  return { channel: "whatsapp", status: "stubbed" };
}

module.exports = { dispatchInApp, dispatchEmail, dispatchSMS, dispatchWhatsApp };
