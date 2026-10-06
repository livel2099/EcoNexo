"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../app/lib/api";

type Operations = {
  generated_at: string;
  stale_after_minutes: number;
  metrics: {
    devices_total: number; devices_stale: number; latest_reading_at: string | null;
    alerts_pending: number; alerts_confirmed: number; alerts_discarded: number;
    pipeline_degraded_24h: number; latest_pipeline_at: string | null;
  };
  integrations: { name: string; configured: boolean; detail: string }[];
  predictive_status: string;
  predictive_gaps: string[];
};

function date(value: string | null) {
  return value ? new Date(value).toLocaleString("es-AR") : "Sin registros";
}

export default function PlatformOperationsPanel({ token }: { token: string }) {
  const [data, setData] = useState<Operations | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    setBusy(true); setError("");
    try { setData(await apiGet<Operations>("/platform/operations", token)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo consultar la operación."); }
    finally { setBusy(false); }
  }, [token]);
  useEffect(() => { void refresh(); }, [refresh]);

  return <section aria-label="Operación y predicción">
    <div className="platform-table-title"><h2>Salud operativa global</h2><button disabled={busy} onClick={() => void refresh()}>{busy ? "Consultando…" : "Actualizar diagnóstico"}</button></div>
    {error && <p role="alert" className="workspace-message error">{error}</p>}
    {data && <>
      <p>Datos al {date(data.generated_at)}{error ? " · Diagnóstico anterior; no actualizado" : ""}.</p>
      <section className="platform-metrics">
        <article><span>Nodos registrados</span><strong>{data.metrics.devices_total}</strong></article>
        <article><span>Nodos sin datos recientes</span><strong>{data.metrics.devices_stale}</strong><small>Sin contacto, más de {data.stale_after_minutes} min o reloj adelantado.</small></article>
        <article><span>Alertas pendientes</span><strong>{data.metrics.alerts_pending}</strong></article>
        <article><span>Ejecuciones degradadas · 24 h</span><strong>{data.metrics.pipeline_degraded_24h}</strong><small>Fallidas, parciales o demoradas.</small></article>
      </section>
      <p>Última lectura: {date(data.metrics.latest_reading_at)}. Última ejecución terminada: {date(data.metrics.latest_pipeline_at)}.</p>
      <section className="platform-overview-grid">
        {data.integrations.map((item) => <article key={item.name}><h3>{item.name}</h3><strong className={item.configured ? "status-on" : "status-warn"}>{item.configured ? "Configurada" : "Sin configurar / deshabilitada"}</strong><p>{item.detail}</p></article>)}
      </section>
      <div className="platform-table-card" style={{ marginTop: 24, padding: 24 }}>
        <span className="eyebrow">MADUREZ PREDICTIVA</span><h2>Predicción de incidentes pendiente de validación</h2>
        <p>El ciclo predictivo archiva pronósticos futuros, registra resultados independientes, entrena modelos locales y mide anticipación, calibración y deriva. Un índice heurístico no equivale a una probabilidad validada de incidente futuro.</p>
        <p><a href="/dashboard">Abrir Centro operativo → Predicción</a></p>
        <p>Alertas confirmadas: {data.metrics.alerts_confirmed}. Descartadas: {data.metrics.alerts_discarded}. Estos recuentos no miden los incidentes omitidos ni la anticipación.</p>
        <ol>{data.predictive_gaps.map((gap) => <li key={gap}>{gap}</li>)}</ol>
      </div>
    </>}
  </section>;
}
