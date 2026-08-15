"use client";
import { useEffect, useState } from "react";
import { apiGet, apiPost, API } from "../app/lib/api";
import type { Rule } from "../app/lib/types";

// CRUD visual del motor de reglas — crear una regla sin tocar codigo.
const VARS = ["temp", "humidity", "pm25", "mq4", "nivel", "turbidez"];
const OPS = [">", ">=", "<", "<=", "==", "!="];

export default function RulesPanel({ token }: { token: string }) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [alertType, setAlertType] = useState("anomalia");
  const [variable, setVariable] = useState("temp");
  const [operator, setOperator] = useState(">");
  const [threshold, setThreshold] = useState("42");
  const [severity, setSeverity] = useState("alta");
  const [reqSat, setReqSat] = useState(false);

  const load = () => apiGet<Rule[]>("/rules", token).then(setRules).catch(() => {});
  useEffect(() => { load(); }, [token]);

  async function create() {
    await apiPost("/rules", token, {
      name, alert_type: alertType,
      conditions: [{ variable, operator, threshold: parseFloat(threshold) }],
      condition_logic: "AND", window_seconds: 300, severity,
      require_satellite: reqSat, actions: ["notify"], enabled: true,
    });
    setOpen(false); setName(""); load();
  }

  async function toggle(id: string) {
    await fetch(`${API}/rules/${id}/toggle`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` } });
    load();
  }
  async function del(id: string) {
    await fetch(`${API}/rules/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
    load();
  }

  return (
    <div className="view">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2>Motor de reglas</h2>
          <div className="sub">SI [variable][operador][umbral] DURANTE [ventana] ENTONCES [severidad + acciones]</div>
        </div>
        <button className="primary" onClick={() => setOpen(true)}>+ Nueva regla</button>
      </div>

      <table>
        <thead><tr><th>Nombre</th><th>Tipo</th><th>Condiciones</th><th>Severidad</th><th>Satélite</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          {rules.map((r) => (
            <tr key={r.id}>
              <td style={{ fontWeight: 600 }}>{r.name}</td>
              <td className="muted">{r.alert_type}</td>
              <td className="mono" style={{ fontSize: 12 }}>
                {r.conditions.map((c, i) => <span key={i}>{c.variable} {c.operator} {c.threshold}{i < r.conditions.length - 1 ? ` ${r.condition_logic} ` : ""}</span>)}
              </td>
              <td><span className={`sev ${r.severity}`}>{r.severity}</span></td>
              <td>{r.require_satellite ? "sí" : "—"}</td>
              <td><span className={`stat ${r.enabled ? "online" : "offline"}`}>● {r.enabled ? "activa" : "pausada"}</span></td>
              <td style={{ whiteSpace: "nowrap" }}>
                <button className="sm" onClick={() => toggle(r.id)}>{r.enabled ? "Pausar" : "Activar"}</button>{" "}
                <button className="sm danger" onClick={() => del(r.id)}>Borrar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rules.length === 0 && <div className="empty">Sin reglas. Creá la primera.</div>}

      {open && (
        <div className="modal-bg" onClick={() => setOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Nueva regla</h3>
            <label>Nombre</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Incendio forestal zona norte" />
            <label>Tipo de alerta</label>
            <select value={alertType} onChange={(e) => setAlertType(e.target.value)}>
              <option value="incendio">incendio</option>
              <option value="anomalia_hidrica">anomalia_hidrica</option>
              <option value="anomalia">anomalia</option>
            </select>
            <label>Condición</label>
            <div className="row2">
              <select value={variable} onChange={(e) => setVariable(e.target.value)}>{VARS.map((v) => <option key={v}>{v}</option>)}</select>
              <select value={operator} onChange={(e) => setOperator(e.target.value)}>{OPS.map((o) => <option key={o}>{o}</option>)}</select>
              <input value={threshold} onChange={(e) => setThreshold(e.target.value)} />
            </div>
            <label>Severidad</label>
            <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              {["baja", "media", "alta", "critica"].map((s) => <option key={s}>{s}</option>)}
            </select>
            <label style={{ display: "flex", alignItems: "center", gap: 8, margin: "8px 0 16px" }}>
              <input type="checkbox" checked={reqSat} onChange={(e) => setReqSat(e.target.checked)} style={{ width: "auto", margin: 0 }} />
              Requiere confirmación satelital
            </label>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setOpen(false)}>Cancelar</button>
              <button className="primary" disabled={!name} onClick={create}>Crear regla</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
