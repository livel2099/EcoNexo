"use client";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { WS, apiGet, apiPost, clearSession, getSession } from "../lib/api";
import type { Alert, Detection, Device, Kpi, Org, Report } from "../lib/types";
import DevicesPanel from "../../components/DevicesPanel";
import RulesPanel from "../../components/RulesPanel";
import ReportsPanel from "../../components/ReportsPanel";

const MapView = dynamic(() => import("../../components/MapView"), { ssr: false });

const BANNER: Record<string, string> = { normal: "Estado normal", atencion: "Atención", critico: "Estado crítico" };
type View = "comando" | "dispositivos" | "reglas" | "reportes";

function pct(v: number | null) { return v == null ? "—" : `${Math.round(v * 100)}%`; }
function since(iso: string) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `hace ${Math.round(s)}s`;
  if (s < 3600) return `hace ${Math.round(s / 60)}m`;
  if (s < 86400) return `hace ${Math.round(s / 3600)}h`;
  return `hace ${Math.round(s / 86400)}d`;
}
function confColor(c: number) { return c >= 0.85 ? "#37D08A" : c >= 0.6 ? "#D97706" : "#7f9488"; }

export default function Dashboard() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [org, setOrg] = useState<Org | null>(null);
  const [view, setView] = useState<View>("comando");
  const [kpi, setKpi] = useState<Kpi | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [feed, setFeed] = useState<string[]>([]);

  const refresh = useCallback(async (t: string) => {
    const [k, a, d, s, r] = await Promise.all([
      apiGet<Kpi>("/kpis", t), apiGet<Alert[]>("/alerts", t), apiGet<Device[]>("/devices", t),
      apiGet<Detection[]>("/satellite/detections?hours=48", t), apiGet<Report[]>("/reports", t),
    ]);
    setKpi(k); setAlerts(a); setDevices(d); setDetections(s); setReports(r);
  }, []);

  useEffect(() => {
    const sess = getSession();
    if (!sess) { router.replace("/login"); return; }
    setToken(sess.access_token);
    apiGet<Org>("/orgs/me", sess.access_token).then(setOrg).catch(() => {});
    refresh(sess.access_token).catch(() => {});
    const ws = new WebSocket(`${WS}/ws?token=${sess.access_token}`);
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      const line = m.kind === "alerts" ? `🚨 ${m.data.title} · ${Math.round((m.data.confidence || 0) * 100)}%`
        : m.kind === "reports" ? `👤 nuevo reporte: ${m.data.type}` : `📡 ${m.data.external_id || "telemetría"}`;
      setFeed((f) => [line, ...f].slice(0, 6));
      if (m.kind !== "readings") refresh(sess.access_token).catch(() => {});
    };
    const iv = setInterval(() => refresh(sess.access_token).catch(() => {}), 15000);
    return () => { ws.close(); clearInterval(iv); };
  }, [router, refresh]);

  async function act(id: string, action: string) {
    if (!token) return;
    await apiPost(`/alerts/${id}/action`, token, { action });
    await refresh(token);
  }

  const center: [number, number] = [-26.82, -54.45];
  const g = kpi?.global_status || "normal";
  const navItem = (v: View, label: string) => (
    <a className={view === v ? "active" : ""} onClick={() => setView(v)}>{label}</a>
  );

  return (
    <div className="shell">
      <div className="topbar">
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div className="brand">ECO<span>NEXO</span><small>{org?.name || "…"}</small></div>
          <nav className="nav">
            {navItem("comando", "Centro de Comando")}
            {navItem("dispositivos", "Dispositivos")}
            {navItem("reglas", "Reglas")}
            {navItem("reportes", "Reportes")}
          </nav>
        </div>
        <button onClick={() => { clearSession(); router.replace("/login"); }}>Salir</button>
      </div>

      <div className={`banner ${g} kpirow`}>
        <span className="dot" /> {BANNER[g]} · {kpi?.active_alerts ?? 0} alertas activas
      </div>

      <div className="kpis kpirow">
        <KpiCard title="⏱ Tiempo de detección" val={kpi?.detection_time_s != null ? `${kpi.detection_time_s}s` : "—"}
          target="< 5 min" good={(kpi?.detection_time_s ?? 1e9) < 300} ratio={kpi?.detection_time_s != null ? Math.min(1, 300 / Math.max(kpi.detection_time_s, 1)) : 0} />
        <KpiCard title="🎯 Precisión motor IA" val={pct(kpi?.model_precision ?? null)}
          target="85%+" good={(kpi?.model_precision ?? 0) >= 0.85} ratio={kpi?.model_precision ?? 0} />
        <KpiCard title="✓ Reportes válidos" val={pct(kpi?.valid_reports_rate ?? null)}
          target="70%+" good={(kpi?.valid_reports_rate ?? 0) >= 0.7} ratio={kpi?.valid_reports_rate ?? 0} />
        <KpiCard title="⚡ Reducción respuesta" val={pct(kpi?.response_time_reduction ?? null)}
          target="-40%" good={(kpi?.response_time_reduction ?? 0) >= 0.4} ratio={kpi?.response_time_reduction ?? 0} />
      </div>

      <div className="feedbar kpirow">
        <span className="live"><span className="dot" /> EN VIVO</span>
        <span className="mono muted">{feed[0] || "esperando telemetría del bus MQTT…"}</span>
      </div>

      {view === "comando" ? (
        <>
          <div className="mapwrap">
            <MapView devices={devices} alerts={alerts} detections={detections} reports={reports} center={center} />
            <div className="legend">
              <div className="li"><span className="sw" style={{ background: "#37D08A" }} /> Nodo online</div>
              <div className="li"><span className="sw" style={{ background: "#f97316" }} /> Foco satélite (FIRMS)</div>
              <div className="li"><span className="sw" style={{ background: "#DC2626" }} /> Alerta crítica</div>
              <div className="li"><span className="sw" style={{ background: "#3b82f6" }} /> Reporte ciudadano</div>
            </div>
          </div>
          <div className="side">
            <h3>Alertas priorizadas <span className="count">{alerts.length}</span></h3>
            {alerts.length === 0 && <div className="empty">Sin alertas activas.</div>}
            {alerts.map((a) => (
              <div className="alert" key={a.id}>
                <div className="row">
                  <span className={`sev ${a.severity}`}>{a.severity}</span>
                  <span className="conf" style={{ color: confColor(a.confidence) }}>{Math.round(a.confidence * 100)}%</span>
                </div>
                <div className="ttl">{a.title}</div>
                <div className="muted mono" style={{ fontSize: 11 }}>{a.type} · {a.status} · {since(a.detected_at)}</div>
                <div className="confbar"><i style={{ width: `${a.confidence * 100}%`, background: confColor(a.confidence) }} /></div>
                <div className="pills">
                  {a.sources.map((s, i) => <span className={`pill ${s.source_type}`} key={i}>{s.source_type}</span>)}
                </div>
                <div className="acts">
                  <button className="primary sm" onClick={() => act(a.id, "confirmar")}>Confirmar</button>
                  <button className="sm" onClick={() => act(a.id, "descartar")}>Descartar</button>
                  <button className="sm" onClick={() => act(a.id, "escalar")}>Escalar</button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : token && view === "dispositivos" ? <DevicesPanel token={token} />
        : token && view === "reglas" ? <RulesPanel token={token} />
        : token ? <ReportsPanel token={token} /> : null}
    </div>
  );
}

function KpiCard({ title, val, target, good, ratio }: { title: string; val: string; target: string; good: boolean; ratio: number }) {
  const col = good ? "#37D08A" : "#D97706";
  return (
    <div className="kpi">
      <h4>{title}</h4>
      <div className={`val ${good ? "ok" : "bad"}`}>{val}</div>
      <div className="tgt">objetivo {target}</div>
      <div className="bar"><i style={{ width: `${Math.round(Math.min(1, Math.max(0, ratio)) * 100)}%`, background: col }} /></div>
    </div>
  );
}
