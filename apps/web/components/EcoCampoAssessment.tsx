"use client";
import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPost } from "../app/lib/api";

type Assessment = {
  id: string; created_at: string; evidence: { observed_on: string; source: string };
  result: { status: string; vegetation: string; ndvi_delta: number | null; estimated_animals: number | null;
    limitations: string; missing: string[]; risks: { factor: string; level: string; action: string }[];
    sources: { name: string; url: string; scope: string }[] };
};
type Satellite = { series: { day: string; ndvi: number; valid_pixel_pct: number }[]; source: string; note: string };
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

export default function EcoCampoAssessment({ lotId, token }: { lotId: string; token: string }) {
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
  async function loadSatellite() {
    setSatBusy(true); setError("");
    try {
      const geometry = JSON.parse(polygon);
      const result = await apiPost<Satellite>(`/agro/lots/${lotId}/ecocampo/ndvi`, token, geometry);
      setSatellite(result);
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo consultar NDVI"); }
    finally { setSatBusy(false); }
  }
  useEffect(() => {
    let active = true;
    apiGet<Assessment[]>(`/agro/lots/${lotId}/ecocampo`, token)
      .then(rows => { if (active) { setHistory(rows); setLoaded(true); } })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : "No se pudo cargar la evaluación"); });
    apiGet<{polygon: unknown; result: Satellite}[]>(`/agro/lots/${lotId}/ecocampo/ndvi`, token)
      .then(rows => { if (active && rows[0]) { setPolygon(JSON.stringify(rows[0].polygon)); setSatellite(rows[0].result); } })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : "No se pudo cargar NDVI"); });
    return () => { active = false; };
  }, [lotId, token]);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    const data: Record<string, unknown> = { observed_on: form.get("observed_on"), source: form.get("source"), use: form.get("use") };
    numeric.forEach(([key]) => { const v = String(form.get(key) ?? ""); data[key] = v === "" ? null : Number(v); });
    checks.forEach(([key]) => { const v = form.get(key); data[key] = v === "" ? null : v === "true"; });
    try {
      const row = await apiPost<Assessment>(`/agro/lots/${lotId}/ecocampo`, token, data);
      setHistory(previous => [row, ...previous].slice(0, 50)); setLoaded(true);
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo guardar"); }
    finally { setBusy(false); }
  }
  return <section className="agro-card" aria-label="Evaluación EcoCampo">
    <h3>EcoCampo · aptitud, vegetación y ganadería</h3>
    <p>Evaluación por lote con evidencia trazable. Consultá Sentinel-2 sobre el polígono real o cargá un análisis externo. Las mediciones de campo deben corresponder a la fecha indicada.</p>
    {error && <p role="alert" className="agro-lot-error">{error}</p>}
    <details><summary>Monitoreo satelital · Sentinel-2</summary>
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
    </details>
    <details><summary>Cargar evidencia y evaluar lote</summary>
      <form className="agro-form" onSubmit={save}>
        <label>Fecha de observación<input name="observed_on" value={observationDate} onChange={e => setObservationDate(e.target.value)} type="date" required max={new Date().toISOString().slice(0, 10)} /></label>
        <label>Destino<select name="use" defaultValue="mixto"><option value="agricultura">Agricultura</option><option value="ganaderia">Ganadería</option><option value="mixto">Mixto</option></select></label>
        <label className="agro-form-wide">Fuente, sensor, período de referencia e informe de campo<input name="source" value={source} onChange={e => setSource(e.target.value)} required minLength={3} maxLength={500} placeholder="Informe, responsable y método de medición" /></label>
        {numeric.map(([key, name, min, max, step]) => <label key={key}>{name}<input type="number" name={key} value={values[key] ?? ""} onChange={e => setValues(previous => ({...previous, [key]: e.target.value}))} min={min} max={max} step={step} placeholder="Sin dato" /></label>)}
        {checks.map(([key, name]) => <label key={key}>{name}<select name={key} defaultValue=""><option value="">Sin verificar</option><option value="true">Sí</option><option value="false">No</option></select></label>)}
        <p className="agro-form-wide">El NDVI no equivale a toneladas ni demuestra aptitud. Compará igual sensor, estación y cobertura. Dejá vacíos los datos desconocidos. El presupuesto ganadero usa materia seca × superficie × aprovechamiento / demanda / días.</p>
        <button disabled={busy} type="submit">{busy ? "Guardando…" : "Evaluar y guardar"}</button>
      </form>
    </details>
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
  </section>;
}