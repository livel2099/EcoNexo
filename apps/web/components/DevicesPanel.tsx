"use client";
import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../app/lib/api";
import type { Device, PipelineRun } from "../app/lib/types";
import Sparkline from "./Sparkline";

// Vista de gestion de dispositivos + drawer de detalle con series temporales.
export default function DevicesPanel({ token }: { token: string }) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [sel, setSel] = useState<Device | null>(null);
  const [variable, setVariable] = useState<string>("temp");
  const [series, setSeries] = useState<{ ts: string; value: number }[]>([]);

  const [error, setError] = useState("");
  const [seriesError, setSeriesError] = useState("");
  const [loadingSeries, setLoadingSeries] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const next = await apiGet<Device[]>("/devices", token);
        if (!active) return;
        setDevices(next);
        setSel((current) => current ? next.find((device) => device.id === current.id) || null : null);
        setError("");
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "No se pudieron actualizar los dispositivos");
      }
    }
    void load();
    const timer = window.setInterval(() => void load(), 15_000);
    return () => { active = false; window.clearInterval(timer); };
  }, [token, revision]);

  async function refreshVirtualReadings() {
    setBusy(true);
    setNotice("");
    try {
      const run = await apiPost<PipelineRun>("/pipeline/run", token, {});
      const details = run.errors.map((item) => String(item.error || item.detail || "")).filter(Boolean).join(" · ");
      setNotice(`${run.devices_updated} nodos actualizados · ${run.readings_inserted} lecturas. ${details}`);
      setRevision((current) => current + 1);
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "No se pudieron obtener las lecturas");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!sel) return;
    let active = true;
    setSeries([]);
    setSeriesError("");
    setLoadingSeries(true);
    apiGet<{ ts: string; value: number }[]>(`/devices/${sel.id}/readings?variable=${encodeURIComponent(variable)}&hours=48`, token)
      .then((rows) => { if (active) setSeries(rows); })
      .catch((cause) => { if (active) setSeriesError(cause instanceof Error ? cause.message : "No se pudieron consultar las lecturas"); })
      .finally(() => { if (active) setLoadingSeries(false); });
    return () => { active = false; };
  }, [sel, variable, token]);

  function sourceLabel(device: Device) {
    return device.telemetry_mode === "open_meteo" ? "Open-Meteo · datos modelados" : device.telemetry_mode === "manual" ? "Carga manual" : "Dispositivo físico · MQTT";
  }

  function statusLabel(device: Device) {
    if (device.telemetry_mode === "mqtt") return device.status;
    if (!Object.keys(device.latest_readings || {}).length) return "Sin lecturas";
    return device.status === "online" ? "Datos recientes" : "Datos sin actualizar";
  }

  const online = devices.filter((d) => d.status === "online").length;

  return (
    <div className="view">
      <h2>Dispositivos y nodos virtuales</h2>
      <div className="sub">{devices.length} nodos · <span style={{ color: "#37D08A" }}>{online} online</span> · actualización cada 15 segundos</div>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <button type="button" disabled={busy} onClick={() => setRevision((current) => current + 1)}>Actualizar estado</button>
      {devices.some((device) => device.telemetry_mode === "open_meteo") && <button type="button" className="primary" disabled={busy} onClick={() => void refreshVirtualReadings()}>{busy ? "Obteniendo lecturas…" : "Obtener lecturas virtuales"}</button>}
      <div className="grid-cards">
        {devices.map((d) => (
          <div className="dcard" key={d.id} onClick={() => { setSel(d); setVariable("temp"); }}>
            <div className="dh">
              <span className="nm">{d.name}</span>
              <span className={`stat ${d.status}`}>● {statusLabel(d)}</span>
            </div>
            <div className="muted">{sourceLabel(d)}</div>
            <div>{Object.entries(d.latest_readings || {}).map(([key, value]) => `${key}: ${value}`).join(" · ") || "Sin lecturas todavía"}</div>
            {d.last_pipeline_status?.startsWith("error:") && <div role="status">{d.last_pipeline_status}</div>}
            {d.telemetry_mode === "mqtt" && <div className="metrics mono">
              <span>🔋 {d.battery ?? "—"}%</span>
              <span>📶 {d.rssi ?? "—"} dBm</span>
            </div>}
            <div className="tags">
              {d.tags.map((t) => <span className="chip" key={t}>{t}</span>)}
            </div>
          </div>
        ))}
      </div>

      {sel && (
        <>
          <div className="drawer-bg" onClick={() => setSel(null)} />
          <div className="drawer">
            <div className="dhead">
              <div>
                <div className="mono" style={{ fontSize: 18, fontWeight: 700 }}>{sel.name}</div>
                <div className="muted" style={{ fontSize: 12 }}>{sel.external_id} · <span className={`stat ${sel.status}`}>{statusLabel(sel)}</span></div>
              </div>
              <button className="sm" onClick={() => setSel(null)}>✕</button>
            </div>
            <div className="body">
              <div className="metrics mono" style={{ fontSize: 13, marginBottom: 16 }}>
                <span>🔋 {sel.battery ?? "—"}%</span>
                <span>📶 {sel.rssi ?? "—"} dBm</span>
                <span>📍 {sel.lat.toFixed(3)}, {sel.lon.toFixed(3)}</span>
              </div>
              <p>{sourceLabel(sel)}</p>
              <p>Última recepción: {sel.last_seen ? new Date(sel.last_seen).toLocaleString("es-AR") : "Todavía no se recibieron datos"}</p>
              {sel.telemetry_mode === "mqtt" && !Object.keys(sel.latest_readings || {}).length && <p>Este nodo espera datos del dispositivo físico por MQTT. Si querés datos meteorológicos modelados, cambiá su fuente a Open-Meteo en la configuración de nodos.</p>}
              <label>Variable</label>
              <select value={variable} onChange={(e) => setVariable(e.target.value)}>
                {Array.from(new Set(["temp", "humidity", "soil_moisture", "precipitation", "wind_speed", "wind_gust", "vpd", "pm25", "mq4", "nivel", "turbidez", ...Object.keys(sel.latest_readings || {})])).map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
              <div className="muted" style={{ fontSize: 11, margin: "4px 0 8px" }}>Serie temporal · últimas 48h</div>
              {seriesError ? <p role="alert">{seriesError}</p> : loadingSeries ? <p>Cargando lecturas…</p> : series.length ? <Sparkline values={series.map((s) => s.value)} /> : <p>No hay lecturas de esta variable en las últimas 48 horas.</p>}
              <div className="metrics mono" style={{ marginTop: 8 }}>
                <span>{series.length} lecturas</span>
                {series.length > 0 && <span>último: {series[series.length - 1].value}</span>}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
