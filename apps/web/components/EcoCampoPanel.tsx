"use client";
import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPost } from "../app/lib/api";
import type { AgroLot, AgroCrop } from "../app/lib/types";
import EcoCampoAssessment from "./EcoCampoAssessment";

export default function EcoCampoPanel({ token }: { token: string }) {
  const [lots, setLots] = useState<AgroLot[]>([]);
  const [crops, setCrops] = useState<AgroCrop[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all([apiGet<AgroLot[]>("/ecocampo/lots", token), apiGet<AgroCrop[]>("/ecocampo/crops", token)])
      .then(([rows, catalog]) => { if (active) { setLots(rows); setCrops(catalog); setSelected(rows[0]?.id ?? ""); setLoaded(true); } })
      .catch(cause => { if (active) { setError(cause instanceof Error ? cause.message : "No se pudo abrir EcoCampo"); setLoaded(true); } });
    return () => { active = false; };
  }, [token]);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    try {
      const lot = await apiPost<AgroLot>("/ecocampo/lots", token, {
        name: String(data.get("name")).trim(), crop_key: data.get("crop_key"), area_ha: Number(data.get("area_ha")),
        lat: Number(data.get("lat")), lon: Number(data.get("lon")),
      });
      setLots(previous => [...previous, lot]); setSelected(lot.id); setCreating(false);
    } catch(cause) { setError(cause instanceof Error ? cause.message : "No se pudo crear el lote"); }
    finally { setBusy(false); }
  }
  const lot = lots.find(item => item.id === selected);
  return <section className="view ecocampo-console">
    <header className="agro-header"><div><span className="eyebrow">ECOCAMPO · APTITUD AGROPECUARIA</span>
      <h2>Evaluación de campos y producción</h2>
      <p>Monitoreo NDVI, evaluación de aptitud, presupuesto forrajero e historial por lote.</p>
      <p className="muted">Plan Productor · USD 400 mensuales. Comparte los lotes registrados con EcoNexo AG.</p>
    </div><button onClick={() => setCreating(!creating)} disabled={!loaded}>{creating ? "Cancelar" : "Nuevo lote"}</button></header>
    {error && <p role="alert" className="agro-notice">{error}</p>}
    {!loaded && <p role="status">Cargando lotes de EcoCampo…</p>}
    {creating && <form className="agro-form agro-card" onSubmit={create}>
      <label>Nombre del lote<input name="name" required minLength={2} maxLength={120} /></label>
      <label>Cultivo o cobertura<select name="crop_key"><option value="pastizal">Pastizal / uso ganadero</option>{crops.map(crop => <option key={crop.key} value={crop.key}>{crop.name}</option>)}</select></label>
      <label>Superficie (ha)<input name="area_ha" type="number" min="0.01" max="100000" step="0.01" required /></label>
      <label>Latitud del lote<input name="lat" type="number" min="-90" max="90" step="any" required /></label>
      <label>Longitud del lote<input name="lon" type="number" min="-180" max="180" step="any" required /></label>
      <p>Usá las coordenadas reales del lote. La cobertura territorial actual de la plataforma es Misiones.</p>
      <button disabled={busy} type="submit">{busy ? "Guardando…" : "Crear lote"}</button>
    </form>}
    {loaded && !lots.length && !error && <article className="agro-card"><h3>Empezá con un lote</h3><p>Creá un lote para evaluar su aptitud y guardar su presupuesto forrajero. Los lotes que ya cargaste en EcoNexo AG aparecerán aquí.</p><button onClick={() => setCreating(true)}>Crear primer lote</button></article>}
    {lots.length > 0 && <div className="ecocampo-lot-picker"><label>Lote a evaluar<select value={selected} onChange={event => setSelected(event.target.value)}>{lots.map(item => <option value={item.id} key={item.id}>{item.name} · {item.area_ha} ha</option>)}</select></label><span>{lot?.crop_name} · {lot?.area_ha} ha</span></div>}
    {lot && <EcoCampoAssessment key={lot.id} lotId={lot.id} token={token} areaHa={lot.area_ha} />}
  </section>;
}