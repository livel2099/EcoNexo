"use client";
import { useEffect, useMemo, useState } from "react";
import type { Map as LeafletMap, GeoJSON } from "leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { API, IS_DEMO } from "../app/lib/api";

type AlertProperties = { id: string; kind: "fire"|"deforestation"; source: string; observed_at: string; municipality: string; municipality_code: string; title: string; status: string; confidence?: string };
type AlertFeature = Feature<Geometry, AlertProperties>;
type Source = { source: string; status: "ok"|"partial"|"not_configured"|"unavailable"; message: string; features: AlertFeature[] };
type Feed = { queried_at: string; sources: Source[] };
const statusLabels = { ok: "Consulta disponible", partial: "Cobertura parcial", not_configured: "Sin configurar", unavailable: "No disponible" };

export default function BrazilAlerts({ token, map, municipality }: { token: string; map: LeafletMap|null; municipality: string }) {
  const [feed, setFeed] = useState<Feed|null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const [kind, setKind] = useState("all");
  const [page, setPage] = useState(0);
  useEffect(() => {
    setFeed(null); setError("");
    if (IS_DEMO || !token) {
      setError(IS_DEMO ? "Las alertas reales requieren la API conectada. El modo demostración no genera detecciones." : "Iniciá sesión para consultar alertas.");
      return;
    }
    let disposed = false;
    let active: AbortController|null = null;
    async function refresh() {
      if (active) return;
      const controller = new AbortController(); active = controller;
      const timeout = setTimeout(() => controller.abort(), 45000);
      setBusy(true); setError("");
      try {
        const response = await fetch(API + "/brasil/mato-grosso/alerts", { headers: { Authorization: "Bearer " + token }, signal: controller.signal });
        if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? "Revisá tu sesión y permisos." : response.status === 402 ? "La licencia no está activa." : "No se pudieron actualizar las alertas.");
        const result: Feed = await response.json();
        if (!Array.isArray(result.sources)) throw new Error("Respuesta de alertas inválida.");
        if (!disposed) setFeed(result);
      } catch (e) {
        if (!disposed) setError(e instanceof Error && e.name !== "AbortError" ? e.message : "La consulta agotó el tiempo de espera.");
      } finally { clearTimeout(timeout); active = null; if (!disposed) setBusy(false); }
    }
    void refresh();
    const timer = setInterval(() => { if (!document.hidden) void refresh(); }, 300000);
    return () => { disposed = true; active?.abort(); clearInterval(timer); };
  }, [token, reload]);

  const features = useMemo(() => (feed?.sources.flatMap(s => s.features) || [])
    .filter(f => (kind === "all" || f.properties.kind === kind) && (!municipality || f.properties.municipality_code === municipality))
    .sort((a,b) => b.properties.observed_at.localeCompare(a.properties.observed_at)), [feed, kind, municipality]);
  useEffect(() => { setPage(0); }, [feed, kind, municipality]);
  useEffect(() => {
    if (!map) return;
    let disposed = false;
    let layer: GeoJSON|undefined;
    void import("leaflet").then(L => {
      if (disposed) return;
      layer = L.geoJSON({ type: "FeatureCollection", features } as FeatureCollection, {
        style: { color: "#ffd166", weight: 2, fillOpacity: .25 },
        pointToLayer: (_feature, latlng) => L.circleMarker(latlng, { radius: 7, color: "#ff6b55", fillOpacity: .8 }),
        onEachFeature: (feature, item) => {
          const p = feature.properties as AlertProperties;
          const text = document.createElement("span");
          text.textContent = p.title + " · " + p.municipality + " · " + p.observed_at + " · " + p.source;
          item.bindPopup(text);
        },
      }).addTo(map);
    });
    return () => { disposed = true; layer?.remove(); };
  }, [map, features]);

  async function focus(feature: AlertFeature) {
    if (!map) return;
    const L = await import("leaflet");
    map.fitBounds(L.geoJSON(feature).getBounds(), { padding: [35, 35], maxZoom: 12 });
    document.getElementById("mato-grosso-map")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return <article className="agro-card" aria-label="Alertas de Mato Grosso">
    <h3>Alertas satelitales</h3>
    <p>Focos de calor: últimos 2 días. Deforestación: observaciones de los últimos 30 días en las capas DETER de Amazonia y Cerrado. No se garantiza cobertura del Pantanal.</p>
    <div className="workspace-map-tools"><label>Tipo de alerta <select value={kind} onChange={e => setKind(e.target.value)}><option value="all">Todas</option><option value="fire">Focos de calor</option><option value="deforestation">Deforestación</option></select></label><button disabled={busy || IS_DEMO || !token} onClick={() => setReload(n => n + 1)}>{busy ? "Actualizando…" : "Actualizar alertas"}</button></div>
    <p>Rojo: foco de calor · Amarillo: polígono de deforestación. {municipality ? "Filtro del municipio seleccionado." : "Vista de todo Mato Grosso."}</p>
    {error && <p role="alert">{error} {feed ? "Se conserva la última consulta; los datos pueden estar desactualizados." : ""}</p>}
    {busy && <p role="status">Consultando las fuentes satelitales…</p>}
    {feed && <>
      <p>Última consulta: {new Date(feed.queried_at).toLocaleString("es-AR", { timeZone: "America/Cuiaba" })} (Cuiabá). Actualización cada 5 minutos con esta sección abierta; caché de hasta 5 minutos.</p>
      <ul>{feed.sources.map(s => <li key={s.source}><strong>{s.source}: {statusLabels[s.status]}</strong>. {s.message}</li>)}</ul>
      <p role="status">{features.length} avisos en la selección. {feed.sources.some(s => s.status !== "ok") ? "Hay fuentes incompletas o no disponibles; el conteo no representa todas las alertas." : ""}</p>
      {!features.length && <p>No hay avisos en los resultados disponibles para este filtro. Esto no garantiza ausencia de incendios o deforestación.</p>}
      {!!features.length && <div className="agro-series-table"><table><caption>Avisos por verificar · fecha de observación del proveedor</caption><thead><tr><th>Tipo</th><th>Municipio</th><th>Fecha</th><th>Fuente / estado</th><th>Ubicación</th></tr></thead><tbody>{features.slice(page * 25, page * 25 + 25).map(f => <tr key={f.properties.id}><td>{f.properties.title}</td><td>{f.properties.municipality}</td><td>{f.properties.observed_at.replace("T", " ").replace("+00:00", " UTC")}</td><td>{f.properties.source}<br/>{f.properties.status}{f.properties.confidence && <><br/>Confianza del proveedor: {f.properties.confidence}</>}</td><td><button disabled={!map} onClick={() => void focus(f)}>Ver en mapa</button></td></tr>)}</tbody></table></div>}
      {features.length > 25 && <div className="workspace-map-tools"><button disabled={page === 0} onClick={() => setPage(p => p - 1)}>Anterior</button><span>Página {page + 1} de {Math.ceil(features.length / 25)}</span><button disabled={(page + 1) * 25 >= features.length} onClick={() => setPage(p => p + 1)}>Siguiente</button></div>}
    </>}
    <p>Un foco de calor no confirma un incendio. DETER es un aviso satelital y no determina por sí solo ilegalidad ni sustituye una verificación en campo. Las alertas aparecen en esta pantalla; no se envían correos ni notificaciones externas.</p>
    <p>Fuentes: <a href="https://firms.modaps.eosdis.nasa.gov/">NASA FIRMS</a> · <a href="https://terrabrasilis.dpi.inpe.br/">INPE TerraBrasilis</a>.</p>
  </article>;
}
