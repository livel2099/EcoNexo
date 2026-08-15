"use client";
import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../app/lib/api";
import type { Report } from "../app/lib/types";

// Backoffice de moderacion — filtro inteligente: score de correlacion IA
// (cercania a lecturas/satelite anomalos) cruzado con reputacion del emisor.
function scoreColor(v: number | null): string {
  if (v == null) return "#5c6f65";
  return v >= 0.66 ? "#37D08A" : v >= 0.33 ? "#D97706" : "#DC2626";
}

export default function ReportsPanel({ token }: { token: string }) {
  const [reports, setReports] = useState<Report[]>([]);
  const load = () => apiGet<Report[]>("/reports", token).then(setReports).catch(() => {});
  useEffect(() => { load(); }, [token]);

  async function moderate(id: string, status: "verificado" | "rechazado") {
    await apiPost(`/reports/${id}/moderate`, token, { status });
    load();
  }

  const pend = reports.filter((r) => r.status === "pendiente").length;

  return (
    <div className="view">
      <h2>Reportes ciudadanos</h2>
      <div className="sub">{reports.length} reportes · <span style={{ color: "#D97706" }}>{pend} pendientes</span> · filtro inteligente (correlación IA × reputación)</div>
      <table>
        <thead><tr><th>Tipo</th><th>Descripción</th><th>Correlación IA</th><th>Reputación</th><th>Estado</th><th>Foto</th><th></th></tr></thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id}>
              <td style={{ fontWeight: 600, textTransform: "capitalize" }}>{r.type}</td>
              <td className="muted" style={{ maxWidth: 240 }}>{r.description || "—"}</td>
              <td className="score" style={{ color: scoreColor(r.correlation_score) }}>
                {r.correlation_score != null ? `${Math.round(r.correlation_score * 100)}%` : "—"}
              </td>
              <td className="score" style={{ color: scoreColor(r.reputation_score) }}>
                {r.reputation_score != null ? `${Math.round(r.reputation_score * 100)}%` : "—"}
              </td>
              <td>
                <span className={`stat ${r.status === "verificado" ? "online" : r.status === "rechazado" ? "alerta" : "offline"}`}>● {r.status}</span>
              </td>
              <td>{r.photo_url ? <a href={r.photo_url} target="_blank" rel="noreferrer" style={{ color: "#8fbcff" }}>ver</a> : "—"}</td>
              <td style={{ whiteSpace: "nowrap" }}>
                {r.status === "pendiente" && (
                  <>
                    <button className="sm primary" onClick={() => moderate(r.id, "verificado")}>Verificar</button>{" "}
                    <button className="sm danger" onClick={() => moderate(r.id, "rechazado")}>Rechazar</button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {reports.length === 0 && <div className="empty">Sin reportes todavía. Cargá uno desde <span className="mono">/reportar</span>.</div>}
    </div>
  );
}
