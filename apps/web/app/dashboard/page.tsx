"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { IS_DEMO, WS, apiGet, apiPost, clearSession, getSession } from "../lib/api";
import type { EarthIntel } from "../lib/earth-intel";
import type { Alert, Detection, Device, EnvironmentalSourceSettings, Kpi, Org, PipelineRun, Report, RiskZone, Session } from "../lib/types";
import { buildSpaceAIThreatAssessment } from "../lib/spaceai";
import { MISIONES_CENTER, isInMisiones, misionesLocationLabel } from "../lib/misiones";
import { useCollapsible } from "../lib/use-collapsible";
import DevicesPanel from "../../components/DevicesPanel";
import EarthIntelBar from "../../components/EarthIntelBar";
import ReportsPanel from "../../components/ReportsPanel";
import ImpactReportsPanel from "../../components/ImpactReportsPanel";
import RulesPanel from "../../components/RulesPanel";
import ObservatoryPanel from "../../components/ObservatoryPanel";
import AdminPanel from "../../components/AdminPanel";
import CircuitBackdrop from "../../components/CircuitBackdrop";
import FireSmokePanel from "../../components/FireSmokePanel";
import ForestryPestPanel from "../../components/ForestryPestPanel";

import AgroPanel from "../../components/AgroPanel";

const MapView = dynamic(() => import("../../components/MapView"), { ssr: false });
const COMMAND_CENTER: [number, number] = MISIONES_CENTER;
const BANNER: Record<string, string> = { normal: "Estado normal", atencion: "Atención", critico: "Estado crítico" };

const DEFAULT_SOURCE_SETTINGS: EnvironmentalSourceSettings = {
  org_id: "pending",
  default_latitude: COMMAND_CENTER[0],
  default_longitude: COMMAND_CENTER[1],
  open_meteo_enabled: true,
  air_quality_enabled: true,
  flood_enabled: true,
  firms_enabled: true,
  copernicus_enabled: true,
  copernicus_use_system_default: true,
  copernicus_wms_url: null,
  copernicus_true_color_layer: "TRUE_COLOR",
  copernicus_ndvi_layer: "NDVI",
  copernicus_moisture_layer: "NDMI",
  copernicus_burn_layer: "NBR",
  forestry_pest_enabled: true,
  sinarame_radar_enabled: true,
  refresh_minutes: 10,
  fire_radius_km: 50,
  operational_alert_min_level: "R3",
  auto_activate_alerts: false,
  firms_map_key_configured: false,
  copernicus_configured: false,
  copernicus_provider: "none",
  copernicus_process_configured: false,
  copernicus_wms_configured: false,
  copernicus_system_default: true,
  copernicus_effective_wms_url: null,
  copernicus_last_test_at: null,
  copernicus_last_test_ok: null,
  copernicus_last_error: null,
  copernicus_available_layers: [],
  updated_at: new Date(0).toISOString(),
};

type View = "comando" | "fuego" | "plagas" | "agro" | "observatorio" | "dispositivos" | "reglas" | "reportes" | "informes" | "admin";

function pct(value: number | null) {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

function since(iso: string) {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return `hace ${Math.round(seconds)}s`;
  if (seconds < 3600) return `hace ${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `hace ${Math.round(seconds / 3600)}h`;
  return `hace ${Math.round(seconds / 86400)}d`;
}

function confidenceColor(confidence: number) {
  return confidence >= 0.85 ? "#8ff06a" : confidence >= 0.6 ? "#ffd166" : "#7f948f";
}

export default function Dashboard() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [org, setOrg] = useState<Org | null>(null);
  const [view, setView] = useState<View>("comando");
  const [kpi, setKpi] = useState<Kpi | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [zones, setZones] = useState<RiskZone[]>([]);
  const [lastPipeline, setLastPipeline] = useState<PipelineRun | null>(null);
  const [pipelineBusy, setPipelineBusy] = useState(false);
  const [pipelineNotice, setPipelineNotice] = useState("");
  const [feed, setFeed] = useState<string[]>([]);
  const [earthIntel, setEarthIntel] = useState<EarthIntel | null>(null);
  const [sourceSettings, setSourceSettings] = useState<EnvironmentalSourceSettings>(DEFAULT_SOURCE_SETTINGS);
  // Paneles plegables. El mapa recupera el espacio liberado por si solo: su
  // ResizeObserver detecta el cambio de contenedor y reencuadra.
  const [kpisOpen, toggleKpis] = useCollapsible("kpis");
  const [earthOpen, toggleEarth] = useCollapsible("earth");
  const [alertsOpen, toggleAlerts] = useCollapsible("alerts");

  const refresh = useCallback(async (accessToken: string) => {
    const [nextKpi, nextAlerts, nextDevices, nextDetections, nextReports, nextZones, pipelineRuns] = await Promise.all([
      apiGet<Kpi>("/kpis", accessToken),
      apiGet<Alert[]>("/alerts", accessToken),
      apiGet<Device[]>("/devices", accessToken),
      apiGet<Detection[]>("/satellite/detections?hours=48", accessToken),
      apiGet<Report[]>("/reports", accessToken),
      apiGet<RiskZone[]>("/zones", accessToken),
      apiGet<PipelineRun[]>("/pipeline/runs?limit=1", accessToken).catch(() => []),
    ]);
    setKpi(nextKpi);
    setAlerts(nextAlerts);
    setDevices(nextDevices);
    setDetections(nextDetections);
    setReports(nextReports);
    setZones(nextZones);
    setLastPipeline(pipelineRuns[0] || null);
  }, []);

  useEffect(() => {
    const session = getSession();
    if (!session) {
      router.replace("/login");
      return;
    }
    if (session.must_change_password) {
      router.replace("/cambiar-contrasena");
      return;
    }
    if (session.account_type === "community") {
      router.replace("/red-investigacion");
      return;
    }
    setSession(session);
    setToken(session.access_token);
    void apiGet<Org>("/orgs/me", session.access_token).then(setOrg).catch(() => undefined);
    void apiGet<EnvironmentalSourceSettings>("/environment/source-settings", session.access_token).then(setSourceSettings).catch(() => undefined);
    void refresh(session.access_token).catch(() => undefined);

    let stopLiveFeed: () => void;
    if (IS_DEMO) {
      const demoEvents = [
        "Nodo Arroyo Verde · telemetría recibida",
        "Copernicus Sentinel‑2 · mosaico actualizado",
        "Open‑Meteo · contexto meteorológico sincronizado",
        "CAMS · aerosoles y material particulado actualizados",
        "Reporte ciudadano validado · presencia de humo",
      ];
      let index = 0;
      setFeed(["Demo geoespacial ejecutándose en Cloudflare"]);
      const demoInterval = window.setInterval(() => {
        setFeed((current) => [demoEvents[index++ % demoEvents.length], ...current].slice(0, 6));
      }, 4500);
      stopLiveFeed = () => window.clearInterval(demoInterval);
    } else {
      const websocket = new WebSocket(`${WS}/ws?token=${session.access_token}`);
      websocket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        const line = message.kind === "alerts"
          ? `Alerta · ${message.data.title} · ${Math.round((message.data.confidence || 0) * 100)}%`
          : message.kind === "reports"
            ? `Nuevo reporte · ${message.data.type}`
            : message.kind === "pipeline"
              ? `Pipeline · ${message.data.devices_updated || 0} nodos · ${message.data.readings_inserted || 0} lecturas`
              : `Telemetría · ${message.data.external_id || "nodo sin identificar"}`;
        setFeed((current) => [line, ...current].slice(0, 6));
        if (message.kind === "pipeline" || message.kind === "alerts" || message.kind === "reports") {
          void refresh(session.access_token).catch(() => undefined);
        }
      };
      stopLiveFeed = () => websocket.close();
    }

    const refreshInterval = window.setInterval(() => void refresh(session.access_token).catch(() => undefined), 15_000);
    return () => {
      stopLiveFeed();
      window.clearInterval(refreshInterval);
    };
  }, [refresh, router]);

  async function act(id: string, action: string) {
    if (!token) return;
    await apiPost(`/alerts/${id}/action`, token, { action });
    await refresh(token);
  }

  async function runCommandPipeline() {
    if (!token || pipelineBusy) return;
    setPipelineBusy(true);
    setPipelineNotice("");
    try {
      if (!devices.length && session?.role === "admin") {
        await apiPost("/pipeline/bootstrap", token, { count: 2, zone_id: zones[0]?.id || null });
      }
      const run = await apiPost<PipelineRun>("/pipeline/run", token, {});
      setLastPipeline(run);
      setPipelineNotice(`${run.devices_updated}/${run.devices_total} nodos · ${run.readings_inserted} lecturas · ${run.detections_ingested} focos · ${run.alerts_created} alertas`);
      setFeed((current) => [`Pipeline ${run.status} · ${run.readings_inserted} lecturas actualizadas`, ...current].slice(0, 6));
      await refresh(token);
    } catch (cause) {
      setPipelineNotice(cause instanceof Error ? cause.message : "No se pudo ejecutar el pipeline");
    } finally {
      setPipelineBusy(false);
    }
  }

  const globalStatus = kpi?.global_status || "normal";
  const commandCenter: [number, number] = isInMisiones(sourceSettings.default_latitude, sourceSettings.default_longitude)
    ? [sourceSettings.default_latitude, sourceSettings.default_longitude]
    : MISIONES_CENTER;
  const localDevices = useMemo(() => devices.filter((item) => isInMisiones(item.lat, item.lon)), [devices]);
  const localAlerts = useMemo(() => alerts.filter((item) => isInMisiones(item.lat, item.lon)), [alerts]);
  const localDetections = useMemo(() => detections.filter((item) => isInMisiones(item.lat, item.lon)), [detections]);
  const localReports = useMemo(() => reports.filter((item) => isInMisiones(item.lat, item.lon)), [reports]);
  const localZones = useMemo(() => zones.filter((item) => isInMisiones(item.lat, item.lon)), [zones]);
  const ignoredExternalSignals = (devices.length - localDevices.length) + (alerts.length - localAlerts.length)
    + (detections.length - localDetections.length) + (reports.length - localReports.length);
  const commandAssessment = useMemo(() => buildSpaceAIThreatAssessment(earthIntel, localDetections, { fireRadiusKm: sourceSettings.fire_radius_km, firmsEnabled: sourceSettings.firms_enabled }), [earthIntel, localDetections, sourceSettings.fire_radius_km, sourceSettings.firms_enabled]);
  const navItem = (target: View, label: string) => (
    <button className={view === target ? "active" : ""} onClick={() => setView(target)}>{label}</button>
  );

  return (
    <main className={`shell tech-shell${kpisOpen ? "" : " kpis-collapsed"}${earthOpen ? "" : " earth-collapsed"}${alertsOpen ? "" : " alerts-collapsed"}`}>
      <CircuitBackdrop dense />
      <header className="topbar">
        <div className="topbar-main">
          <img className="topbar-official-logo" src="/brand/econexo-lockup.jpg" alt="EcoNexo" />
          <span className="topbar-org">{org?.name || "conectando…"}<small>{org?.municipality ? `${org.municipality} · ` : ""}Misiones</small></span>
          <span className="orbital-status"><i /> órbita activa</span>
          <nav className="nav" aria-label="Navegación principal">
            {navItem("comando", "Centro de Comando")}
            {navItem("fuego", "Fuego y humo")}
            {navItem("plagas", "Plagas forestales")}
            {navItem("agro", "EcoNexo AG")}
            {navItem("observatorio", "Alerta IA")}
            {navItem("dispositivos", "Dispositivos")}
            {navItem("reglas", "Reglas")}
            {navItem("reportes", "Reportes ciudadanos")}
            {navItem("informes", "Informes")}
            <button className="foi-nav-link" onClick={() => router.push("/red-investigacion")}>EcoNexoFoI</button>
            {session?.role === "admin" && navItem("admin", "Admin Core")}
          </nav>
        </div>
        <div className="account-area">
          <div className="account-chip">
            {session?.avatar_url ? <img src={session.avatar_url} alt="" referrerPolicy="no-referrer" /> : <span>{session?.name?.slice(0, 1).toUpperCase() || "E"}</span>}
            <div><strong>{session?.name || "Usuario"}</strong><small>{session?.auth_provider === "google" ? "Google · " : ""}{session?.role || ""}</small></div>
          </div>
          <button className="logout" onClick={() => { clearSession(); router.replace("/"); }}>Salir</button>
        </div>
      </header>

      <div className={`banner ${globalStatus} kpirow`}>
        <span className="dot" /> {BANNER[globalStatus]} · {localAlerts.filter((item) => !["descartada", "resuelta"].includes(item.status)).length} alertas activas en Misiones
        <small>{misionesLocationLabel(commandCenter[0], commandCenter[1])} · 17 departamentos · 79 municipios{ignoredExternalSignals ? ` · ${ignoredExternalSignals} señales externas excluidas` : ""}</small>
        <button
          type="button"
          className="panel-pill banner-pill"
          onClick={toggleKpis}
          aria-expanded={kpisOpen}
          aria-controls="kpi-row"
        >
          <span aria-hidden="true">{kpisOpen ? "▾" : "▸"}</span> Indicadores
        </button>
      </div>

      <section className="kpis kpirow" id="kpi-row" aria-label="Indicadores principales" hidden={!kpisOpen}>
        <KpiCard title="Tiempo de detección" val={kpi?.detection_time_s != null ? `${kpi.detection_time_s}s` : "—"}
          target="< 5 min" good={(kpi?.detection_time_s ?? 1e9) < 300} ratio={kpi?.detection_time_s != null ? Math.min(1, 300 / Math.max(kpi.detection_time_s, 1)) : 0} />
        <KpiCard title="Precisión motor IA" val={pct(kpi?.model_precision ?? null)}
          target="85%+" good={(kpi?.model_precision ?? 0) >= 0.85} ratio={kpi?.model_precision ?? 0} />
        <KpiCard title="Reportes válidos" val={pct(kpi?.valid_reports_rate ?? null)}
          target="70%+" good={(kpi?.valid_reports_rate ?? 0) >= 0.7} ratio={kpi?.valid_reports_rate ?? 0} />
        <KpiCard title="Reducción respuesta" val={pct(kpi?.response_time_reduction ?? null)}
          target="-40%" good={(kpi?.response_time_reduction ?? 0) >= 0.4} ratio={kpi?.response_time_reduction ?? 0} />
      </section>

      <EarthIntelBar lat={commandCenter[0]} lon={commandCenter[1]} onUpdate={setEarthIntel} collapsed={!earthOpen} onToggle={toggleEarth} />

      <div className="feedbar kpirow command-pipeline-bar">
        <span className="live"><span className="dot" /> EN VIVO</span>
        <span className="mono muted">{feed[0] || "Pipeline listo para sincronizar telemetría, reglas y focos"}</span>
        <span className="pipeline-last-run">{pipelineNotice || (lastPipeline ? `Última corrida: ${lastPipeline.status} · ${lastPipeline.readings_inserted} lecturas` : "Sin corridas")}</span>
        <button type="button" className="pipeline-run-button" disabled={pipelineBusy || !token} onClick={() => void runCommandPipeline()}>{pipelineBusy ? "Actualizando…" : devices.length ? "Ejecutar pipeline" : session?.role === "admin" ? "Crear red y ejecutar" : "Ejecutar pipeline"}</button>
      </div>

      {view === "comando" ? (
        <>
          <section className="mapwrap" aria-label="Mapa operacional">
            <MapView token={token} devices={localDevices} alerts={localAlerts} detections={localDetections} reports={localReports} zones={localZones} center={commandCenter} earth={earthIntel} sourceSettings={sourceSettings} initialSatelliteMode="TRUE_COLOR" />
            <div className="legend">
              <div className="li"><span className="sw" style={{ background: "#8ff06a" }} /> Nodo online</div>
              <div className="li"><span className="sw" style={{ background: "#ff9f45" }} /> Foco satelital</div>
              <div className="li"><span className="sw" style={{ background: "#ff5d52" }} /> Alerta crítica</div>
              <div className="li"><span className="sw" style={{ background: "#33daff" }} /> Reporte ciudadano</div>
            </div>
          </section>
          {!alertsOpen && (
            <button
              type="button"
              className="panel-pill side-reopen"
              onClick={toggleAlerts}
              aria-expanded={false}
              aria-controls="alerts-rail"
            >
              <span aria-hidden="true">◂</span> Alertas <span className="count">{localAlerts.length}</span>
            </button>
          )}
          <aside className="side" id="alerts-rail" hidden={!alertsOpen}>
            <h3>
              Alertas priorizadas en Misiones <span className="count">{localAlerts.length}</span>
              <button
                type="button"
                className="panel-toggle side-toggle"
                onClick={toggleAlerts}
                aria-expanded
                aria-controls="alerts-rail"
                title="Plegar alertas"
              >
                <span aria-hidden="true">▸</span>
                <span className="sr-only">Plegar alertas</span>
              </button>
            </h3>
            {localAlerts.length === 0 && <div className="empty">Sin alertas activas.</div>}
            {localAlerts.map((alert) => (
              <article className="alert" key={alert.id}>
                <div className="row">
                  <span className={`sev ${alert.severity}`}>{alert.severity}</span>
                  <span className="conf" style={{ color: confidenceColor(alert.confidence) }}>{Math.round(alert.confidence * 100)}%</span>
                </div>
                <div className="ttl">{alert.title}</div>
                <div className="muted mono alert-meta">{alert.type} · {alert.status} · {since(alert.detected_at)}</div>
                <div className="confbar"><i style={{ width: `${alert.confidence * 100}%`, background: confidenceColor(alert.confidence) }} /></div>
                <div className="pills">
                  {alert.sources.map((source, index) => <span className={`pill ${source.source_type}`} key={index}>{source.source_type}</span>)}
                </div>
                <div className="acts">
                  <button className="primary sm" onClick={() => void act(alert.id, "confirmar")}>Confirmar</button>
                  <button className="sm" onClick={() => void act(alert.id, "descartar")}>Descartar</button>
                  <button className="sm" onClick={() => void act(alert.id, "escalar")}>Escalar</button>
                </div>
              </article>
            ))}
          </aside>
        </>
      ) : token && view === "fuego" ? <FireSmokePanel token={token} org={org} devices={localDevices} alerts={localAlerts} detections={localDetections} zones={localZones} earth={earthIntel} center={commandCenter} sourceSettings={sourceSettings} />
        : token && view === "agro" ? <AgroPanel token={token} />
        : token && view === "plagas" ? <ForestryPestPanel token={token} devices={localDevices} alerts={localAlerts} detections={localDetections} zones={localZones} sourceSettings={sourceSettings} />
        : token && view === "observatorio" ? <ObservatoryPanel token={token} devices={localDevices} detections={localDetections} commandIntel={earthIntel} commandAssessment={commandAssessment} sourceSettings={sourceSettings} />
        : token && view === "dispositivos" ? <DevicesPanel token={token} />
          : token && view === "reglas" ? <RulesPanel token={token} />
            : token && view === "reportes" ? <ReportsPanel token={token} />
              : token && view === "informes" ? <ImpactReportsPanel token={token} />
                : token && view === "admin" && session?.role === "admin" ? <AdminPanel token={token} org={org} onOrgUpdate={setOrg} onSourceSettingsUpdate={setSourceSettings} /> : null}
    </main>
  );
}

function KpiCard({ title, val, target, good, ratio }: { title: string; val: string; target: string; good: boolean; ratio: number }) {
  const color = good ? "#8ff06a" : "#ffd166";
  return (
    <article className="kpi">
      <h4>{title}</h4>
      <div className={`val ${good ? "ok" : "bad"}`}>{val}</div>
      <div className="tgt">objetivo {target}</div>
      <div className="bar"><i style={{ width: `${Math.round(Math.min(1, Math.max(0, ratio)) * 100)}%`, background: color }} /></div>
    </article>
  );
}
