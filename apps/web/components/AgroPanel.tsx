"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../app/lib/api";
import type { ApiError } from "../app/lib/api";
import { MISIONES_OPERATIONAL_HUBS } from "../app/lib/misiones";
import type {
  AgroCrop,
  AgroDaily,
  AgroLot,
  AgroRefresh,
  AgroSummary,
} from "../app/lib/types";

const NIVEL_ORDEN = { alto: 0, medio: 1, bajo: 2 } as const;

const KIND_LABEL: Record<string, string> = {
  helada: "Helada",
  riego: "Riego",
  pulverizacion: "Pulverización",
  enfermedad: "Enfermedad",
  estres_termico: "Estrés térmico",
  fenologia: "Fenología",
};

function fecha(valor: string | null): string {
  if (!valor) return "—";
  return new Date(valor).toLocaleDateString("es-AR", { day: "2-digit", month: "short" });
}

function fechaHora(valor: string | null): string {
  if (!valor) return "nunca";
  return new Date(valor).toLocaleString("es-AR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

/**
 * Gráfico de balance hídrico acumulado. Es SVG inline a propósito: el panel no
 * puede depender de una librería externa porque la web se exporta estática.
 */
function BalanceChart({ series }: { series: AgroDaily[] }) {
  const puntos = series.filter((d) => d.balance_accum_mm != null);
  if (puntos.length < 2) return null;

  const ancho = 760;
  const alto = 160;
  const valores = puntos.map((d) => d.balance_accum_mm as number);
  const min = Math.min(...valores, 0);
  const max = Math.max(...valores, 0);
  const rango = max - min || 1;
  const x = (i: number) => (i / (puntos.length - 1)) * ancho;
  const y = (v: number) => alto - ((v - min) / rango) * alto;
  const cero = y(0);

  const linea = puntos.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d.balance_accum_mm as number).toFixed(1)}`).join(" ");
  const area = `${linea} L${ancho},${cero} L0,${cero} Z`;
  const inicioPronostico = puntos.findIndex((d) => d.is_forecast);

  return (
    <figure className="agro-chart">
      <svg viewBox={`0 0 ${ancho} ${alto}`} preserveAspectRatio="none" role="img"
           aria-label="Balance hídrico acumulado: lluvia menos evapotranspiración del cultivo">
        <path d={area} className="agro-chart-area" />
        <line x1="0" y1={cero} x2={ancho} y2={cero} className="agro-chart-zero" />
        {inicioPronostico > 0 && (
          <line x1={x(inicioPronostico)} y1="0" x2={x(inicioPronostico)} y2={alto}
                className="agro-chart-forecast" />
        )}
        <path d={linea} className="agro-chart-line" />
      </svg>
      <figcaption>
        Balance hídrico acumulado (mm): lluvia menos ETc. Máximo {max.toFixed(0)} mm,
        mínimo {min.toFixed(0)} mm.{inicioPronostico > 0 ? " La línea vertical marca el inicio del pronóstico." : ""}
      </figcaption>
    </figure>
  );
}

export default function AgroPanel({ token }: { token: string }) {
  const [crops, setCrops] = useState<AgroCrop[]>([]);
  const [lots, setLots] = useState<AgroLot[]>([]);
  const [summary, setSummary] = useState<AgroSummary | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [series, setSeries] = useState<AgroDaily[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [locked, setLocked] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState({
    name: "",
    crop_key: "yerba_mate",
    sowing_date: "",
    area_ha: "10",
    municipality: "Posadas",
    lat: "",
    lon: "",
    notes: "",
  });

  const load = useCallback(async () => {
    const [catalogo, lotes, resumen] = await Promise.all([
      apiGet<AgroCrop[]>("/agro/crops", token),
      apiGet<AgroLot[]>("/agro/lots", token),
      apiGet<AgroSummary>("/agro/summary", token),
    ]);
    setCrops(catalogo);
    setLots(lotes);
    setSummary(resumen);
    return lotes;
  }, [token]);

  useEffect(() => {
    load().catch((cause) => {
      // 402 no es una falla: es el modulo sin licencia. Merece otra pantalla.
      if ((cause as ApiError)?.status === 402) {
        setLocked(cause instanceof Error ? cause.message : "Módulo no habilitado");
        return;
      }
      setError(cause instanceof Error ? cause.message : "No se pudo cargar EcoNexo AG");
    });
  }, [load]);


  const loteActual = useMemo(() => lots.find((l) => l.id === selected) || null, [lots, selected]);
  const cropActual = useMemo(
    () => crops.find((c) => c.key === (loteActual?.crop_key || draft.crop_key)) || null,
    [crops, loteActual, draft.crop_key],
  );

  const avisos = useMemo(
    () => lots.flatMap((l) => l.advisories.map((a) => ({ ...a, lot_name: a.lot_name || l.name })))
      .sort((a, b) => NIVEL_ORDEN[a.level] - NIVEL_ORDEN[b.level]),
    [lots],
  );

  async function verSerie(lotId: string) {
    setSelected(lotId);
    setSeries([]);
    try {
      setSeries(await apiGet<AgroDaily[]>(`/agro/lots/${lotId}/series?days=180`, token));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo leer la serie");
    }
  }

  async function refrescar(lot: AgroLot) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const resultado = await apiPost<AgroRefresh>(`/agro/lots/${lot.id}/refresh`, token, {});
      setNotice(`${lot.name}: ${resultado.detail} Fuentes: ${resultado.sources.join(" · ")}`);
      await load();
      if (selected === lot.id) await verSerie(lot.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo procesar el lote");
    } finally {
      setBusy(false);
    }
  }

  async function refrescarTodos() {
    setBusy(true);
    setError("");
    const fallos: string[] = [];
    for (const lot of lots.filter((l) => l.is_active)) {
      try {
        await apiPost<AgroRefresh>(`/agro/lots/${lot.id}/refresh`, token, {});
      } catch {
        fallos.push(lot.name);
      }
    }
    await load();
    setBusy(false);
    setNotice(fallos.length
      ? `Procesados con errores en: ${fallos.join(", ")}`
      : "Todos los lotes activos fueron procesados con datos reales.");
  }

  async function crearLote(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      // Los municipios del catalogo no traen coordenada; los hubs operativos si.
      const hub = MISIONES_OPERATIONAL_HUBS.find((m) => m.name === draft.municipality);
      const lat = draft.lat.trim() ? Number(draft.lat) : hub?.lat;
      const lon = draft.lon.trim() ? Number(draft.lon) : hub?.lon;
      if (lat == null || lon == null || Number.isNaN(lat) || Number.isNaN(lon)) {
        throw new Error("Elegí una localidad o cargá la coordenada del lote.");
      }
      await apiPost<AgroLot>("/agro/lots", token, {
        name: draft.name.trim(),
        crop_key: draft.crop_key,
        sowing_date: draft.sowing_date || null,
        area_ha: Number(draft.area_ha),
        lat,
        lon,
        notes: draft.notes.trim() || null,
      });
      setShowForm(false);
      setDraft({ ...draft, name: "", sowing_date: "", notes: "", lat: "", lon: "" });
      setNotice("Lote creado. Ejecutá «Procesar» para traer los datos meteorológicos reales.");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo crear el lote");
    } finally {
      setBusy(false);
    }
  }

  async function borrarLote(lot: AgroLot) {
    if (!window.confirm(`¿Eliminar el lote ${lot.name} y toda su serie?`)) return;
    setBusy(true);
    try {
      await apiDelete(`/agro/lots/${lot.id}`, token);
      if (selected === lot.id) setSelected(null);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo eliminar el lote");
    } finally {
      setBusy(false);
    }
  }

  async function alternarActivo(lot: AgroLot) {
    setBusy(true);
    try {
      await apiPatch(`/agro/lots/${lot.id}`, token, { is_active: !lot.is_active });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo actualizar el lote");
    } finally {
      setBusy(false);
    }
  }

  if (locked) {
    return (
      <section className="agro-console">
        <article className="agro-locked">
          <span className="eyebrow">ECONEXO AG · MÓDULO NO HABILITADO</span>
          <h2>Inteligencia agronómica por lote</h2>
          <p>{locked}</p>
          <ul>
            <li>Fenología por grados día y coeficiente de cultivo por etapa.</li>
            <li>Balance hídrico con ET0 FAO-56 y demanda real del cultivo.</li>
            <li>Ventanas de pulverización por delta-T, viento y ráfagas.</li>
            <li>Riesgo de helada, estrés térmico y presión de enfermedad.</li>
          </ul>
          <p className="agro-locked-note">
            Se habilita desde Admin Core &gt; Suscripción, con el plan EcoNexo AG · Productor
            o cualquier plan que incluya el módulo.
          </p>
        </article>
      </section>
    );
  }

  return (
    <section className="agro-console">
      <header className="agro-header">
        <div>
          <span className="eyebrow">ECONEXO AG · INTELIGENCIA AGRONÓMICA</span>
          <h2>Lotes y decisiones de campo</h2>
          <p>
            Fenología por grados día, balance hídrico con ET0 FAO-56 y ventanas de aplicación,
            calculados sobre reanálisis y pronóstico meteorológico reales de Open-Meteo.
          </p>
        </div>
        <div className="agro-header-actions">
          <button className="primary" disabled={busy || !lots.length} onClick={() => void refrescarTodos()}>
            {busy ? "Procesando…" : "Procesar todos"}
          </button>
          <button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancelar" : "Nuevo lote"}</button>
        </div>
      </header>

      {summary && (
        <div className="agro-tiles">
          <article><span>Lotes activos</span><strong>{summary.lots_active}<small> / {summary.lots_total}</small></strong></article>
          <article><span>Superficie</span><strong>{summary.area_ha.toLocaleString("es-AR")}<small> ha</small></strong></article>
          <article className={summary.advisories_high ? "alto" : ""}><span>Avisos altos</span><strong>{summary.advisories_high}</strong></article>
          <article><span>Avisos medios</span><strong>{summary.advisories_medium}</strong></article>
          <article><span>Último procesamiento</span><strong className="agro-tile-date">{fechaHora(summary.last_refresh_at)}</strong></article>
        </div>
      )}

      {error && <div className="auth-error" role="alert">{error}</div>}
      {notice && <div className="agro-notice" role="status">{notice}</div>}

      {showForm && (
        <form className="agro-form" onSubmit={crearLote}>
          <label>Nombre del lote
            <input required maxLength={120} value={draft.name}
                   onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                   placeholder="Ej. Lote 4 · Colonia Aurora" />
          </label>
          <label>Cultivo
            <select value={draft.crop_key} onChange={(e) => setDraft({ ...draft, crop_key: e.target.value })}>
              {crops.map((c) => <option key={c.key} value={c.key}>{c.name}</option>)}
            </select>
          </label>
          <label>Fecha de siembra {cropActual?.perennial && <small>no aplica en perennes</small>}
            <input type="date" value={draft.sowing_date} disabled={cropActual?.perennial}
                   onChange={(e) => setDraft({ ...draft, sowing_date: e.target.value })} />
          </label>
          <label>Superficie (ha)
            <input type="number" min="0.1" step="0.1" required value={draft.area_ha}
                   onChange={(e) => setDraft({ ...draft, area_ha: e.target.value })} />
          </label>
          <label>Localidad de referencia
            <select value={draft.municipality} onChange={(e) => setDraft({ ...draft, municipality: e.target.value })}>
              {MISIONES_OPERATIONAL_HUBS.map((m) => (
                <option key={`${m.department}-${m.name}`} value={m.name}>{m.name} · Dpto. {m.department}</option>
              ))}
            </select>
          </label>
          <label>Latitud <small>opcional, más precisa</small>
            <input value={draft.lat} onChange={(e) => setDraft({ ...draft, lat: e.target.value })} placeholder="-27.3621" />
          </label>
          <label>Longitud <small>opcional</small>
            <input value={draft.lon} onChange={(e) => setDraft({ ...draft, lon: e.target.value })} placeholder="-55.9008" />
          </label>
          <label className="agro-form-wide">Notas
            <input maxLength={1000} value={draft.notes}
                   onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
                   placeholder="Variedad, manejo, antecedentes del lote" />
          </label>
          <button className="primary agro-form-wide" disabled={busy}>Crear lote</button>
        </form>
      )}

      <div className="agro-layout">
        <div className="agro-lots">
          {!lots.length && <p className="agro-empty">Todavía no hay lotes cargados. Creá el primero para empezar a procesar datos.</p>}
          {lots.map((lot) => (
            <article key={lot.id} className={`agro-lot ${selected === lot.id ? "selected" : ""} ${lot.is_active ? "" : "inactive"}`}>
              <header>
                <div>
                  <strong>{lot.name}</strong>
                  <span>{lot.crop_name} · {lot.area_ha} ha</span>
                </div>
                <small>{lot.last_refresh_at ? `procesado ${fechaHora(lot.last_refresh_at)}` : "sin procesar"}</small>
              </header>
              <dl className="agro-lot-metrics">
                <div><dt>Etapa</dt><dd>{lot.stage_name || "—"}</dd></div>
                <div><dt>Grados día</dt><dd>{lot.gdd_accum != null ? lot.gdd_accum.toFixed(0) : "—"}</dd></div>
                <div><dt>Balance 14 d</dt>
                  <dd className={lot.balance_14d_mm != null && lot.balance_14d_mm < -25 ? "deficit" : ""}>
                    {lot.balance_14d_mm != null ? `${lot.balance_14d_mm.toFixed(0)} mm` : "—"}
                  </dd></div>
              </dl>
              {lot.advisories.length > 0 && (
                <ul className="agro-lot-flags">
                  {lot.advisories.slice(0, 3).map((a) => (
                    <li key={a.id} className={a.level}>{KIND_LABEL[a.kind] || a.kind}</li>
                  ))}
                </ul>
              )}
              <div className="agro-lot-actions">
                <button disabled={busy} onClick={() => void refrescar(lot)}>Procesar</button>
                <button disabled={busy} onClick={() => void verSerie(lot.id)}>Ver serie</button>
                <button disabled={busy} onClick={() => void alternarActivo(lot)}>{lot.is_active ? "Pausar" : "Activar"}</button>
                <button disabled={busy} className="danger" onClick={() => void borrarLote(lot)}>Eliminar</button>
              </div>
            </article>
          ))}
        </div>

        <div className="agro-detail">
          {loteActual && series.length > 0 && (
            <article className="agro-card">
              <h3>{loteActual.name} · serie diaria</h3>
              <BalanceChart series={series} />
              <div className="agro-series-table">
                <table>
                  <thead>
                    <tr><th>Día</th><th>Máx</th><th>Mín</th><th>Lluvia</th><th>ET0</th><th>ETc</th><th>GDD ac.</th><th>Balance ac.</th></tr>
                  </thead>
                  <tbody>
                    {series.slice(-14).map((d) => (
                      <tr key={d.day} className={d.is_forecast ? "forecast" : ""}>
                        <td>{fecha(d.day)}{d.is_forecast && <small> pron.</small>}</td>
                        <td>{d.tmax_c?.toFixed(1) ?? "—"}</td>
                        <td>{d.tmin_c?.toFixed(1) ?? "—"}</td>
                        <td>{d.precipitation_mm?.toFixed(1) ?? "—"}</td>
                        <td>{d.et0_mm?.toFixed(2) ?? "—"}</td>
                        <td>{d.etc_mm?.toFixed(2) ?? "—"}</td>
                        <td>{d.gdd_accum?.toFixed(0) ?? "—"}</td>
                        <td>{d.balance_accum_mm?.toFixed(1) ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          )}

          <article className="agro-card">
            <h3>Recomendaciones vigentes</h3>
            {!avisos.length && <p className="agro-empty">Sin recomendaciones activas. Procesá los lotes para generarlas.</p>}
            {avisos.map((a) => (
              <div key={a.id} className={`agro-advisory ${a.level}`}>
                <header>
                  <span className="agro-advisory-kind">{KIND_LABEL[a.kind] || a.kind}</span>
                  <strong>{a.title}</strong>
                  <small>{a.lot_name}</small>
                </header>
                <p>{a.detail}</p>
              </div>
            ))}
          </article>

          {cropActual && (
            <article className="agro-card">
              <h3>Parámetros de {cropActual.name}</h3>
              <p className="agro-params-note">
                Son valores de literatura (Kc según FAO-56) tomados como punto de partida.
                Deberían calibrarse por zona, cultivar y manejo antes de decidir con ellos.
              </p>
              <dl className="agro-params">
                <div><dt>Temperatura base</dt><dd>{cropActual.t_base_c} °C</dd></div>
                <div><dt>Techo térmico</dt><dd>{cropActual.t_cap_c} °C</dd></div>
                <div><dt>Umbral de helada</dt><dd>{cropActual.frost_c} °C</dd></div>
                <div><dt>Estrés por calor</dt><dd>{cropActual.heat_c} °C</dd></div>
                <div><dt>Enfermedad de referencia</dt><dd>{cropActual.disease.name}</dd></div>
                <div><dt>Condición favorable</dt>
                  <dd>HR ≥ {cropActual.disease.hr_min} % y {cropActual.disease.rango_c[0]}–{cropActual.disease.rango_c[1]} °C por {cropActual.disease.horas_umbral} h</dd></div>
              </dl>
              {cropActual.stages.length > 0 && (
                <table className="agro-stages">
                  <thead><tr><th>Etapa</th><th>GDD</th><th>Kc</th></tr></thead>
                  <tbody>
                    {cropActual.stages.map((s) => (
                      <tr key={s.key}>
                        <td>{s.name}</td>
                        <td>{s.gdd_from}{s.gdd_to != null ? `–${s.gdd_to}` : "+"}</td>
                        <td>{s.kc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </article>
          )}
        </div>
      </div>

      <p className="agro-disclaimer">
        EcoNexo AG procesa datos meteorológicos reales y los traduce a indicadores agronómicos.
        Los indicadores son estimaciones: no miden lo que pasa dentro del lote ni reemplazan la
        recorrida a campo, el análisis de suelo ni la indicación de un profesional.
      </p>
    </section>
  );
}
