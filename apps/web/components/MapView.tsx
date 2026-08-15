"use client";
import { useEffect, useRef } from "react";
import type { Alert, Detection, Device, Report } from "../app/lib/types";

// Capa de abstraccion de mapa. Default Leaflet; lista para Mapbox via
// NEXT_PUBLIC_MAP_PROVIDER=mapbox (+ token). El MVP usa tiles OSM.
interface Props {
  devices: Device[];
  alerts: Alert[];
  detections: Detection[];
  reports: Report[];
  center: [number, number];
  onAlert?: (id: string) => void;
}

const SEV_COLOR: Record<string, string> = { critica: "#DC2626", alta: "#D97706", media: "#84cc16", baja: "#64748b" };

export default function MapView({ devices, alerts, detections, reports, center, onAlert }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const layerRef = useRef<any>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = (await import("leaflet")).default;
      if (cancelled || !ref.current) return;
      if (!mapRef.current) {
        mapRef.current = L.map(ref.current, { zoomControl: true, attributionControl: false }).setView(center, 12);
        L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(mapRef.current);
        layerRef.current = L.layerGroup().addTo(mapRef.current);
      }
      const layer = layerRef.current;
      layer.clearLayers();

      devices.forEach((d) => {
        const color = d.status === "online" ? "#2E7D5B" : d.status === "alerta" ? "#DC2626" : "#5b6b62";
        L.circleMarker([d.lat, d.lon], { radius: 5, color, fillColor: color, fillOpacity: 0.9, weight: 1 })
          .bindPopup(`<b>${d.name}</b><br/>${d.status} · bat ${d.battery ?? "?"}%`).addTo(layer);
      });
      detections.forEach((s) =>
        L.circleMarker([s.lat, s.lon], { radius: 7, color: "#f97316", fillColor: "#f97316", fillOpacity: 0.5, weight: 1 })
          .bindPopup(`🔥 Satelite ${s.source}<br/>conf ${Math.round((s.confidence ?? 0) * 100)}%`).addTo(layer)
      );
      reports.forEach((r) =>
        L.marker([r.lat, r.lon]).bindPopup(`👤 Reporte: ${r.type}`).addTo(layer)
      );
      alerts.forEach((a) => {
        const c = SEV_COLOR[a.severity] || "#DC2626";
        L.circleMarker([a.lat, a.lon], { radius: 12, color: c, fillColor: c, fillOpacity: 0.25, weight: 2 })
          .on("click", () => onAlert?.(a.id))
          .bindPopup(`<b>${a.title}</b><br/>${a.severity} · conf ${Math.round(a.confidence * 100)}%`).addTo(layer);
      });
    })();
    return () => { cancelled = true; };
  }, [devices, alerts, detections, reports, center, onAlert]);

  return <div id="map" ref={ref} />;
}
