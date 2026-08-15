"use client";
import { useEffect, useState } from "react";
import { apiGet } from "../app/lib/api";
import type { Device } from "../app/lib/types";
import Sparkline from "./Sparkline";

// Vista de gestion de dispositivos + drawer de detalle con series temporales.
export default function DevicesPanel({ token }: { token: string }) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [sel, setSel] = useState<Device | null>(null);
  const [variable, setVariable] = useState<string>("temp");
  const [series, setSeries] = useState<{ ts: string; value: number }[]>([]);

  useEffect(() => { apiGet<Device[]>("/devices", token).then(setDevices).catch(() => {}); }, [token]);

  useEffect(() => {
    if (!sel) return;
    apiGet<{ ts: string; value: number }[]>(`/devices/${sel.id}/readings?variable=${variable}&hours=48`, token)
      .then(setSeries).catch(() => setSeries([]));
  }, [sel, variable, token]);

  const online = devices.filter((d) => d.status === "online").length;

  return (
    <div className="view">
      <h2>Red de hardware</h2>
      <div className="sub">{devices.length} nodos · <span style={{ color: "#37D08A" }}>{online} online</span> · heartbeat MQTT</div>
      <div className="grid-cards">
        {devices.map((d) => (
          <div className="dcard" key={d.id} onClick={() => { setSel(d); setVariable("temp"); }}>
            <div className="dh">
              <span className="nm">{d.name}</span>
              <span className={`stat ${d.status}`}>● {d.status}</span>
            </div>
            <div className="metrics mono">
              <span>🔋 {d.battery ?? "—"}%</span>
              <span>📶 {d.rssi ?? "—"} dBm</span>
            </div>
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
                <div className="muted" style={{ fontSize: 12 }}>{sel.external_id} · <span className={`stat ${sel.status}`}>{sel.status}</span></div>
              </div>
              <button className="sm" onClick={() => setSel(null)}>✕</button>
            </div>
            <div className="body">
              <div className="metrics mono" style={{ fontSize: 13, marginBottom: 16 }}>
                <span>🔋 {sel.battery ?? "—"}%</span>
                <span>📶 {sel.rssi ?? "—"} dBm</span>
                <span>📍 {sel.lat.toFixed(3)}, {sel.lon.toFixed(3)}</span>
              </div>
              <label>Variable</label>
              <select value={variable} onChange={(e) => setVariable(e.target.value)}>
                {["temp", "humidity", "pm25", "mq4", "nivel", "turbidez"].map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
              <div className="muted" style={{ fontSize: 11, margin: "4px 0 8px" }}>Serie temporal · últimas 48h</div>
              <Sparkline values={series.map((s) => s.value)} />
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
