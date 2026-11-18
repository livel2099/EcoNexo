"use client";
import { useBrazilLanguage } from "./BrazilLanguage";
import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap, TileLayer } from "leaflet";

type Catalog = { latest: string; ranges: string[] };
let catalogPromise: Promise<Catalog>|null = null;
const GIBS = "https://gibs.earthdata.nasa.gov";
const LAYER = "MODIS_Terra_NDVI_8Day";
function catalog() {
  if (!catalogPromise) catalogPromise = (async () => {
    const response = await fetch(GIBS + "/wmts/epsg3857/best/wmts.cgi?SERVICE=WMTS&REQUEST=GetCapabilities", { signal: AbortSignal.timeout(20000) });
    if (!response.ok) throw Error("No se pudo consultar el catálogo NDVI de NASA.");
    const xml = new DOMParser().parseFromString(await response.text(), "text/xml");
    const layer = Array.from(xml.getElementsByTagNameNS("*", "Layer")).find(node =>
      Array.from(node.children).some(c => c.localName === "Identifier" && c.textContent === LAYER));
    const dimension = layer?.getElementsByTagNameNS("*", "Dimension")[0];
    const latest = dimension?.getElementsByTagNameNS("*", "Default")[0]?.textContent || "";
    const ranges = Array.from(dimension?.getElementsByTagNameNS("*", "Value") || []).map(n => n.textContent || "");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(latest) || !ranges.length) throw Error("NASA no informó fechas válidas para NDVI.");
    return { latest, ranges };
  })().catch(error => { catalogPromise = null; throw error; });
  return catalogPromise;
}

export default function BrazilNdviLayer({ map }: { map: LeafletMap|null }) {
 const { t } = useBrazilLanguage();

  const [enabled, setEnabled] = useState(false);
  const [metadata, setMetadata] = useState<Catalog|null>(null);
  const [date, setDate] = useState("");
  const [opacity, setOpacity] = useState(.8);
  const [status, setStatus] = useState("");
  const [retry, setRetry] = useState(0);
  const opacityRef = useRef(opacity); opacityRef.current = opacity;
  const active = useRef<TileLayer|null>(null);
  useEffect(() => {
    if (!enabled) return;
    let disposed = false;
    setStatus("Consultando fechas disponibles de NASA…");
    void catalog().then(value => {
      if (disposed) return;
      setMetadata(value); setDate(d => d || value.latest);
    }).catch(error => { if (!disposed) setStatus(error.message); });
    return () => { disposed = true; };
  }, [enabled, retry]);
  useEffect(() => {
    if (!enabled || !metadata || !date || !map) return;
    if (!metadata.ranges.some(range => {
      const [start, end] = range.split("/");
      return date >= start && date <= (end || start);
    })) { setStatus("No hay una fecha publicada para esta selección. Elegí otra fecha."); return; }
    let disposed = false;
    let layer: TileLayer|undefined;
    let failed = false;
    setStatus("Cargando vegetación NDVI…");
    void import("leaflet").then(L => {
      if (disposed) return;
      layer = L.tileLayer(GIBS + "/wmts/epsg3857/best/" + LAYER + "/default/" + date + "/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png", {
        tileSize: 256, maxNativeZoom: 9, maxZoom: 18, opacity: opacityRef.current,
        bounds: [[-18.1, -61], [-7.2, -50]], noWrap: true, zIndex: 250,
        attribution: "NASA GIBS · MODIS Terra NDVI",
      });
      active.current = layer;
      layer.on("loading", () => { failed = false; setStatus("Cargando vegetación NDVI…"); });
      layer.on("tileerror", () => { failed = true; setStatus("Parte de la imagen NDVI no pudo cargarse. Reintentá o cambiá la fecha."); });
      layer.on("load", () => { if (!failed) setStatus("NDVI cargado. Las áreas transparentes pueden no tener observaciones válidas."); });
      layer.addTo(map);
    });
    return () => { disposed = true; layer?.remove(); if (active.current === layer) active.current = null; };
  }, [enabled, metadata, date, map, retry]);
  useEffect(() => { active.current?.setOpacity(opacity); }, [opacity, enabled, date, metadata, retry]);
  return <div className="workspace-technical" style={{ padding: 16, marginBottom: 16 }}>
    <div className="workspace-map-tools">
      <label><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)}/> {t("Vegetación NDVI · NASA")}</label>
      {enabled && <><label>{t("Fecha de composición ")}<input type="date" value={date} min={metadata?.ranges[0]?.split("/")[0]} max={metadata?.latest} onChange={e => setDate(e.target.value)}/></label>
      <label>{t("Opacidad ")}<input type="range" min="0.2" max="1" step="0.1" value={opacity} onChange={e => setOpacity(Number(e.target.value))}/></label>
      <button onClick={() => { catalogPromise = null; setRetry(n => n + 1); }}>{t("Reintentar NDVI")}</button></>}
    </div>
    {enabled && <><p role="status">{t(status)}</p><p>{t("MODIS Terra · composición móvil de 8 días · resolución nominal de 250 m. Última fecha publicada: ")}{metadata?.latest || t("consultando")}{t(". Cobertura regional: puede incluir zonas vecinas a Mato Grosso. Al acercar el mapa se amplían los píxeles; no aumenta el detalle.")}</p>
      <img src={GIBS + "/legends/MODIS_NDVI_H.svg"} alt={t("Escala oficial del índice NDVI de NASA")} style={{ maxWidth: "100%", background: "white", padding: 8 }}/>
      <p>{t("NDVI representa vegetación, no exclusivamente soja; no mide rendimiento ni diagnostica plagas. Transparencia no significa ausencia de vegetación. Para el detalle del lote, usá Sentinel-2 en Satélite.")}</p></>}
  </div>;
}
