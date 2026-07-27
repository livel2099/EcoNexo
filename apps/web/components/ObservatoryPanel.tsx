"use client";

import { useEffect, useId, useMemo, useState, type CSSProperties } from "react";
import { apiGet, apiPost } from "../app/lib/api";
import { fetchEarthIntel, type EarthIntel, type EarthIntelOptions } from "../app/lib/earth-intel";
import { buildSpaceAIThreatAssessment, levelLabel, type SpaceAIThreatAssessment } from "../app/lib/spaceai";
import type { AlertShareInput, AlertShareResult, Detection, Device, EnvironmentalSnapshotRecord, EnvironmentalSourceSettings, SpaceAILevel } from "../app/lib/types";

interface Reading {
  ts: string;
  value: number;
}

interface Props {
  token: string;
  devices: Device[];
  detections: Detection[];
  commandIntel: EarthIntel | null;
  commandAssessment: SpaceAIThreatAssessment | null;
  sourceSettings: EnvironmentalSourceSettings;
}

const LEVEL_COLOR: Record<SpaceAILevel, string> = {
  R0: "#8ff06a",
  R1: "#8fd7b7",
  R2: "#ffd166",
  R3: "#ff9f45",
  R4: "#ff6f5f",
  R5: "#ff3f55",
};

function fmt(value: number | null | undefined, unit = "", digits = 1): string {
  return value == null || !Number.isFinite(value) ? "—" : `${value.toFixed(digits)}${unit}`;
}

function latest(readings: Reading[]): Reading | null {
  return readings.length ? readings[readings.length - 1] : null;
}

function linePath(values: Array<number | null>, width = 520, height = 140): string {
  const clean = values.map((value, index) => ({ value, index })).filter((item): item is { value: number; index: number } => item.value != null);
  if (clean.length < 2) return "";
  const min = Math.min(...clean.map((item) => item.value));
  const max = Math.max(...clean.map((item) => item.value));
  const range = Math.max(max - min, 1);
  return clean.map((item, order) => {
    const x = order / (clean.length - 1) * width;
    const y = height - 12 - (item.value - min) / range * (height - 24);
    return `${order ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function sourceHealth(intel: EarthIntel | null): number {
  if (!intel) return 0;
  const enabled = Object.values(intel.sources).filter((state) => state !== "disabled");
  if (!enabled.length) return 0;
  const live = enabled.filter((state) => state === "live").length;
  return Math.round(live / enabled.length * 100);
}

function Gauge({ assessment }: { assessment: SpaceAIThreatAssessment | null }) {
  const score = assessment?.overallScore ?? 0;
  const level = assessment?.overallLevel ?? "R0";
  const color = LEVEL_COLOR[level];
  return (
    <div className="hti-gauge" style={{ "--hti": `${score * 3.6}deg`, "--hti-color": color } as CSSProperties}>
      <div className="hti-gauge-inner">
        <span>HEALTH THREAT INDEX</span>
        <strong>{assessment ? Math.round(score) : "—"}</strong>
        <b>{level} · {levelLabel(level)}</b>
      </div>
      <i className="hti-orbit orbit-a" /><i className="hti-orbit orbit-b" /><i className="hti-orbit orbit-c" />
    </div>
  );
}

function NeuralCircuit({ assessment }: { assessment: SpaceAIThreatAssessment | null }) {
  const pulse = assessment?.overallScore ?? 0;
  const uid = useId().replaceAll(":", "");
  const gradientId = `circuitGradient-${uid}`;
  const glowId = `neuralGlow-${uid}`;
  const iotPathId = `iotPath-${uid}`;
  const weatherPathId = `weatherPath-${uid}`;
  const satellitePathId = `satPath-${uid}`;
  const outputPathId = `outputPath-${uid}`;
  return (
    <div className="neural-circuit" aria-label="Circuito de integración de datos SpaceAI">
      <svg viewBox="0 0 680 250" role="img" aria-label="IoT, meteorología, satélite e inteligencia artificial convergen en alertas e informes">
        <defs>
          <linearGradient id={gradientId} x1="0" x2="1">
            <stop offset="0" stopColor="#33daff" stopOpacity=".25" />
            <stop offset=".52" stopColor="#8ff06a" />
            <stop offset="1" stopColor="#a78bff" stopOpacity=".3" />
          </linearGradient>
          <filter id={glowId}><feGaussianBlur stdDeviation="3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <path id={iotPathId} className="circuit-path" d="M72 54 H188 Q220 54 220 86 V125 H292" />
        <path id={weatherPathId} className="circuit-path" d="M72 126 H292" />
        <path id={satellitePathId} className="circuit-path" d="M72 198 H188 Q220 198 220 164 V125 H292" />
        <path id={outputPathId} className="circuit-path output" d="M388 125 H472 Q506 125 506 88 H610" />
        <path className="circuit-path output" d="M388 125 H472 Q506 125 506 174 H610" />
        <circle className="circuit-node source" cx="72" cy="54" r="18" /><circle className="circuit-node source" cx="72" cy="126" r="18" /><circle className="circuit-node source" cx="72" cy="198" r="18" />
        <circle className="circuit-node core" cx="340" cy="125" r="48" style={{ opacity: .68 + pulse / 320 }} />
        <circle className="circuit-core-ring" cx="340" cy="125" r="62" />
        <circle className="circuit-node output" cx="610" cy="88" r="18" /><circle className="circuit-node output" cx="610" cy="174" r="18" />
        <text x="72" y="58" textAnchor="middle">IoT</text><text x="72" y="130" textAnchor="middle">MET</text><text x="72" y="202" textAnchor="middle">SAT</text>
        <text className="core-title" x="340" y="120" textAnchor="middle">SPACEAI</text><text className="core-score" x="340" y="139" textAnchor="middle">HTI {Math.round(pulse)}</text>
        <text x="610" y="92" textAnchor="middle">ALR</text><text x="610" y="178" textAnchor="middle">DOC</text>
        <circle className="moving-packet packet-a" r="4"><animateMotion dur="3.1s" repeatCount="indefinite"><mpath href={`#${iotPathId}`} /></animateMotion></circle>
        <circle className="moving-packet packet-b" r="4"><animateMotion dur="3.8s" repeatCount="indefinite"><mpath href={`#${weatherPathId}`} /></animateMotion></circle>
        <circle className="moving-packet packet-c" r="4"><animateMotion dur="4.3s" repeatCount="indefinite"><mpath href={`#${satellitePathId}`} /></animateMotion></circle>
        <circle className="moving-packet packet-d" r="4"><animateMotion dur="2.7s" repeatCount="indefinite"><mpath href={`#${outputPathId}`} /></animateMotion></circle>
      </svg>
      <div className="circuit-labels">
        <span><i />telemetría física</span><span><i />Open-Meteo / CAMS / GloFAS</span><span><i />FIRMS / Copernicus</span><span><i />scoring sanitario</span>
      </div>
    </div>
  );
}

function IndexCard({ index }: { index: NonNullable<SpaceAIThreatAssessment>["indices"][number] }) {
  const color = LEVEL_COLOR[index.level];
  return (
    <article className={`threat-card ${index.level.toLowerCase()}`} style={{ "--risk-color": color } as CSSProperties}>
      <div className="threat-card-head"><span>{index.label}</span><b>{index.level}</b></div>
      <div className="threat-card-value"><strong>{index.value == null ? "—" : Number.isInteger(index.value) ? index.value : index.value.toFixed(1)}</strong><small>{index.unit}</small></div>
      <div className="threat-score"><i style={{ width: `${Math.min(100, index.score)}%` }} /></div>
      <p>{index.status}</p>
      <small>{index.source}</small>
    </article>
  );
}

export default function ObservatoryPanel({ token, devices, detections, commandIntel, commandAssessment, sourceSettings }: Props) {
  const chartUid = useId().replaceAll(":", "");
  const lineFillId = `lineFill-${chartUid}`;
  const [selectedId, setSelectedId] = useState("");
  const [deviceIntel, setDeviceIntel] = useState<EarthIntel | null>(null);
  const [deviceReadings, setDeviceReadings] = useState<Record<string, Reading[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [snapshotNotice, setSnapshotNotice] = useState("");
  const [persisting, setPersisting] = useState(false);
  const [shareNotice, setShareNotice] = useState("");
  const [sharing, setSharing] = useState(false);

  useEffect(() => {
    if (!selectedId && devices.length) setSelectedId(devices.find((device) => device.status === "online")?.id || devices[0].id);
  }, [devices, selectedId]);

  const selected = devices.find((device) => device.id === selectedId) || null;
  const earthOptions = useMemo<EarthIntelOptions>(() => ({
    weatherEnabled: sourceSettings.open_meteo_enabled,
    airQualityEnabled: sourceSettings.air_quality_enabled,
    floodEnabled: sourceSettings.flood_enabled,
    cacheTtlMinutes: sourceSettings.refresh_minutes,
  }), [sourceSettings.open_meteo_enabled, sourceSettings.air_quality_enabled, sourceSettings.flood_enabled, sourceSettings.refresh_minutes]);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    Promise.all([
      fetchEarthIntel(selected.lat, selected.lon, controller.signal, false, earthOptions),
      Promise.all(["temp", "humidity", "pm25", "nivel"].map(async (variable) => {
        try {
          const values = await apiGet<Reading[]>(`/devices/${selected.id}/readings?variable=${variable}&hours=48`, token);
          return [variable, values] as const;
        } catch {
          return [variable, []] as const;
        }
      })),
    ]).then(([intel, readings]) => {
      setDeviceIntel(intel);
      setDeviceReadings(Object.fromEntries(readings));
    }).catch((cause) => {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setError(cause instanceof Error ? cause.message : "No se pudo sincronizar el nodo");
      setDeviceIntel(null);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [selected, token, earthOptions]);

  const activeIntel = deviceIntel || commandIntel;
  const assessment = useMemo(() => buildSpaceAIThreatAssessment(activeIntel, detections, { fireRadiusKm: sourceSettings.fire_radius_km, firmsEnabled: sourceSettings.firms_enabled }), [activeIntel, detections, sourceSettings.fire_radius_km, sourceSettings.firms_enabled]);
  const line = linePath(assessment?.indexSeries ?? []);
  const localTemp = latest(deviceReadings.temp || []);
  const localHumidity = latest(deviceReadings.humidity || []);
  const localPm25 = latest(deviceReadings.pm25 || []);
  const localLevel = latest(deviceReadings.nivel || []);
  const selectedAssessment = assessment || commandAssessment;

  function alertMessage(): string {
    if (!selectedAssessment) return "EcoNexo todavía no dispone de una lectura ambiental para comunicar.";
    const top = [...selectedAssessment.indices].sort((a, b) => b.score - a.score).slice(0, 3);
    return [
      `⚠️ *EcoNexo · Alerta IA ${selectedAssessment.overallLevel}*`,
      `*${selectedAssessment.overallLabel}* · índice ${Math.round(selectedAssessment.overallScore)}/100`,
      "",
      ...top.map((index) => `• ${index.label}: ${index.level} · ${index.status}`),
      "",
      `📍 Coordenadas: ${selectedAssessment.snapshot.latitude.toFixed(4)}, ${selectedAssessment.snapshot.longitude.toFixed(4)}`,
      `🛰️ Focos térmicos en 48 h: ${selectedAssessment.hotspots.count48h}`,
      `🧪 Método: ${selectedAssessment.snapshot.methodology_version}`,
      "",
      selectedAssessment.alerts[0]?.action || "Mantener vigilancia y contrastar con fuentes locales.",
      "",
      "Mensaje preventivo generado por EcoNexo. Requiere revisión humana; no reemplaza una comunicación oficial, diagnóstico o peritaje.",
    ].join("\n");
  }

  async function shareAlert(channel: AlertShareInput["channel"], audience: AlertShareInput["audience"]) {
    if (!selectedAssessment) return;
    setSharing(true); setShareNotice("");
    const message = alertMessage();
    try {
      await apiPost<AlertShareResult>("/modules/alert-share", token, {
        channel, audience, title: `${selectedAssessment.overallLevel} · ${selectedAssessment.overallLabel}`,
        message, module_key: "core", metadata: { score: selectedAssessment.overallScore, level: selectedAssessment.overallLevel },
      } satisfies AlertShareInput);
      const encoded = encodeURIComponent(message);
      if (channel === "whatsapp") window.open(`https://wa.me/?text=${encoded}`, "_blank", "noopener,noreferrer");
      else if (channel === "telegram") window.open(`https://t.me/share/url?url=&text=${encoded}`, "_blank", "noopener,noreferrer");
      else if (channel === "email") window.location.href = `mailto:?subject=${encodeURIComponent(`Alerta EcoNexo ${selectedAssessment.overallLevel}`)}&body=${encoded}`;
      else await navigator.clipboard.writeText(message);
      setShareNotice(channel === "copiar" ? "Mensaje copiado y registrado." : "Comunicación registrada; revisala antes de enviarla.");
    } catch (cause) {
      setShareNotice(cause instanceof Error ? cause.message : "No se pudo preparar la comunicación.");
    } finally { setSharing(false); }
  }

  async function persistSnapshot(activateAlerts: boolean) {
    if (!selectedAssessment) return;
    setPersisting(true);
    setSnapshotNotice("");
    try {
      const record = await apiPost<EnvironmentalSnapshotRecord>(`/environment/snapshots?activate_alerts=${activateAlerts ? "true" : "false"}&origin=observatorio_web`, token, selectedAssessment.snapshot);
      setSnapshotNotice(`Snapshot ${record.snapshot.overall_level} registrado${record.activated_alerts ? ` · ${record.activated_alerts} alertas activadas` : ""}.`);
    } catch (cause) {
      setSnapshotNotice(cause instanceof Error ? cause.message : "No se pudo registrar el snapshot");
    } finally {
      setPersisting(false);
    }
  }

  return (
    <div className="view observatory-view">
      <div className="observatory-header">
        <div>
          <span className="eyebrow">ALERTA IA · SPACEAI</span>
          <h2>Lectura ambiental y comunicación preventiva</h2>
          <p>El nodo físico aporta telemetría local. Open-Meteo, CAMS y GloFAS agregan contexto modelado para la coordenada del dispositivo; NASA FIRMS aporta detecciones térmicas satelitales cercanas al tiempo real.</p>
        </div>
        <div className="observatory-controls">
          <label>Nodo observado
            <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
              {devices.map((device) => <option key={device.id} value={device.id}>{device.name} · {device.external_id}</option>)}
            </select>
          </label>
          <span className={`observatory-sync ${loading ? "loading" : error ? "error" : "live"}`}><i />{loading ? "sincronizando" : error ? "enlace parcial" : "flujo activo"}</span>
          <div className="observatory-actions">
            <button type="button" disabled={persisting || !selectedAssessment} onClick={() => void persistSnapshot(false)}>Registrar snapshot</button>
            <button type="button" className="primary" disabled={persisting || !selectedAssessment} onClick={() => void persistSnapshot(true)}>Registrar + alertar</button>
          </div>
        </div>
      </div>
      {snapshotNotice && <div className="workspace-message success">{snapshotNotice}</div>}
      <section className="ai-share-panel">
        <div><span className="eyebrow">SALIDA PARA COMUNICACIÓN</span><h3>Alerta IA revisable</h3><p>Prepará un mensaje entendible para WhatsApp, Telegram, medios, organizaciones o laboratorios. El envío siempre queda bajo revisión humana y se registra en auditoría.</p></div>
        <pre>{alertMessage()}</pre>
        <div className="ai-share-controls">
          <button className="primary" disabled={sharing || !selectedAssessment} onClick={() => void shareAlert("whatsapp", "organizacion")}>WhatsApp</button>
          <button disabled={sharing || !selectedAssessment} onClick={() => void shareAlert("telegram", "medios")}>Telegram</button>
          <button disabled={sharing || !selectedAssessment} onClick={() => void shareAlert("email", "laboratorio")}>Email a laboratorio</button>
          <button disabled={sharing || !selectedAssessment} onClick={() => void shareAlert("copiar", "otro")}>Copiar</button>
        </div>
        {shareNotice && <small className="ai-share-notice">{shareNotice}</small>}
      </section>

      <section className="observatory-hero">
        <div className="hti-panel">
          <Gauge assessment={selectedAssessment} />
          <div className="hti-copy">
            <span>MODELO COMPUESTO</span>
            <h3>{selectedAssessment?.overallLabel || "Esperando datos"}</h3>
            <p>Excedencia, persistencia, confiabilidad y co-exposición se integran en una lectura operacional. Las categorías R0-R5 siguen la matriz SpaceAI del documento técnico.</p>
            <div className="hti-meta"><span>fuentes <b>{sourceHealth(activeIntel)}%</b></span><span>focos {sourceSettings.fire_radius_km} km <b>{selectedAssessment?.hotspots.count48h ?? 0}</b></span><span>método <b>0.2</b></span></div>
          </div>
        </div>
        <NeuralCircuit assessment={selectedAssessment} />
      </section>

      <section className="ai-line-panel">
        <div className="ai-line-copy"><span>AI THREAT LINE · 12 H</span><strong>Proyección de presión ambiental</strong><small>Combina PM2.5, estrés térmico y peligro meteorológico de incendio.</small></div>
        <div className="ai-line-chart">
          {line ? <svg viewBox="0 0 520 140" preserveAspectRatio="none" aria-label="Tendencia proyectada del índice ambiental">
            <defs><linearGradient id={lineFillId} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#8ff06a" stopOpacity=".28" /><stop offset="1" stopColor="#33daff" stopOpacity="0" /></linearGradient></defs>
            <path className="ai-line-grid" d="M0 35 H520 M0 70 H520 M0 105 H520" />
            <path className="ai-line-area" fill={`url(#${lineFillId})`} d={`${line} L520,140 L0,140 Z`} />
            <path className="ai-line" d={line} />
          </svg> : <div className="empty">Sin serie disponible.</div>}
          <div className="ai-line-threshold"><span>R4</span></div>
        </div>
        <div className="ai-line-score"><small>AHORA</small><strong>{selectedAssessment ? Math.round(selectedAssessment.overallScore) : "—"}</strong><span>{selectedAssessment?.overallLevel || "R0"}</span></div>
      </section>

      <section className="threat-grid" aria-label="Índices ambientales SpaceAI">
        {(selectedAssessment?.indices || []).map((index) => <IndexCard key={index.id} index={index} />)}
      </section>

      <section className="observatory-data-grid">
        <article className="device-twin-panel">
          <div className="panel-heading"><span>01</span><div><h3>Gemelo digital del nodo</h3><p>Comparación entre sensor físico y contexto geoespacial.</p></div></div>
          <div className="device-identity">
            <div className={`device-pulse ${selected?.status || "offline"}`}><i /><i /><b /></div>
            <div><strong>{selected?.name || "Centro de comando"}</strong><span>{selected?.external_id || "COORDENADA BASE"}</span><small>{selected ? `${selected.lat.toFixed(5)}, ${selected.lon.toFixed(5)}` : "—"}</small></div>
            <span className={`stat ${selected?.status === "online" ? "online" : selected?.status === "alerta" ? "alerta" : "offline"}`}>● {selected?.status || "contexto"}</span>
          </div>
          <div className="twin-table">
            <div className="twin-row head"><span>Variable</span><span>Nodo IoT</span><span>Open-Meteo / CAMS</span><span>Diferencia</span></div>
            <TwinRow label="Temperatura" local={localTemp?.value ?? null} external={activeIntel?.weather.temperature ?? null} unit="°C" />
            <TwinRow label="Humedad" local={localHumidity?.value ?? null} external={activeIntel?.weather.humidity ?? null} unit="%" />
            <TwinRow label="PM2.5" local={localPm25?.value ?? null} external={activeIntel?.atmosphere.pm25 ?? null} unit="µg/m³" />
            <TwinRow label="Nivel hídrico" local={localLevel?.value ?? null} external={activeIntel?.flood.currentDischarge ?? null} unit="m / m³s" comparable={false} />
          </div>
          <p className="data-disclaimer">La columna externa no reemplaza al dispositivo: representa una celda de modelo de varios kilómetros. Las diferencias se usan para control de coherencia, no para calibración automática.</p>
        </article>

        <article className="spaceai-alert-panel">
          <div className="panel-heading"><span>02</span><div><h3>Alertas sanitarias ambientales</h3><p>Generadas por la matriz R0-R5.</p></div></div>
          <div className="spaceai-alert-list">
            {(selectedAssessment?.alerts || []).map((alert) => <div className={`spaceai-alert-row ${alert.level.toLowerCase()}`} key={alert.id}>
              <b>{alert.level}</b><div><strong>{alert.title}</strong><p>{alert.summary}</p><small>{alert.action}</small></div><span>{Math.round(alert.confidence * 100)}%</span>
            </div>)}
            {!selectedAssessment?.alerts.length && <div className="empty">Sin dominios en R2 o superior.</div>}
          </div>
        </article>
      </section>

      <section className="methodology-ribbon">
        <div><span>SPACEAI · REGLA CONTINUA</span><strong>R0 &lt;80% · R1 80-99% · R2 100-149% · R3 150-199% · R4 ≥200%</strong></div>
        <div><span>ESCALAS ESPECÍFICAS</span><strong>AQI · UV · calor · GloFAS · focos FIRMS</strong></div>
        <div><span>CONDICIÓN DE USO</span><strong>Apoyo operativo; validar con normativa y autoridad competente</strong></div>
      </section>
    </div>
  );
}

function TwinRow({ label, local, external, unit, comparable = true }: { label: string; local: number | null; external: number | null; unit: string; comparable?: boolean }) {
  const difference = comparable && local != null && external != null ? local - external : null;
  return <div className="twin-row"><span>{label}</span><strong>{fmt(local, ` ${unit}`)}</strong><strong>{fmt(external, ` ${unit}`)}</strong><span className={difference != null && Math.abs(difference) > 8 ? "delta high" : "delta"}>{difference == null ? "contexto" : `${difference >= 0 ? "+" : ""}${difference.toFixed(1)}`}</span></div>;
}
