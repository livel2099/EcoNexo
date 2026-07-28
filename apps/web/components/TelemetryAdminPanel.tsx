"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../app/lib/api";
import type {
  Device,
  DeviceMarkerShape,
  PipelineRun,
  RiskZone,
  TelemetryMode,
  TelemetryPipelineSettings,
} from "../app/lib/types";
import { MISIONES_CENTER, assertMisionesCoordinates } from "../app/lib/misiones";

type Draft = {
  name: string;
  external_id: string;
  lat: string;
  lon: string;
  zone_id: string;
  marker_shape: DeviceMarkerShape;
  telemetry_mode: TelemetryMode;
  pipeline_enabled: boolean;
};

const EMPTY_DRAFT: Draft = {
  name: "",
  external_id: "",
  lat: String(MISIONES_CENTER[0]),
  lon: String(MISIONES_CENTER[1]),
  zone_id: "",
  marker_shape: "square",
  telemetry_mode: "open_meteo",
  pipeline_enabled: true,
};

const SHAPE_LABEL: Record<DeviceMarkerShape, string> = {
  circle: "Círculo",
  square: "Cuadro",
  triangle: "Triángulo",
};

const MODE_LABEL: Record<TelemetryMode, string> = {
  mqtt: "MQTT / dispositivo real",
  open_meteo: "Open-Meteo / nodo virtual",
  manual: "Carga manual",
};

function runLabel(run: PipelineRun | null): string {
  if (!run) return "Sin ejecuciones registradas";
  const time = run.finished_at || run.started_at;
  const when = time ? new Date(time).toLocaleString("es-AR") : "en curso";
  return `${run.status} · ${when} · ${run.devices_updated}/${run.devices_total} nodos actualizados`;
}

function readingSummary(device: Device): string {
  const value = device.latest_readings || {};
  const parts: string[] = [];
  if (typeof value.temp === "number") parts.push(`${value.temp.toFixed(1)} °C`);
  if (typeof value.humidity === "number") parts.push(`${value.humidity.toFixed(0)}% HR`);
  if (typeof value.soil_moisture === "number") parts.push(`${value.soil_moisture.toFixed(0)}% suelo`);
  if (typeof value.wind_gust === "number") parts.push(`${value.wind_gust.toFixed(0)} km/h ráfaga`);
  return parts.length ? parts.join(" · ") : "sin lecturas todavía";
}

export default function TelemetryAdminPanel({
  token,
  zones,
  onChanged,
}: {
  token: string;
  zones: RiskZone[];
  onChanged?: () => void;
}) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [settings, setSettings] = useState<TelemetryPipelineSettings | null>(null);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    const [nextDevices, nextSettings, nextRuns] = await Promise.all([
      apiGet<Device[]>("/devices", token),
      apiGet<TelemetryPipelineSettings>("/pipeline/settings", token),
      apiGet<PipelineRun[]>("/pipeline/runs?limit=12", token),
    ]);
    setDevices(nextDevices);
    setSettings(nextSettings);
    setRuns(nextRuns);
    setDraft((current) => {
      if (current.zone_id || !zones.length) return current;
      const zone = zones[0];
      return {
        ...current,
        zone_id: zone.id,
        lat: String(zone.lat),
        lon: String(zone.lon),
      };
    });
  }, [token, zones]);

  useEffect(() => {
    void load().catch((cause) => {
      setError(cause instanceof Error ? cause.message : "No se pudo cargar la telemetría");
    });
  }, [load]);

  const lastRun = runs[0] || null;
  const online = useMemo(() => devices.filter((item) => item.status === "online").length, [devices]);
  const virtual = useMemo(() => devices.filter((item) => item.telemetry_mode === "open_meteo").length, [devices]);

  function flash(message: string) {
    setNotice(message);
    setError("");
    globalThis.setTimeout(() => setNotice(""), 5000);
  }

  function selectZone(zoneId: string) {
    const zone = zones.find((item) => item.id === zoneId);
    setDraft((current) => ({
      ...current,
      zone_id: zoneId,
      lat: zone ? String(zone.lat) : current.lat,
      lon: zone ? String(zone.lon) : current.lon,
    }));
  }

  async function createNode(event: React.FormEvent) {
    event.preventDefault();
    const lat = Number(draft.lat);
    const lon = Number(draft.lon);
    try {
      assertMisionesCoordinates(lat, lon);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "El nodo debe ubicarse dentro de Misiones");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await apiPost("/devices", token, {
        name: draft.name.trim(),
        external_id: draft.external_id.trim(),
        lat,
        lon,
        tags: [draft.telemetry_mode === "open_meteo" ? "virtual" : "campo", "telemetria"],
        marker_shape: draft.marker_shape,
        telemetry_mode: draft.telemetry_mode,
        zone_id: draft.zone_id || null,
        pipeline_enabled: draft.pipeline_enabled,
        telemetry_config: {
          provider: draft.telemetry_mode === "open_meteo" ? "open-meteo" : draft.telemetry_mode,
          context: draft.telemetry_mode === "open_meteo" ? "modelled-not-physical-sensor" : "physical-or-manual",
        },
      });
      setDraft((current) => ({
        ...EMPTY_DRAFT,
        zone_id: current.zone_id,
        lat: current.lat,
        lon: current.lon,
      }));
      await load();
      onChanged?.();
      flash("Nodo creado. Ya puede aparecer en el mapa y participar del pipeline.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo crear el nodo");
    } finally {
      setBusy(false);
    }
  }

  async function updateNode(device: Device, changes: Record<string, unknown>) {
    setBusy(true);
    setError("");
    try {
      await apiPatch(`/devices/${device.id}`, token, changes);
      await load();
      onChanged?.();
      flash("Configuración del nodo actualizada.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo actualizar el nodo");
    } finally {
      setBusy(false);
    }
  }

  async function addManualReading(device: Device) {
    const raw = window.prompt(
      `Lecturas para ${device.name} en formato variable=valor, separadas por coma.`,
      "temp=25,humidity=60,soil_moisture=35",
    );
    if (!raw) return;
    const values: Record<string, number> = {};
    for (const fragment of raw.split(",")) {
      const [keyRaw, valueRaw] = fragment.split("=");
      const key = keyRaw?.trim();
      const value = Number(valueRaw?.trim());
      if (!key || !Number.isFinite(value)) {
        setError(`Lectura inválida: ${fragment.trim()}`);
        return;
      }
      values[key] = value;
    }
    setBusy(true);
    setError("");
    try {
      await apiPost(`/devices/${device.id}/readings`, token, { values });
      await load();
      onChanged?.();
      flash("Lecturas registradas y nodo actualizado en el Command Core.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo registrar la lectura");
    } finally {
      setBusy(false);
    }
  }


  async function deleteNode(device: Device) {
    if (!window.confirm(`Eliminar el nodo “${device.name}”? Las lecturas asociadas también se eliminarán.`)) return;
    setBusy(true);
    setError("");
    try {
      await apiDelete(`/devices/${device.id}`, token);
      await load();
      onChanged?.();
      flash("Nodo eliminado y mapa actualizado.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo eliminar el nodo");
    } finally {
      setBusy(false);
    }
  }

  async function bootstrap() {
    setBusy(true);
    setError("");
    try {
      await apiPost("/pipeline/bootstrap", token, {
        count: 2,
        zone_id: draft.zone_id || null,
      });
      const run = await apiPost<PipelineRun>("/pipeline/run", token, {});
      await load();
      onChanged?.();
      flash(`Red inicial creada y pipeline ${run.status}: ${run.readings_inserted} lecturas.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo preparar la red inicial");
    } finally {
      setBusy(false);
    }
  }

  async function runPipeline() {
    setBusy(true);
    setError("");
    try {
      const run = await apiPost<PipelineRun>("/pipeline/run", token, {});
      await load();
      onChanged?.();
      flash(`Pipeline ${run.status}: ${run.devices_updated} nodos, ${run.readings_inserted} lecturas y ${run.alerts_created} alertas.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo ejecutar el pipeline");
    } finally {
      setBusy(false);
    }
  }

  async function saveSettings(event: React.FormEvent) {
    event.preventDefault();
    if (!settings) return;
    setBusy(true);
    setError("");
    try {
      const { org_id: _org, firms_configured: _firms, updated_at: _updated, ...payload } = settings;
      const next = await apiPatch<TelemetryPipelineSettings>("/pipeline/settings", token, payload);
      setSettings(next);
      flash("Política de telemetría guardada.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo guardar el pipeline");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="telemetry-admin">
      {error && <div className="workspace-message error" role="alert">{error}</div>}
      {notice && <div className="workspace-message success">{notice}</div>}

      <div className="telemetry-admin-hero">
        <div>
          <span className="eyebrow">TELEMETRÍA · COMMAND PIPELINE</span>
          <h3>Red física y nodos virtuales</h3>
          <p>Ubicá cada nodo dentro de una geocerca, elegí cuadro, triángulo o círculo y definí si recibe datos por MQTT, Open-Meteo o carga manual.</p>
        </div>
        <div className="telemetry-admin-stats">
          <span><b>{devices.length}</b> nodos</span>
          <span><b>{online}</b> online</span>
          <span><b>{virtual}</b> virtuales</span>
          <span><b>{zones.length}</b> zonas</span>
        </div>
        <div className="telemetry-pipeline-actions">
          {!devices.length && <button type="button" className="primary" disabled={busy} onClick={() => void bootstrap()}>Crear red inicial y ejecutar</button>}
          <button type="button" className="primary" disabled={busy || !settings?.enabled} onClick={() => void runPipeline()}>{busy ? "Procesando…" : "Ejecutar pipeline ahora"}</button>
          <small>{runLabel(lastRun)}</small>
        </div>
      </div>

      <div className="telemetry-admin-layout">
        <form className="admin-form-card telemetry-node-form" onSubmit={createNode}>
          <div className="panel-heading"><span>01</span><div><h3>Alta de nodo</h3><p>El marcador y la geocerca quedan persistidos en PostGIS.</p></div></div>
          <label>Nombre<input required minLength={2} maxLength={120} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="Nodo Arroyo Verde" /></label>
          <label>Identificador externo<input required minLength={2} maxLength={120} value={draft.external_id} onChange={(event) => setDraft({ ...draft, external_id: event.target.value })} placeholder="nodo-arroyo-verde-01" /></label>
          <label>Zona<select value={draft.zone_id} onChange={(event) => selectZone(event.target.value)}><option value="">Sin zona</option>{zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name} · {zone.kind}</option>)}</select></label>
          <div className="form-two">
            <label>Forma<select value={draft.marker_shape} onChange={(event) => setDraft({ ...draft, marker_shape: event.target.value as DeviceMarkerShape })}>{Object.entries(SHAPE_LABEL).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
            <label>Fuente<select value={draft.telemetry_mode} onChange={(event) => setDraft({ ...draft, telemetry_mode: event.target.value as TelemetryMode })}>{Object.entries(MODE_LABEL).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          </div>
          <div className="form-two">
            <label>Latitud<input required type="number" step="0.000001" value={draft.lat} onChange={(event) => setDraft({ ...draft, lat: event.target.value })} /></label>
            <label>Longitud<input required type="number" step="0.000001" value={draft.lon} onChange={(event) => setDraft({ ...draft, lon: event.target.value })} /></label>
          </div>
          <label className="telemetry-checkbox"><input type="checkbox" checked={draft.pipeline_enabled} onChange={(event) => setDraft({ ...draft, pipeline_enabled: event.target.checked })} />Participa del pipeline operativo</label>
          <button className="primary" disabled={busy}>Crear nodo</button>
          <div className="source-warning"><strong>Open-Meteo</strong><span>Un nodo virtual representa contexto modelado en esa coordenada; no debe presentarse como sensor físico instalado.</span></div>
        </form>

        <article className="admin-table-card telemetry-node-table-card">
          <div className="panel-heading"><span>02</span><div><h3>Nodos configurados</h3><p>Cambios de forma, fuente y zona sin recompilar la plataforma.</p></div></div>
          <div className="telemetry-node-list">
            {devices.map((device) => (
              <div className={`telemetry-node-row ${device.status}`} key={device.id}>
                <span className={`telemetry-shape ${device.marker_shape}`} aria-hidden="true" />
                <div className="telemetry-node-copy"><strong>{device.name}</strong><span>{device.external_id} · {device.zone_name || "sin zona"}</span><small>{readingSummary(device)}</small><small>{device.last_pipeline_status || "pipeline pendiente"}</small></div>
                <label>Forma<select disabled={busy} value={device.marker_shape} onChange={(event) => void updateNode(device, { marker_shape: event.target.value })}>{Object.entries(SHAPE_LABEL).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
                <label>Fuente<select disabled={busy} value={device.telemetry_mode} onChange={(event) => void updateNode(device, { telemetry_mode: event.target.value })}>{Object.entries(MODE_LABEL).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
                <label>Zona<select disabled={busy} value={device.zone_id || ""} onChange={(event) => void updateNode(device, { zone_id: event.target.value || null })}><option value="">Sin zona</option>{zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}</select></label>
                <div className="telemetry-node-actions"><button type="button" disabled={busy} onClick={() => void addManualReading(device)}>Cargar lectura</button><button type="button" disabled={busy} onClick={() => void updateNode(device, { pipeline_enabled: !device.pipeline_enabled })}>{device.pipeline_enabled ? "Pausar pipeline" : "Activar pipeline"}</button><button type="button" className="danger" disabled={busy} onClick={() => void deleteNode(device)}>Eliminar</button></div>
              </div>
            ))}
            {!devices.length && <div className="empty telemetry-empty"><strong>No hay nodos todavía.</strong><span>Creá uno manualmente o usá “Crear red inicial y ejecutar”.</span></div>}
          </div>
        </article>
      </div>

      {settings && <form className="admin-form-card telemetry-settings" onSubmit={saveSettings}>
        <div className="panel-heading"><span>03</span><div><h3>Política del pipeline</h3><p>Controla actualización, caducidad y evaluación automática de reglas.</p></div></div>
        <div className="source-switch-grid">
          <label className={`source-toggle ${settings.enabled ? "enabled" : ""}`}><div><strong>Pipeline habilitado</strong><small>Permite ejecuciones manuales y programadas</small></div><button type="button" className={`switch ${settings.enabled ? "on" : ""}`} onClick={() => setSettings({ ...settings, enabled: !settings.enabled })}><i /></button></label>
          <label className={`source-toggle ${settings.auto_run ? "enabled" : ""}`}><div><strong>Ejecución automática</strong><small>Scheduler liviano dentro de la API</small></div><button type="button" className={`switch ${settings.auto_run ? "on" : ""}`} onClick={() => setSettings({ ...settings, auto_run: !settings.auto_run })}><i /></button></label>
          <label className={`source-toggle ${settings.refresh_firms ? "enabled" : ""}`}><div><strong>Actualizar NASA FIRMS</strong><small>{settings.firms_configured ? "MAP_KEY configurada" : "sin MAP_KEY: no se simulan focos"}</small></div><button type="button" className={`switch ${settings.refresh_firms ? "on" : ""}`} onClick={() => setSettings({ ...settings, refresh_firms: !settings.refresh_firms })}><i /></button></label>
          <label className={`source-toggle ${settings.evaluate_rules ? "enabled" : ""}`}><div><strong>Evaluar reglas</strong><small>Correlación de lecturas, zonas y satélite</small></div><button type="button" className={`switch ${settings.evaluate_rules ? "on" : ""}`} onClick={() => setSettings({ ...settings, evaluate_rules: !settings.evaluate_rules })}><i /></button></label>
        </div>
        <div className="form-two"><label>Intervalo automático (min)<input type="number" min={2} max={1440} value={settings.interval_minutes} onChange={(event) => setSettings({ ...settings, interval_minutes: Number(event.target.value) })} /></label><label>Marcar nodo vencido después de (min)<input type="number" min={5} max={10080} value={settings.stale_minutes} onChange={(event) => setSettings({ ...settings, stale_minutes: Number(event.target.value) })} /></label></div>
        <button className="primary" disabled={busy}>Guardar política de telemetría</button>
      </form>}

      <article className="admin-table-card telemetry-runs-card">
        <div className="panel-heading"><span>04</span><div><h3>Historial de ejecuciones</h3><p>Lecturas, focos y alertas creadas en cada corrida.</p></div></div>
        <div className="telemetry-run-list">
          {runs.map((run) => <div key={run.id}><span className={`pipeline-status ${run.status}`}>{run.status}</span><time>{run.started_at ? new Date(run.started_at).toLocaleString("es-AR") : "—"}</time><strong>{run.devices_updated}/{run.devices_total} nodos</strong><span>{run.readings_inserted} lecturas</span><span>{run.detections_ingested} focos</span><span>{run.alerts_created} alertas</span></div>)}
          {!runs.length && <div className="empty">Sin ejecuciones todavía.</div>}
        </div>
      </article>
    </section>
  );
}
