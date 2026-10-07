"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, IS_DEMO } from "../app/lib/api";

type Hazard = "fire" | "hydric" | "health_heat" | "health_air";
const risks: Record<Hazard, { title: string; event: string; scope: string }> = {
  fire: { title: "incendios", event: "Incendio", scope: "Condiciones meteorológicas favorables al incendio; verificar combustible y fuentes de ignición." },
  hydric: { title: "riesgo hídrico por lluvias", event: "Anegamiento por lluvias", scope: "Susceptibilidad pluvial experimental. No pronostica crecidas fluviales: faltan niveles, cuencas, relieve y drenaje local." },
  health_heat: { title: "riesgo sanitario por calor", event: "Incidente sanitario asociado al calor", scope: "Exposición ambiental por sensación térmica. Verificar incidentes agregados con responsables sanitarios; no estima diagnósticos ni brotes." },
  health_air: { title: "riesgo sanitario por PM2.5", event: "Incidente sanitario asociado a PM2.5", scope: "Exposición ambiental prevista por CAMS vía Open-Meteo. La grilla global de aproximadamente 45 km requiere contraste local y evidencia sanitaria agregada; no estima diagnósticos ni brotes." },
};
type Horizon = 6 | 24 | 72;
type Forecast = {
  id: string; device_id: string; device_name: string; horizon_hours: Horizon;
  issued_at: string; valid_from: string; valid_to: string; model_version: string;
  risk_index: number; probability: number | null; warning: boolean;
  explanation: string[]; action: string;
  provenance?: { hourly?: Record<string, number | string>[] };
};
type Metric = {
  model_version: string; evaluated: number; pending_labels: number; tp: number; fp: number; fn: number;
  scope_start: string;
  precision: number | null; recall: number | null; brier: number | null; independent_events: number;
  events_missed: number; median_lead_hours: number | null; event_recall: number | null;
  calibration: { count: number; mean_probability: number; observed_rate: number }[];
};
type Model = {
  id: string; version: string; eligible: boolean; created_at: string;
  evaluation: { train: number; calibration: number; test: number; purged: number; brier: number;
    prevalence_brier: number; heuristic_index_brier: number; recall: number; scope: string };
  drift: { status: string; samples: number };
};
type Evaluation = { metrics: Metric[]; models: Model[]; labels_policy: string; generated_at: string };
type Settings = { hazard?: Hazard; horizon_hours: Horizon; enabled: boolean; active_model_id: string | null };
type Observation = { id: string; outcome: "event" | "no_event"; start_at: string; end_at: string; source: string; reference: string };
type Node = { id: string; name: string };
const date = (value: string) => new Date(value).toLocaleString("es-AR");
const pct = (value: number | null) => value == null ? "Sin evidencia" : `${(value * 100).toFixed(1)}%`;

export default function PredictivePanel({ token, role }: { token: string; role: string }) {
  const [hazard, setHazard] = useState<Hazard>("fire");
  const risk = risks[hazard];
  const [horizon, setHorizon] = useState<Horizon>(24);
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [settings, setSettings] = useState<Settings[]>([]);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [consent, setConsent] = useState(false);
  const [coverage, setCoverage] = useState(false);
  const [draft, setDraft] = useState({ device_id: "", outcome: "event", start_at: "", end_at: "", source: "field_report", reference: "", notes: "" });
  const enabled = settings.find((item) => item.horizon_hours === horizon && (item.hazard ?? "fire") === hazard)?.enabled ?? false;
  const activeId = settings.find((item) => item.horizon_hours === horizon && (item.hazard ?? "fire") === hazard)?.active_model_id;
  const canOperate = role === "admin" || role === "operador";

  const load = useCallback(async () => {
    const results = await Promise.allSettled([
      apiGet<Forecast[]>(`/predictions?hazard=${hazard}&horizon_hours=${horizon}`, token),
      apiGet<Evaluation>(`/predictions/evaluation?hazard=${hazard}&horizon_hours=${horizon}&days=90`, token),
      apiGet<Settings[]>("/predictions/settings", token),
      apiGet<Observation[]>(`/predictions/observations?hazard=${hazard}`, token),
      apiGet<Node[]>("/devices", token),
    ]);
    const [predictions, metrics, config, evidence, devices] = results;
    if (predictions.status === "fulfilled") setForecasts(predictions.value as Forecast[]);
    if (metrics.status === "fulfilled") setEvaluation(metrics.value as Evaluation);
    if (evidence.status === "fulfilled") setObservations(evidence.value as Observation[]);
    if (config.status === "fulfilled") {
      const nextSettings = config.value as Settings[];
      setSettings(nextSettings);
      setConsent(nextSettings.find((item) => item.horizon_hours === horizon && (item.hazard ?? "fire") === hazard)?.enabled ?? false);
    }
    if (devices.status === "fulfilled") {
      const nextNodes = devices.value as Node[];
      setNodes(nextNodes);
      setDraft((current) => current.device_id || !nextNodes.length ? current : { ...current, device_id: nextNodes[0].id });
    }
    const labels = ["Pronósticos", "Evaluación", "Configuración predictiva", "Evidencia", "Nodos"];
    const failures = results.flatMap((result, index) => result.status === "rejected" ? [`${labels[index]}: ${result.reason instanceof Error ? result.reason.message : "consulta no disponible"}`] : []);
    if (failures.length) throw new Error(failures.join(" · "));
  }, [token, horizon, hazard]);

  const refresh = useCallback(async () => {
    setBusy(true); setError("");
    try { await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo consultar el ciclo predictivo."); }
    finally { setBusy(false); }
  }, [load]);
  useEffect(() => {
    setForecasts([]); setEvaluation(null); setConsent(false); setCoverage(false); setNotice(""); setObservations([]);
    setDraft((current) => ({ ...current, reference: "", notes: "", start_at: "", end_at: "" }));
    if (!IS_DEMO) void refresh();
  }, [refresh]);

  async function mutate(path: string, body: unknown, message: string) {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await apiPost<{ message?: string; errors?: unknown[] }>(path, token, body);
      setNotice(result.errors?.length ? `${message} Hay territorios sin cobertura horaria completa.` : result.message || message);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo completar la operación."); }
    finally { setBusy(false); }
  }

  async function generate() {
    setBusy(true); setError(""); setNotice("");
    try {
      if (!enabled) {
        if (role !== "admin" || !consent) throw new Error("Un administrador debe autorizar la fuente para este riesgo y horizonte.");
        await apiPost("/predictions/models/deploy", token, { hazard, horizon_hours: horizon, enabled: true, external_weather_consent: true });
      }
      const result = await apiPost<{ created: number; skipped: number; message: string; errors: { detail: string; device_id?: string; horizon_hours?: number }[] }>(`/predictions/run?hazard=${hazard}&horizon_hours=${horizon}`, token, {});
      await load();
      if (result.errors?.length) {
        setError(result.errors.map((item) => `${item.device_id ? `Nodo ${item.device_id}: ` : ""}${item.detail}`).join(" · "));
      }
      setNotice(result.created > 0 ? `${result.created} ${result.created === 1 ? "pronóstico generado" : "pronósticos generados"} para ${horizon} horas.` : result.message || "No se generaron nuevos pronósticos.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo generar el pronóstico."); }
    finally { setBusy(false); }
  }

  async function verify(event: React.FormEvent) {
    event.preventDefault();
    if (!coverage) return;
    const start = new Date(draft.start_at).toISOString();
    const end = draft.outcome === "event" ? start : new Date(draft.end_at).toISOString();
    await mutate("/predictions/observations", { ...draft, hazard, start_at: start, end_at: end, coverage_verified: true }, "Resultado independiente registrado.");
  }

  if (IS_DEMO) return <section className="view predictive-panel" tabIndex={0}><h1>Predicción de {risk.title}</h1><p>El ciclo predictivo necesita fuentes y resultados reales. Abrí una sesión conectada a la API para utilizarlo.</p></section>;

  return <section className="view predictive-panel" aria-label="Ciclo predictivo" tabIndex={0}>
    <header className="predictive-header"><div><span className="eyebrow">ECO/NEXO · ANTICIPACIÓN</span><h1>Predicción de {risk.title}</h1><p>Pronósticos archivados, evidencia independiente y aprendizaje por territorio.</p></div>
      <label>Riesgo<select aria-label="Riesgo predictivo" disabled={busy} value={hazard} onChange={(event) => setHazard(event.target.value as Hazard)}>{(Object.keys(risks) as Hazard[]).map((id) => <option key={id} value={id}>{risks[id].title}</option>)}</select></label>
      <label>Horizonte<select disabled={busy} value={horizon} onChange={(event) => setHorizon(Number(event.target.value) as Horizon)}><option value={6}>6 horas</option><option value={24}>24 horas</option><option value={72}>72 horas</option></select></label>
      <button disabled={busy} onClick={() => void refresh()}>Actualizar</button>
    </header>
    {error && <p role="alert" className="workspace-message error">{error}</p>}
    {notice && <p role="status" className="workspace-message success">{notice}</p>}
    <article className="predictive-card">
      <h2>{enabled ? "Pronósticos habilitados" : "Fuente predictiva deshabilitada"} · {horizon} h</h2>
      <p>{risk.scope}</p>
      {hazard === "health_air" && <p>Fuente: <a href="https://open-meteo.com/en/docs/air-quality-api" target="_blank" rel="noreferrer">Open-Meteo</a> y <a href="https://atmosphere.copernicus.eu/" target="_blank" rel="noreferrer">Copernicus CAMS</a>.</p>}
      <p>El índice ambiental inicial es heurístico. Un modelo propio entrenado emite probabilidades estimadas con evaluación temporal local. Los avisos permanecen en modo sombra para revisión humana.</p>
      {role === "admin" && <>
        <label className="predictive-check"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />Autorizo consultar Open-Meteo {hazard === "health_air" ? "Calidad del Aire (CAMS)" : "Pronóstico Meteorológico"} para este riesgo y horizonte enviando latitud y longitud de los nodos de mi organización.</label>
        <div className="predictive-actions"><button disabled={busy || !consent || enabled} onClick={() => void mutate("/predictions/models/deploy", { hazard, horizon_hours: horizon, enabled: true, external_weather_consent: true }, "Fuente habilitada para este horizonte.")}>Habilitar fuente</button>
          <button disabled={busy || !enabled} onClick={() => void mutate("/predictions/models/deploy", { hazard, horizon_hours: horizon, model_id: activeId ?? null, enabled: false }, "Pronósticos pausados.")}>Pausar pronósticos</button></div>
      </>}
      <p>Podés generar un pronóstico ambiental futuro sin entrenar un modelo. El entrenamiento agrega probabilidades cuando hay evidencia verificada suficiente.</p>
      {canOperate && <button className="primary" disabled={busy || (!enabled && (role !== "admin" || !consent))} onClick={() => void generate()}>{busy ? "Procesando…" : "Generar pronóstico"}</button>}
      {!enabled && role !== "admin" && <p>Pedí al administrador que habilite este riesgo y horizonte.</p>}
      <p>Una emisión por día UTC, nodo, horizonte y versión. La ejecución programada requiere habilitar el motor en el despliegue y esta fuente por organización.</p>
    </article>

    <h2>Qué puede ocurrir y qué hacer</h2>
    {!forecasts.length && <p>No hay pronósticos archivados para este riesgo y horizonte. {enabled ? "Pulsá Generar pronóstico para consultar la fuente." : "Autorizá la fuente y pulsá Generar pronóstico."} Sin datos no se puede concluir riesgo bajo.</p>}
    <div className="predictive-grid">{forecasts.slice(0, 30).map((item) => <article className="predictive-card" key={item.id}>
      <span className="eyebrow">{item.device_name} · {new Date(item.valid_to) <= new Date() ? "Ventana finalizada" : "Ventana futura"}</span>
      <h3>{item.warning ? "Preparar vigilancia" : "Mantener monitoreo"}</h3>
      <strong>{item.probability == null ? `Índice ${hazard === "fire" ? "meteorológico" : "ambiental"} ${(item.risk_index * 100).toFixed(0)}/100` : `Probabilidad estimada ${pct(item.probability)}`}</strong>
      <p>{date(item.valid_from)} → {date(item.valid_to)}</p><p>{item.action}</p>
      {!!item.provenance?.hourly?.length && <details><summary>Pronóstico hora por hora</summary><div className="predictive-hourly"><table><thead><tr><th>Hora local</th><th>{hazard === "hydric" ? "Lluvia (mm/h)" : hazard === "health_heat" ? "Sensación térmica (°C)" : hazard === "health_air" ? "PM2.5 (μg/m³)" : "Temperatura (°C)"}</th>{hazard === "fire" && <><th>Humedad (%)</th><th>Viento (km/h)</th><th>Lluvia (mm)</th></>}</tr></thead><tbody>{item.provenance.hourly.map((hour) => <tr key={String(hour.time)}><td>{date(String(hour.time))}</td><td>{Number(hour[hazard === "hydric" ? "precipitation" : hazard === "health_heat" ? "apparent_temperature" : hazard === "health_air" ? "pm2_5" : "temperature_2m"]).toFixed(1)}</td>{hazard === "fire" && <><td>{Number(hour.relative_humidity_2m).toFixed(0)}</td><td>{Number(hour.wind_speed_10m).toFixed(1)}</td><td>{Number(hour.precipitation).toFixed(1)}</td></>}</tr>)}</tbody></table></div></details>}
      <details><summary>Fuentes y explicación</summary><ul>{item.explanation.map((reason) => <li key={reason}>{reason}</li>)}</ul><p>Open-Meteo · datos modelados. Área de vigilancia de 5 km del nodo; requiere verificación local. {risk.scope}</p><p>Versión: {item.model_version}<br />Emitido: {date(item.issued_at)}</p><p>{item.probability == null ? "Este índice no es una probabilidad de incidente." : "Estimación local en modo sombra; requiere validación prospectiva."}</p></details>
    </article>)}</div>
    {forecasts.length > 30 && <p>Se muestran las 30 emisiones más recientes de las {forecasts.length} consultadas.</p>}

    <h2>Validación · últimos 90 días</h2>
    {evaluation && <><p>{evaluation.labels_policy} Datos al {date(evaluation.generated_at)}.</p>
      <div className="predictive-grid">{evaluation.metrics.map((metric) => <article className="predictive-card" key={metric.model_version}>
        <h3>{metric.model_version}</h3><p>Período de esta versión desde {date(metric.scope_start)}.</p><dl className="predictive-metrics">
          <div><dt>Ventanas evaluadas</dt><dd>{metric.evaluated}</dd></div>
          <div><dt>Pendientes de verificación</dt><dd>{metric.pending_labels}</dd></div>
          <div><dt>Precisión de avisos</dt><dd>{pct(metric.precision)}</dd></div>
          <div><dt>Recall de ventanas</dt><dd>{pct(metric.recall)}</dd></div>
          <div><dt>Falsas alarmas</dt><dd>{metric.fp}</dd></div>
          <div><dt>Eventos independientes omitidos</dt><dd>{metric.events_missed} / {metric.independent_events}</dd></div>
          <div><dt>Recall de eventos independientes</dt><dd>{pct(metric.event_recall)}</dd></div>
          <div><dt>Anticipación mediana</dt><dd>{metric.median_lead_hours == null ? "Sin evidencia" : `${metric.median_lead_hours.toFixed(1)} h`}</dd></div>
          <div><dt>Brier de probabilidades</dt><dd>{metric.brier == null ? "No aplica al índice" : metric.brier.toFixed(4)}</dd></div>
        </dl>
        {metric.calibration.length > 0 && <details><summary>Calibración observada</summary>{metric.calibration.map((bin, index) => <p key={index}>Predicha {pct(bin.mean_probability)} · observada {pct(bin.observed_rate)} · {bin.count} ventanas</p>)}</details>}
      </article>)}</div>
    </>}

    {canOperate && <form className="predictive-card predictive-form" onSubmit={verify}>
      <h2>Registrar evidencia independiente</h2><p>Registrá incidentes aunque no haya una alerta. Para certificar ausencia de {risk.event.toLowerCase()}, verificá todo el período y el área de vigilancia de 5 km. Las fechas se ingresan en tu hora local.</p>
      <label>Nodo observado<select required value={draft.device_id} onChange={(event) => setDraft({ ...draft, device_id: event.target.value })}><option value="">Seleccionar nodo</option>{nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
      <label>Resultado<select value={draft.outcome} onChange={(event) => setDraft({ ...draft, outcome: event.target.value })}><option value="event">{risk.event} verificado</option><option value="no_event">Período completo sin {risk.event.toLowerCase()}</option></select></label>
      <label>{draft.outcome === "event" ? "Inicio del incidente" : "Inicio de cobertura"}<input required type="datetime-local" value={draft.start_at} onChange={(event) => setDraft({ ...draft, start_at: event.target.value })} /></label>
      {draft.outcome === "no_event" && <label>Fin de cobertura<input required type="datetime-local" value={draft.end_at} onChange={(event) => setDraft({ ...draft, end_at: event.target.value })} /></label>}
      <label>Fuente de evidencia<select value={draft.source} onChange={(event) => setDraft({ ...draft, source: event.target.value })}><option value="field_report">Verificación de campo</option><option value="official_record">Registro oficial</option><option value="sensor_verified">Sensor verificado</option></select></label>
      <label>Referencia única<input required minLength={3} maxLength={160} value={draft.reference} onChange={(event) => setDraft({ ...draft, reference: event.target.value })} /></label>
      {hazard.startsWith("health_") && <p>Registrar evidencia sanitaria agregada y su referencia oficial, sin nombres ni datos personales de pacientes. Un valor de pronóstico no verifica un incidente sanitario.</p>}
      <label>Evidencia y cobertura<textarea required minLength={10} maxLength={2000} value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} /></label>
      <label className="predictive-check"><input required type="checkbox" checked={coverage} onChange={(event) => setCoverage(event.target.checked)} />Verifiqué el resultado y el área del nodo con evidencia independiente; no inferí ausencia por falta de alertas.</label>
      <button className="primary" disabled={busy || !coverage}>Guardar resultado verificado</button>
      <p>El registro es inmutable y auditado. No se aceptan fechas futuras ni evidencia contradictoria.</p>
    </form>}

    {role === "admin" && <article className="predictive-card"><h2>Modelos propios · {horizon} h</h2>
      <p>Entrenamiento supervisado con pronósticos y resultados archivados. La separación temporal elimina ventanas solapadas y reserva bloques distintos para calibración y test. Datos insuficientes bloquean el entrenamiento.</p>
      <button disabled={busy} onClick={() => void mutate("/predictions/models/train", { hazard, horizon_hours: horizon, days: 180 }, "Modelo candidato entrenado; revisar evaluación antes de activarlo.")}>Entrenar candidato</button>
      <button disabled={busy || !enabled || !consent || !activeId} onClick={() => void mutate("/predictions/models/deploy", { hazard, horizon_hours: horizon, enabled: true, external_weather_consent: true, model_id: null }, "Reversión al índice ambiental completada.")}>Volver al índice ambiental</button>
      {evaluation?.models.map((model) => <div className="predictive-model" key={model.id}><h3>{model.version}{activeId === model.id ? " · activo en sombra" : ""}</h3>
        <p>{model.eligible ? "Supera puertas temporales locales" : "No habilitado: no supera evaluación"}. Entrenamiento {model.evaluation.train} · calibración {model.evaluation.calibration} · test {model.evaluation.test} · purgadas {model.evaluation.purged}.</p>
        <p>Brier {model.evaluation.brier.toFixed(4)} · prevalencia {model.evaluation.prevalence_brier.toFixed(4)} · índice {model.evaluation.heuristic_index_brier.toFixed(4)}.</p>
        <p>Deriva: {model.drift.status === "review" ? "Revisar cambio de distribución" : model.drift.status === "insufficient_data" ? "Datos recientes insuficientes" : "Dentro de referencia"}. {model.drift.samples} ventanas.</p>
        <p>{model.evaluation.scope}</p><button disabled={busy || !model.eligible || !consent || !enabled || activeId === model.id} onClick={() => void mutate("/predictions/models/deploy", { hazard, horizon_hours: horizon, enabled: true, external_weather_consent: true, model_id: model.id }, "Modelo activado en sombra; la línea base seguirá emitiéndose para comparación.")}>Usar modelo en sombra</button>
      </div>)}
    </article>}
    <details className="predictive-card"><summary>Últimos resultados verificados</summary>{observations.map((item) => <p key={item.id}>{item.outcome === "event" ? "Incidente" : "Sin incidente"} · {date(item.start_at)} → {date(item.end_at)} · {item.source} · {item.reference}</p>)}</details>
  </section>;
}
