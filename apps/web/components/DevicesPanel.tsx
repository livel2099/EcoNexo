"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "../app/lib/api";
import type { Device } from "../app/lib/types";
import Sparkline from "./Sparkline";

const VARIABLE_LABEL: Record<string, string> = {
  temp: "Temperatura",
  humidity: "Humedad relativa",
  soil_moisture: "Humedad del suelo",
  precipitation: "Precipitación",
  wind_speed: "Viento",
  wind_gust: "Ráfagas",
  vpd: "Déficit de presión de vapor",
  pm25: "PM2.5",
  mq4: "MQ-4",
  nivel: "Nivel",
  turbidez: "Turbidez",
};

function readingUnit(variable: string): string {
  if (variable === "temp") return "°C";
  if (["humidity", "soil_moisture"].includes(variable)) return "%";
  if (variable === "precipitation") return "mm";
  if (["wind_speed", "wind_gust"].includes(variable)) return "km/h";
  if (variable === "vpd") return "kPa";
  if (variable === "pm25") return "µg/m³";
  return "";
}

function latestEntries(device: Device): Array<[string, number]> {
  return Object.entries(device.latest_readings || {})
    .filter((entry): entry is [string, number] => typeof entry[1] === "number")
    .slice(0, 6);
}

export default function DevicesPanel({ token }: { token: string }) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [sel, setSel] = useState<Device | null>(null);
  const [variable, setVariable] = useState<string>("temp");
  const [series, setSeries] = useState<{ ts: string; value: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const next = await apiGet<Device[]>("/devices", token);
      setDevices(next);
      if (sel) {
        setSel(next.find((item) => item.id === sel.id) || null);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo cargar la red");
    } finally {
      setLoading(false);
    }
  }, [token, sel?.id]);

  useEffect(() => {
    void load();
    const timer = globalThis.setInterval(() => void load(), 30_000);
    return () => globalThis.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (!sel) return;
    void apiGet<{ ts: string; value: number }[]>(
      `/devices/${sel.id}/readings?variable=${encodeURIComponent(variable)}&hours=48`,
      token,
    ).then(setSeries).catch(() => setSeries([]));
  }, [sel, variable, token]);

  const online = devices.filter((device) => device.status === "online").length;
  const virtual = devices.filter((device) => device.telemetry_mode === "open_meteo").length;
  const availableVariables = useMemo(() => {
    if (!sel) return ["temp", "humidity", "soil_moisture", "wind_gust"];
    const keys = Object.keys(sel.latest_readings || {});
    return keys.length ? keys : ["temp", "humidity", "soil_moisture", "wind_gust"];
  }, [sel]);

  useEffect(() => {
    if (availableVariables.length && !availableVariables.includes(variable)) {
      setVariable(availableVariables[0]);
    }
  }, [availableVariables, variable]);

  return (
    <div className="view devices-view">
      <div className="view-title-row">
        <div><span className="eyebrow">RED DE TELEMETRÍA</span><h2>Dispositivos y nodos ambientales</h2><p className="sub">{devices.length} nodos · {online} online · {virtual} virtuales Open-Meteo</p></div>
        <button className="secondary" disabled={loading} onClick={() => void load()}>{loading ? "Actualizando…" : "Actualizar red"}</button>
      </div>
      {error && <div className="workspace-message error" role="alert">{error}</div>}

      {!loading && !devices.length && <section className="device-empty-state">
        <span className="device-empty-orbit"><i /><i /><i /></span>
        <div><span className="eyebrow">RED VACÍA</span><h3>Configurá la telemetría desde Admin Core</h3><p>Podés crear nodos físicos MQTT o una red virtual con Open-Meteo. Elegí cuadro, triángulo o círculo y vinculalos a una geocerca.</p><strong>Admin Core → Telemetría → Crear red inicial y ejecutar</strong></div>
      </section>}

      <div className="grid-cards device-grid-enhanced">
        {devices.map((device) => (
          <button className="dcard device-card-button" type="button" key={device.id} onClick={() => { setSel(device); setVariable(Object.keys(device.latest_readings || {})[0] || "temp"); }}>
            <div className="dh">
              <span className="device-card-identity"><i className={`telemetry-shape ${device.marker_shape}`} /><span className="nm">{device.name}</span></span>
              <span className={`stat ${device.status}`}>● {device.status}</span>
            </div>
            <div className="device-mode-row"><span>{device.telemetry_mode === "open_meteo" ? "contexto modelado" : device.telemetry_mode}</span><span>{device.zone_name || "sin zona"}</span></div>
            <div className="device-latest-grid">
              {latestEntries(device).map(([key, value]) => <span key={key}><small>{VARIABLE_LABEL[key] || key}</small><strong>{value.toLocaleString("es-AR", { maximumFractionDigits: 2 })}{readingUnit(key)}</strong></span>)}
              {!latestEntries(device).length && <span className="device-no-readings">Sin lecturas. Ejecutá el pipeline.</span>}
            </div>
            <div className="tags">{device.tags.map((tag) => <span className="chip" key={tag}>{tag}</span>)}</div>
            <small className="device-pipeline-state">{device.last_pipeline_status || "pipeline pendiente"}</small>
          </button>
        ))}
      </div>

      {sel && <>
        <div className="drawer-bg" onClick={() => setSel(null)} />
        <div className="drawer device-detail-drawer">
          <div className="dhead">
            <div><div className="mono" style={{ fontSize: 18, fontWeight: 700 }}>{sel.name}</div><div className="muted" style={{ fontSize: 12 }}>{sel.external_id} · <span className={`stat ${sel.status}`}>{sel.status}</span></div></div>
            <button className="sm" onClick={() => setSel(null)}>✕</button>
          </div>
          <div className="body">
            <div className="device-detail-meta"><span><b>Fuente</b>{sel.telemetry_mode}</span><span><b>Forma</b>{sel.marker_shape}</span><span><b>Zona</b>{sel.zone_name || "sin zona"}</span><span><b>Ubicación</b>{sel.lat.toFixed(5)}, {sel.lon.toFixed(5)}</span><span><b>Última lectura</b>{sel.last_seen ? new Date(sel.last_seen).toLocaleString("es-AR") : "sin registro"}</span><span><b>Pipeline</b>{sel.last_pipeline_status || "pendiente"}</span></div>
            <label>Variable</label>
            <select value={variable} onChange={(event) => setVariable(event.target.value)}>{availableVariables.map((item) => <option key={item} value={item}>{VARIABLE_LABEL[item] || item}</option>)}</select>
            <div className="muted" style={{ fontSize: 11, margin: "8px 0" }}>Serie temporal · últimas 48 horas</div>
            <Sparkline values={series.map((item) => item.value)} />
            <div className="metrics mono" style={{ marginTop: 8 }}><span>{series.length} lecturas</span>{series.length > 0 && <span>último: {series[series.length - 1].value.toLocaleString("es-AR")}{readingUnit(variable)}</span>}</div>
          </div>
        </div>
      </>}
    </div>
  );
}
