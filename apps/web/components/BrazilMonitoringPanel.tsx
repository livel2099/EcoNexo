"use client";
import { useBrazilLanguage } from "./BrazilLanguage";
import { useEffect, useRef, useState } from "react";
import type { GeoJSON, Map as LeafletMap, CircleMarker } from "leaflet";
import BrazilAlerts from "./BrazilAlerts";
import BrazilNdviLayer from "./BrazilNdviLayer";
import type { FeatureCollection } from "geojson";

type Point = { lat: number; lon: number; name: string };
type Daily = { time: string[]; temperature_2m_max: (number|null)[]; temperature_2m_min: (number|null)[]; precipitation_sum: (number|null)[] };
export default function BrazilMonitoringPanel({ token }: { token: string }) {
 const { t, locale } = useBrazilLanguage();

  const container = useRef<HTMLDivElement>(null);
  const map = useRef<LeafletMap|null>(null);
  const boundary = useRef<GeoJSON|null>(null);
  const marker = useRef<CircleMarker|null>(null);
  const [alertKind, setAlertKind] = useState("all");
  const [geo, setGeo] = useState<FeatureCollection|null>(null);
  const [mapError, setMapError] = useState("");
  const [point, setPoint] = useState<Point|null>(null);
  const [municipality, setMunicipality] = useState("");
  const [daily, setDaily] = useState<Daily|null>(null);
  const [weatherError, setWeatherError] = useState("");
  const [busy, setBusy] = useState(false);
  const [updated, setUpdated] = useState("");
  const [reload, setReload] = useState(0);
  const [mapReload, setMapReload] = useState(0);

  useEffect(() => {
    let disposed = false;
    const controller = new AbortController();
    let observer: ResizeObserver|undefined;
    setMapError("");
    void (async () => {
      try {
        const L = await import("leaflet");
        if (disposed || !container.current) return;
        const m = L.map(container.current).setView([-13, -55.5], 6);
        map.current = m;
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap contributors", maxZoom: 18 }).addTo(m);
        observer = new ResizeObserver(() => m.invalidateSize());
        observer.observe(container.current);
        const response = await fetch("/mato-grosso.geojson", { signal: controller.signal });
        if (!response.ok) throw new Error("Cartografía no disponible.");
        const data: FeatureCollection = await response.json();
        if (disposed) return;
        const layer = L.geoJSON(data, {
          style: { color: "#8ff06a", weight: 1, fillOpacity: .08 },
          onEachFeature: (feature, polygon) => {
            const name = String(feature.properties?.name || feature.properties?.codarea);
            const label = document.createElement("span");
            label.textContent = name;
            polygon.bindTooltip(label);
            polygon.on("click", (event: import("leaflet").LeafletMouseEvent) => {
              setMunicipality(String(feature.properties?.codarea));
              setPoint({ lat: event.latlng.lat, lon: event.latlng.lng, name });
            });
          },
        }).addTo(m);
        boundary.current = layer;
        m.fitBounds(layer.getBounds(), { padding: [16, 16] });
        setGeo(data);
      } catch (error) {
        if (!disposed) setMapError(error instanceof Error ? error.message : "No se pudo cargar el mapa.");
      }
    })();
    return () => { disposed = true; controller.abort(); observer?.disconnect(); map.current?.remove(); map.current = null; boundary.current = null; marker.current = null; };
  }, [mapReload]);

  useEffect(() => {
    let disposed = false;
    void import("leaflet").then(L => {
      if (disposed || !map.current) return;
      marker.current?.remove(); marker.current = null;
      if (point) marker.current = L.circleMarker([point.lat, point.lon], { radius: 7, color: "#ffd166" }).addTo(map.current);
    });
    return () => { disposed = true; };
  }, [point, geo]);

  useEffect(() => {
    setDaily(null); setUpdated(""); setWeatherError("");
    if (!point) { setBusy(false); return; }
    const controller = new AbortController();
    let disposed = false;
    setBusy(true);
    const timeout = setTimeout(() => controller.abort(), 20000);
    const query = new URLSearchParams({ latitude: String(point.lat), longitude: String(point.lon), daily: "temperature_2m_max,temperature_2m_min,precipitation_sum", timezone: "America/Cuiaba", forecast_days: "7" });
    void fetch("https://api.open-meteo.com/v1/forecast?" + query, { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error("El proveedor meteorológico no está disponible. Reintentá la consulta.");
        const data = await response.json();
        if (!data.daily?.time?.length) throw new Error("No hay pronóstico para esta ubicación.");
        if (!disposed) { setDaily(data.daily); setUpdated(new Date().toISOString()); }
      })
      .catch(error => { if (!disposed) setWeatherError(error.name === "AbortError" ? "La consulta demoró demasiado. Reintentá." : error.message); })
      .finally(() => { clearTimeout(timeout); if (!disposed) setBusy(false); });
    return () => { disposed = true; controller.abort(); clearTimeout(timeout); };
  }, [point, reload]);

  async function selectMunicipality(code: string) {
    setMunicipality(code); setPoint(null);
    if (!code) { if (boundary.current) map.current?.fitBounds(boundary.current.getBounds()); return; }
    const feature = geo?.features.find(f => String(f.properties?.codarea) === code);
    if (!feature) return;
    const L = await import("leaflet");
    map.current?.fitBounds(L.geoJSON(feature).getBounds(), { padding: [20, 20] });
  }

  return <section className="view agro-console" aria-label="Brasil · Mato Grosso">
    <header className="agro-header"><div><span className="eyebrow">ECONEXO BRASIL</span><h2>{t("Monitoreo de Mato Grosso")}</h2><p>{t("Explorá todo el estado, acercate a un municipio y consultá el clima de un punto del territorio.")}</p></div></header>
    <article className="agro-card">
      <h3>{t("Territorio y municipios")}</h3>
      <div className="workspace-map-tools">
        <label>{t("Área del mapa ")}<select value={municipality} onChange={e => void selectMunicipality(e.target.value)} disabled={!geo}>
          <option value="">{t("Todo Mato Grosso")}</option>
          {geo?.features.slice().sort((a,b) => String(a.properties?.name).localeCompare(String(b.properties?.name), "pt-BR")).map(f => <option key={f.properties?.codarea} value={f.properties?.codarea}>{f.properties?.name || f.properties?.codarea}</option>)}
        </select></label>
        <button onClick={() => void selectMunicipality("")}>{t("Ver todo el estado")}</button>
      </div>
      <BrazilNdviLayer map={geo ? map.current : null}/>
      <div className="workspace-map-tools"><button className={alertKind === "burned" ? "active" : ""} onClick={() => setAlertKind(alertKind === "burned" ? "all" : "burned")}>{alertKind === "burned" ? t("Ver todas las alertas") : t("Ver zonas quemadas")}</button><span>{t("Violeta: cicatrices de quema DETER · observaciones de los últimos 30 días.")}</span></div>
      <div id="mato-grosso-map" ref={container} className="py-soy-map" style={{ height: "min(65vh, 620px)", minHeight: 320 }} role="region" aria-label={t("Mapa de los municipios de Mato Grosso")}/>
      {mapError && <p role="alert">{t(mapError)} <button onClick={() => setMapReload(v => v + 1)}>{t("Reintentar mapa")}</button></p>}
      <p>{t("Tocá un punto dentro de un municipio para consultar su pronóstico. El selector acerca el mapa; la consulta se realiza en el punto que elijas.")}</p>
      <p className="muted">{t("Cartografía simplificada de IBGE: ")}{geo?.features.length ?? "…"} {t("polígonos municipales. El listado de localidades consultado el 17/11/2026 contiene 142 municipios; esta malla tiene 141 divisiones. Límites orientativos, no catastrales. El mapa base no es una imagen satelital.")}</p>
    </article>
    <BrazilAlerts token={token} map={geo ? map.current : null} municipality={municipality} kind={alertKind} onKindChange={setAlertKind} />
    <article className="agro-card">
      <h3>{point ? t("Pronóstico · ") + point.name : t("Pronóstico por ubicación")}</h3>
      {!point && <p>{t("Seleccioná un punto en el mapa para ver temperatura y lluvia previstas para los próximos siete días.")}</p>}
      {point && <><p>{point.lat.toFixed(4)}, {point.lon.toFixed(4)} · America/Cuiaba</p><button disabled={busy} onClick={() => setReload(v => v + 1)}>{busy ? t("Consultando…") : t("Actualizar pronóstico")}</button></>}
      {busy && <p role="status">{t("Consultando Open-Meteo…")}</p>}
      {weatherError && <p role="alert">{t(weatherError)}</p>}
      {daily && <div className="agro-series-table"><table><caption>{t("Datos modelados · consulta ")}{new Date(updated).toLocaleString(locale, { timeZone: "America/Cuiaba" })} {t("(hora de Cuiabá)")}</caption><thead><tr><th>{t("Fecha")}</th><th>{t("Mínima °C")}</th><th>{t("Máxima °C")}</th><th>{t("Lluvia mm")}</th></tr></thead><tbody>{daily.time.map((day,i) => <tr key={day}><td>{day}</td><td>{daily.temperature_2m_min[i] ?? t("Sin datos")}</td><td>{daily.temperature_2m_max[i] ?? t("Sin datos")}</td><td>{daily.precipitation_sum[i] ?? t("Sin datos")}</td></tr>)}</tbody></table></div>}
      <p>{t("El pronóstico representa el punto seleccionado, no un promedio estatal ni una medición de campo. Las alertas satelitales se consultan por separado; no se generan diagnósticos de plagas a partir del pronóstico.")}</p>
      <p>{t("Fuentes: ")}<a href="https://servicodados.ibge.gov.br/api/docs/malhas?versao=3">IBGE</a> · <a href="https://open-meteo.com/">Open-Meteo</a>.</p>
    </article>
  </section>;
}
