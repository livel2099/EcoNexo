"use client";
import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPost } from "../app/lib/api";

type Assessment = {
  id: string; created_at: string;
  evidence: { observed_on: string; source: string } & Record<string, unknown>;
  result: { status: string; vegetation: string; ndvi_delta: number | null; estimated_animals: number | null;
    limitations: string; missing: string[]; risks: { factor: string; level: string; action: string }[];
    sources: { name: string; url: string; scope: string }[] };
};
type Satellite = { series: { day: string; ndvi: number; valid_pixel_pct: number }[]; source: string; note: string };
type Conditions = {
  as_of: string | null; precipitation_7d_mm: number | null; balance_14d_mm: number | null;
  soil_moisture_pct: number | null; soil_moisture_ts: string | null; soil_moisture_source: string | null;
  water_hint: boolean | null; flooding_hint: boolean | null; note: string;
};
const CARRY_FORWARD_KEYS = [
  "baseline_ndvi", "dry_matter_kg_ha", "utilization_pct", "animal_demand_kg_day", "grazing_days", "herd_size",
  "soil_suitable", "water_suitable", "flooding", "erosion", "pesticide_exposure", "forage_verified",
] as const;
const numeric = [
  ["ndvi", "NDVI medio del lote", -1, 1, "0.001"],
  ["baseline_ndvi", "NDVI de referencia estacional comparable", -1, 1, "0.001"],
  ["valid_pixel_pct", "Píxeles válidos del lote (%)", 0, 100, "0.1"],
  ["dry_matter_kg_ha", "Materia seca aprovechable medida (kg/ha)", 0, 100000, "0.1"],
  ["utilization_pct", "Fracción de aprovechamiento prevista (%)", 0.1, 100, "0.1"],
  ["animal_demand_kg_day", "Demanda por animal (kg MS/día)", 0.1, 200, "0.1"],
  ["grazing_days", "Días de pastoreo previstos", 1, 366, "1"],
  ["herd_size", "Cantidad de animales", 0, 1000000, "1"],
] as const;
const checks = [
  ["soil_suitable", "Suelo apto para el cultivo o uso (análisis profesional)"],
  ["water_suitable", "Agua suficiente y de calidad adecuada"],
  ["flooding", "Presencia de anegamiento"], ["erosion", "Presencia de erosión"],
  ["pesticide_exposure", "Exposición a plaguicidas sin controlar"],
  ["forage_verified", "Especies forrajeras y calidad verificadas"],
] as const;
const label = (value: string) => value.replaceAll("_", " ");

export default function EcoCampoAssessment({ lotId, token, areaHa }: { lotId: string; token: string; areaHa: number }) {
  const [section, setSection] = useState<"aptitud" | "presupuesto" | "ndvi" | "historial">("aptitud");
  const [saved, setSaved] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [history, setHistory] = useState<Assessment[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [polygon, setPolygon] = useState("");
  const [satellite, setSatellite] = useState<Satellite | null>(null);
  const [satBusy, setSatBusy] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});
  const [observationDate, setObservationDate] = useState("");
  const [source, setSource] = useState("");
  const [conditions, setConditions] = useState<Conditions | null>(null);
  async function loadSatellite() {
    setSatBusy(true); setError("");
    try {
      const geometry = JSON.parse(polygon);
      const result = await apiPost<Satellite>(`/ecocampo/lots/${lotId}/ndvi`, token, geometry);
      setSatellite(result);
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo consultar NDVI"); }
    finally { setSatBusy(false); }
  }
  useEffect(() => {
    let active = true;
    Promise.allSettled([
      apiGet<Assessment[]>(`/ecocampo/lots/${lotId}/assessments`, token),
      apiGet<{ polygon: unknown; result: Satellite }[]>(`/ecocampo/lots/${lotId}/ndvi`, token),
      apiGet<Conditions>(`/ecocampo/lots/${lotId}/conditions`, token),
    ]).then(([historyResult, satelliteResult, conditionsResult]) => {
      if (!active) return;
      const historyRows = historyResult.status === "fulfilled" ? historyResult.value : [];
      if (historyResult.status === "fulfilled") setHistory(historyRows);
      else setHistoryError(historyResult.reason instanceof Error ? historyResult.reason.message : "No se pudo cargar el historial");
      setLoaded(true);
      const satelliteRows = satelliteResult.status === "fulfilled" ? satelliteResult.value : [];
      if (satelliteResult.status === "fulfilled" && satelliteRows[0]) {
        setPolygon(JSON.stringify(satelliteRows[0].polygon)); setSatellite(satelliteRows[0].result);
      } else if (satelliteResult.status === "rejected") {
        setError(satelliteResult.reason instanceof Error ? satelliteResult.reason.message : "No se pudo cargar NDVI");
      }
      const cond = conditionsResult.status === "fulfilled" ? conditionsResult.value : null;
      if (cond) setConditions(cond);

      // Autocompletado: última evaluación guardada como base, y encima las
      // lecturas más recientes (NDVI satelital, humedad/lluvia del Centro de
      // Comando) cuando son más confiables que un dato viejo. Nunca pisa lo
      // que la persona ya haya escrito (setValues conserva `previous`).
      const last = historyRows[0]?.evidence;
      const patch: Record<string, string> = {};
      for (const key of CARRY_FORWARD_KEYS) {
        const value = last?.[key];
        if (value !== undefined && value !== null) patch[key] = String(value);
      }
      const usablePoints = (satelliteRows[0]?.result.series ?? []).filter(point => point.valid_pixel_pct >= 70);
      const bestPoint = usablePoints[usablePoints.length - 1];
      let fallbackDate = new Date().toISOString().slice(0, 10);
      if (bestPoint) {
        patch.ndvi = String(bestPoint.ndvi);
        patch.valid_pixel_pct = String(bestPoint.valid_pixel_pct);
        const satelliteSource = satelliteRows[0].result.source;
        fallbackDate = bestPoint.day;
        setSource(current => current || `${satelliteSource}; completar informe de campo y referencia estacional`);
      }
      setObservationDate(current => current || fallbackDate);
      if (cond?.water_hint !== null && cond?.water_hint !== undefined) patch.water_suitable = String(cond.water_hint);
      if (cond?.flooding_hint !== null && cond?.flooding_hint !== undefined) patch.flooding = String(cond.flooding_hint);
      if (Object.keys(patch).length) setValues(previous => ({ ...patch, ...previous }));
    });
    return () => { active = false; };
  }, [lotId, token]);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setSaved(false);
    const form = new FormData(event.currentTarget);
    const data: Record<string, unknown> = { observed_on: form.get("observed_on"), source: form.get("source"), use: form.get("use") };
    numeric.forEach(([key]) => { const v = String(form.get(key) ?? ""); data[key] = v === "" ? null : Number(v); });
    checks.forEach(([key]) => { const v = form.get(key); data[key] = v === "" ? null : v === "true"; });
    try {
      const row = await apiPost<Assessment>(`/ecocampo/lots/${lotId}/assessments`, token, data);
      setHistory(previous => [row, ...previous].slice(0, 50)); setLoaded(true); setSaved(true); setHistoryError("");
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo guardar"); }
    finally { setBusy(false); }
  }
  return <section className="agro-card" aria-label="Evaluación EcoCampo">
    <nav className="ecocampo-tabs" aria-label="Herramientas EcoCampo">
      {([["aptitud", "Evaluación de aptitud"], ["presupuesto", "Presupuesto forrajero"], ["ndvi", "Monitoreo NDVI"], ["historial", "Historial"]] as const).map(([key, title]) => <button type="button" key={key} aria-pressed={section === key} onClick={() => { setSection(key); setSaved(false); }}>{title}</button>)}
    </nav>
    <div className="agro-tiles" aria-label="Último resultado guardado">
      <article><span>Aptitud</span><strong style={{fontSize:"1rem"}}>{history[0] ? label(history[0].result.status) : "Sin evaluar"}</strong></article>
      <article><span>Presupuesto forrajero</span><strong style={{fontSize:"1rem"}}>{history[0]?.result.estimated_animals != null ? `${history[0].result.estimated_animals} animales` : "Sin cálculo guardado"}</strong></article>
      <article><span>Evaluaciones guardadas</span><strong>{loaded ? history.length : "—"}</strong></article>
    </div>
    {saved && <p role="status" className="agro-notice">Evaluación procesada y guardada. Aptitud: {label(history[0].result.status)}. Presupuesto: {history[0].result.estimated_animals === null ? "faltan datos para calcular" : `${history[0].result.estimated_animals} animales`}. Disponible en Historial.</p>}
    {historyError && <p role="alert">{historyError}</p>}
    <p>Evaluación por lote con evidencia trazable. Consultá Sentinel-2 sobre el polígono real o cargá un análisis externo. Las mediciones de campo deben corresponder a la fecha indicada.</p>
    {error && <p role="alert" className="agro-lot-error">{error}</p>}
    <section hidden={section !== "ndvi"}><h3>Monitoreo satelital · Sentinel-2</h3>
      <label>Polígono GeoJSON WGS84 (longitud, latitud)<textarea aria-label="Polígono GeoJSON" value={polygon} onChange={e => setPolygon(e.target.value)} rows={5} placeholder='{"type":"Polygon","coordinates":[[[lon,lat],...]]}' /></label>
      <p>Ingresá los límites reales del lote. No se reemplazan por el centro de la localidad. Requiere credenciales Copernicus configuradas por el administrador.</p>
      <button type="button" disabled={satBusy || !polygon.trim()} onClick={() => void loadSatellite()}>{satBusy ? "Consultando…" : "Consultar últimos 30 días"}</button>
      {satellite && <><p>{satellite.source}. {satellite.note}</p>
        {!satellite.series.length && <p>Sin observaciones válidas en el período. No se genera una estimación.</p>}
        <div className="agro-series-table"><table><thead><tr><th>Fecha</th><th>NDVI</th><th>Píxeles válidos</th><th>Evaluación</th></tr></thead><tbody>
          {satellite.series.map(point => <tr key={point.day}><td>{point.day}</td><td>{point.ndvi}</td><td>{point.valid_pixel_pct}%</td><td><button type="button" onClick={() => {
            setValues(previous => ({...previous, ndvi: String(point.ndvi), valid_pixel_pct: String(point.valid_pixel_pct)}));
            setObservationDate(point.day); setSource(satellite.source + "; completar informe de campo y referencia estacional");
          }}>Usar observación</button></td></tr>)}
        </tbody></table></div></>}
    </section>
    <section hidden={section !== "aptitud" && section !== "presupuesto"}>
      <h3>{section === "presupuesto" ? "Calcular presupuesto forrajero" : "Procesar evaluación de aptitud"}</h3>
      <p>{section === "presupuesto" ? `Presupuesto de alimento para ${areaHa} ha. Ingresá materia seca, aprovechamiento, demanda animal y días; verificá las especies forrajeras.` : "Cargá evidencia y presioná Procesar evaluación. El resultado identifica restricciones y datos faltantes para este lote."}</p>
      {(satellite || conditions || history.length > 0) && <p className="agro-notice">
        Precargamos lo que ya sabemos del lote: {[
          satellite ? "el último NDVI de Sentinel-2" : null,
          conditions?.soil_moisture_source ? conditions.soil_moisture_source.toLowerCase() : conditions?.balance_14d_mm != null ? "el balance hídrico climático de EcoNexo AG" : null,
          history.length > 0 ? "tu última evaluación guardada" : null,
        ].filter(Boolean).join(", ") || "sin lecturas previas para este lote"}. Son sugerencias editables, no reemplazan la inspección del lote: revisá cada campo antes de procesar.
      </p>}
      {!satellite && <p className="agro-notice">Este lote todavía no tiene NDVI cargado: entrá a «Monitoreo NDVI», pegá el polígono real del lote y tocá «Consultar últimos 30 días» una vez. De ahí en adelante, la última lectura válida se va a autocompletar sola en cada evaluación nueva.</p>}
      <p>Suelo apto, erosión y exposición a plaguicidas quedan siempre en «Sin verificar» la primera vez: la plataforma no tiene un sensor que los mida, así que nunca se completan solos. Agua suficiente, anegamiento y NDVI sí se autocompletan cuando hay una lectura reciente del nodo más cercano, el balance hídrico o el satélite.</p>
      <form className="agro-form" onSubmit={save}>
        <label>Fecha de observación<input name="observed_on" value={observationDate} onChange={e => setObservationDate(e.target.value)} type="date" required max={new Date().toISOString().slice(0, 10)} /></label>
        <label>Destino<select name="use" defaultValue="mixto"><option value="agricultura">Agricultura</option><option value="ganaderia">Ganadería</option><option value="mixto">Mixto</option></select></label>
        <label className="agro-form-wide">Fuente, sensor, período de referencia e informe de campo<input name="source" value={source} onChange={e => setSource(e.target.value)} required minLength={3} maxLength={500} placeholder="Informe, responsable y método de medición" /></label>
        {numeric.map(([key, name, min, max, step], index) => <label hidden={section === "presupuesto" ? index < 3 : index >= 3} key={key}>{name}<input type="number" name={key} value={values[key] ?? ""} onChange={e => setValues(previous => ({...previous, [key]: e.target.value}))} min={min} max={max} step={step} placeholder="Sin dato" /></label>)}
        {checks.map(([key, name]) => <label hidden={section === "presupuesto" ? key !== "forage_verified" : key === "forage_verified"} key={key}>{name}<select name={key} value={values[key] ?? ""} onChange={e => setValues(previous => ({...previous, [key]: e.target.value}))}><option value="">Sin verificar</option><option value="true">Sí</option><option value="false">No</option></select></label>)}
        <p className="agro-form-wide">El NDVI no equivale a toneladas ni demuestra aptitud. Compará igual sensor, estación y cobertura. Dejá vacíos los datos desconocidos. El presupuesto ganadero usa materia seca × superficie × aprovechamiento / demanda / días.</p>
        <button disabled={busy} type="submit">{busy ? "Procesando y guardando…" : section === "presupuesto" ? "Calcular y guardar presupuesto" : "Procesar evaluación y guardar"}</button>
      </form>
    </section>
    <section hidden={section !== "historial"}><h3>Historial de evaluaciones</h3><p>Resultados guardados con fecha y evidencia. Cada procesamiento incorpora una nueva evaluación.</p>
    {loaded && history.length === 0 && <p>Sin evaluaciones. Cargá evidencia para evaluar este lote.</p>}
    {history.map((row, index) => <details key={row.id} open={index === 0}>
      <summary>{row.evidence.observed_on} · {label(row.result.status)} · evaluación guardada</summary>
      <p>Vegetación: <strong>{label(row.result.vegetation)}</strong>. Variación NDVI: {row.result.ndvi_delta ?? "Sin referencia válida"}.</p>
      <p>Presupuesto forrajero: {row.result.estimated_animals === null ? "Sin datos suficientes" : `${row.result.estimated_animals} animales durante el período declarado`}. Rendimiento agrícola: requiere modelo calibrado y validación de campo.</p>
      {row.result.risks.map((risk, i) => <p key={i} className="agro-notice"><strong>{risk.level.toUpperCase()} · {risk.factor}</strong>: {risk.action}</p>)}
      {row.result.missing.length > 0 && <><h4>Datos pendientes</h4><ul>{row.result.missing.map(item => <li key={item}>{item}</li>)}</ul></>}
      <p>{row.result.limitations}</p><p>Procedencia declarada: {row.evidence.source}</p>
      <ul>{row.result.sources.map(source => <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.name}</a> — {source.scope}</li>)}</ul>
    </details>)}
    </section>
    {section !== "historial" && history[0] && <article className="agro-card"><h3>Resultado y factores de riesgo</h3>{history[0].result.risks.map((risk, i) => <p key={i}><strong>{risk.level.toUpperCase()} · {risk.factor}</strong>: {risk.action}</p>)}{!history[0].result.risks.length && <p>Sin riesgos declarados identificados. Revisá los datos faltantes antes de decidir.</p>}<ul>{history[0].result.missing.map(item => <li key={item}>{item}</li>)}</ul><button onClick={() => setSection("historial")}>Ver evaluación completa e historial</button></article>}
  </section>;
}