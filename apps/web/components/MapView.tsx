"use client";

import { useEffect, useRef, useState } from "react";
import type { LayerGroup, Map as LeafletMap, TileLayer, WMSOptions } from "leaflet";
import type { EarthIntel } from "../app/lib/earth-intel";
import type {
  Alert,
  Detection,
  Device,
  EnvironmentalSourceSettings,
  Report,
  RiskZone,
} from "../app/lib/types";
import {
  MISIONES_BOUNDS,
  MISIONES_CENTER,
  MISIONES_POLYGON,
  isInMisiones,
} from "../app/lib/misiones";

interface Props {
  devices: Device[];
  alerts: Alert[];
  detections: Detection[];
  reports: Report[];
  zones?: RiskZone[];
  center: [number, number];
  earth?: EarthIntel | null;
  onAlert?: (id: string) => void;
  initialSatelliteMode?: SatelliteMode;
  sourceSettings?: EnvironmentalSourceSettings | null;
  showForestryAssets?: boolean;
}

type BaseMap = "dark" | "street";
type SatelliteMode = "NONE" | "TRUE_COLOR" | "NDVI" | "MOISTURE_INDEX" | "NBR_RAW";
type SatelliteStatus = "off" | "zoom" | "loading" | "live" | "fallback" | "degraded";
type TerritoryFeature = {
  type: "Feature";
  properties?: { province?: string; official?: boolean; source?: string };
  geometry?: Record<string, unknown>;
};

const COPERNICUS_WMS_ENV = (process.env.NEXT_PUBLIC_COPERNICUS_WMS_URL || "").trim();
const API_URL = (process.env.NEXT_PUBLIC_API_URL || "https://econexo.onrender.com").replace(/\/$/, "");
const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
const SEVERITY_COLOR: Record<string, string> = {
  critica: "#ff5d52",
  alta: "#ff9f45",
  media: "#ffd166",
  baja: "#8ff06a",
};
const ZONE_COLOR: Record<string, string> = {
  incendio: "#ff9f45",
  hidrica: "#33daff",
  general: "#b8a4ff",
};
const SATELLITE_LABEL: Record<SatelliteMode, string> = {
  NONE: "Sin capa",
  TRUE_COLOR: "Color natural",
  NDVI: "Vegetación NDVI",
  MOISTURE_INDEX: "Humedad",
  NBR_RAW: "Área quemada",
};

function dayStamp(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function popupText(value: string): string {
  return value.replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", "\"": "&quot;",
  })[char] || char);
}

function devicePopup(device: Device): string {
  const values = Object.entries(device.latest_readings || {})
    .slice(0, 5)
    .map(([key, value]) => `${popupText(key)}: ${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 2 })}`)
    .join("<br>");
  return `<b>${popupText(device.name)}</b><br>${popupText(device.status)} · ${popupText(device.telemetry_mode)}${device.zone_name ? `<br>Zona: ${popupText(device.zone_name)}` : ""}${values ? `<hr>${values}` : ""}`;
}

export default function MapView({
  devices,
  alerts,
  detections,
  reports,
  zones = [],
  center,
  earth,
  onAlert,
  initialSatelliteMode = "NONE",
  sourceSettings,
  showForestryAssets = false,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const baseLayerRef = useRef<TileLayer | null>(null);
  const satelliteLayerRef = useRef<TileLayer.WMS | null>(null);
  const dataLayerRef = useRef<LayerGroup | null>(null);
  const [centerLat, centerLon] = center;
  const [ready, setReady] = useState(false);
  const [baseMap, setBaseMap] = useState<BaseMap>("street");
  const [satelliteMode, setSatelliteMode] = useState<SatelliteMode>(initialSatelliteMode);
  const [satelliteStatus, setSatelliteStatus] = useState<SatelliteStatus>("off");
  const [territoryFeature, setTerritoryFeature] = useState<TerritoryFeature | null>(null);
  const [territoryOfficial, setTerritoryOfficial] = useState(false);
  const runtimeCopernicusWms = sourceSettings?.copernicus_enabled
    ? sourceSettings.copernicus_wms_url
    : null;
  const copernicusWms = (runtimeCopernicusWms || COPERNICUS_WMS_ENV).trim().replace(/\/$/, "");
  const copernicusEnabled = Boolean(copernicusWms);
  const satelliteLayers: Record<Exclude<SatelliteMode, "NONE">, string> = {
    TRUE_COLOR: sourceSettings?.copernicus_true_color_layer || "TRUE_COLOR",
    NDVI: sourceSettings?.copernicus_ndvi_layer || "NDVI",
    MOISTURE_INDEX: sourceSettings?.copernicus_moisture_layer || "MOISTURE_INDEX",
    NBR_RAW: sourceSettings?.copernicus_burn_layer || "NBR_RAW",
  };

  useEffect(() => {
    if (DEMO_MODE || !API_URL) return;
    let active = true;
    fetch(`${API_URL}/territory/geojson`, { cache: "no-store" })
      .then((response) => response.ok ? response.json() : Promise.reject(response.status))
      .then((feature) => {
        if (!active || feature?.properties?.province !== "Misiones") return;
        setTerritoryFeature(feature);
        setTerritoryOfficial(Boolean(feature?.properties?.official));
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let disposed = false;
    void import("leaflet").then(({ default: L }) => {
      if (disposed || !containerRef.current || mapRef.current) return;
      const safeCenter: [number, number] = isInMisiones(centerLat, centerLon)
        ? [centerLat, centerLon]
        : MISIONES_CENTER;
      const map = L.map(containerRef.current, {
        zoomControl: true,
        attributionControl: true,
        preferCanvas: true,
        minZoom: 7,
        maxBounds: L.latLngBounds(MISIONES_BOUNDS),
        maxBoundsViscosity: 0.92,
      }).setView(safeCenter, 8);
      L.control.scale({ imperial: false, metric: true, position: "bottomright" }).addTo(map);
      mapRef.current = map;
      dataLayerRef.current = L.layerGroup().addTo(map);
      setReady(true);
    });
    return () => {
      disposed = true;
      mapRef.current?.remove();
      mapRef.current = null;
      baseLayerRef.current = null;
      satelliteLayerRef.current = null;
      dataLayerRef.current = null;
    };
  }, [centerLat, centerLon]);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    let cancelled = false;
    void import("leaflet").then(({ default: L }) => {
      const map = mapRef.current;
      if (cancelled || !map) return;
      if (baseLayerRef.current) map.removeLayer(baseLayerRef.current);
      let tileErrors = 0;
      const layer = baseMap === "dark"
        ? L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
          maxZoom: 20,
          maxNativeZoom: 19,
          subdomains: "abcd",
          updateWhenIdle: true,
          keepBuffer: 4,
          attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
        })
        : L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          maxNativeZoom: 19,
          updateWhenIdle: true,
          keepBuffer: 4,
          attribution: "&copy; OpenStreetMap contributors",
        });
      layer.on("tileerror", () => {
        tileErrors += 1;
        if (baseMap === "dark" && tileErrors >= 3) setBaseMap("street");
      });
      baseLayerRef.current = layer.addTo(map);
      layer.bringToBack();
    });
    return () => { cancelled = true; };
  }, [baseMap, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    let cancelled = false;
    let activeLayer: TileLayer.WMS | null = null;
    const removeActive = () => {
      if (activeLayer && map.hasLayer(activeLayer)) map.removeLayer(activeLayer);
      if (satelliteLayerRef.current === activeLayer) satelliteLayerRef.current = null;
    };

    if (satelliteLayerRef.current) map.removeLayer(satelliteLayerRef.current);
    satelliteLayerRef.current = null;
    if (satelliteMode === "NONE") {
      setSatelliteStatus("off");
      return;
    }
    if (!copernicusEnabled || !copernicusWms) {
      setSatelliteStatus(
        satelliteMode === "MOISTURE_INDEX" || satelliteMode === "NBR_RAW"
          ? "fallback"
          : "degraded",
      );
      return;
    }

    const syncZoomStatus = () => {
      if (map.getZoom() < 9) setSatelliteStatus("zoom");
      else setSatelliteStatus((current) => current === "zoom" ? "loading" : current);
    };
    syncZoomStatus();
    map.on("zoomend", syncZoomStatus);

    void import("leaflet").then(({ default: L }) => {
      if (cancelled) return;
      const start = new Date();
      start.setUTCFullYear(start.getUTCFullYear() - 1);
      const options: WMSOptions & { time: string; maxcc: number } = {
        layers: satelliteLayers[satelliteMode],
        format: "image/png",
        transparent: true,
        version: "1.1.1",
        minZoom: 9,
        maxZoom: 18,
        opacity: satelliteMode === "TRUE_COLOR" ? 0.76 : 0.68,
        attribution: "Copernicus Data Space Ecosystem · Sentinel Hub · ESA",
        time: `${dayStamp(start)}/${dayStamp(new Date())}`,
        maxcc: 80,
      };
      let tileErrors = 0;
      const layer = L.tileLayer.wms(copernicusWms, options);
      activeLayer = layer;
      layer.on("loading", () => setSatelliteStatus(map.getZoom() < 9 ? "zoom" : "loading"));
      layer.on("load", () => {
        tileErrors = 0;
        setSatelliteStatus(map.getZoom() < 9 ? "zoom" : "live");
      });
      layer.on("tileerror", () => {
        tileErrors += 1;
        setSatelliteStatus("degraded");
        if (tileErrors >= 4 && map.hasLayer(layer)) map.removeLayer(layer);
      });
      satelliteLayerRef.current = layer.addTo(map);
    });

    return () => {
      cancelled = true;
      map.off("zoomend", syncZoomStatus);
      removeActive();
    };
  }, [
    copernicusEnabled,
    copernicusWms,
    ready,
    satelliteLayers.NBR_RAW,
    satelliteLayers.MOISTURE_INDEX,
    satelliteLayers.NDVI,
    satelliteLayers.TRUE_COLOR,
    satelliteMode,
  ]);

  useEffect(() => {
    const layer = dataLayerRef.current;
    if (!ready || !layer) return;
    let cancelled = false;
    void import("leaflet").then(({ default: L }) => {
      if (cancelled) return;
      layer.clearLayers();
      const territoryStyle = {
        color: "#35e6df",
        weight: 2,
        opacity: 0.8,
        fillColor: "#35e6df",
        fillOpacity: 0.025,
        dashArray: territoryOfficial ? undefined : "8 7",
        interactive: false,
      };
      if (territoryFeature) {
        L.geoJSON(
          territoryFeature as unknown as Parameters<typeof L.geoJSON>[0],
          { style: territoryStyle },
        ).addTo(layer);
      } else {
        L.polygon(MISIONES_POLYGON, territoryStyle).addTo(layer);
      }

      zones.filter((item) => isInMisiones(item.lat, item.lon)).forEach((zone) => {
        const color = ZONE_COLOR[zone.kind] || ZONE_COLOR.general;
        L.circle([zone.lat, zone.lon], {
          radius: zone.radius_m,
          color,
          weight: 2,
          opacity: 0.9,
          fillColor: color,
          fillOpacity: satelliteMode === "NDVI" ? 0.14 : 0.06,
          dashArray: "7 6",
        }).bindPopup(
          `<b>${popupText(zone.name)}</b><br>Zona ${popupText(zone.kind)} · ${(zone.radius_m / 1000).toLocaleString("es-AR", { maximumFractionDigits: 1 })} km`,
        ).addTo(layer);
      });

      if (showForestryAssets) {
        const sanAntonio: [number, number] = [-26.01709, -53.78987];
        const bernardoRadar: [number, number] = [-26.2552, -53.6478];
        L.circleMarker(sanAntonio, { radius: 9, color: "#86f56a", fillColor: "#86f56a", fillOpacity: 0.8, weight: 2 })
          .bindPopup("<b>San Antonio · vigilancia forestal</b><br>Área prioritaria para recorridas, trampas, reportes y verificación fitosanitaria.")
          .addTo(layer);
        L.circleMarker(bernardoRadar, { radius: 10, color: "#6dd7ff", fillColor: "#0d3340", fillOpacity: 0.9, weight: 2 })
          .bindPopup("<b>Referencia municipal · radar de Bernardo de Irigoyen</b><br>Contexto meteorológico regional; no identifica especies de plagas.")
          .addTo(layer);
        L.polyline([sanAntonio, bernardoRadar], { color: "#6dd7ff", weight: 2, opacity: 0.72, dashArray: "6 7" })
          .bindTooltip("Corredor de contexto meteorológico · aproximadamente 27 km")
          .addTo(layer);
      }

      if (satelliteMode === "MOISTURE_INDEX" && !copernicusEnabled) {
        let moistureSignals = 0;
        devices.forEach((device) => {
          const humidity = device.latest_readings?.soil_moisture ?? device.latest_readings?.humidity;
          if (humidity == null) return;
          const normalized = Math.max(0, Math.min(100, Number(humidity)));
          moistureSignals += 1;
          L.circle([device.lat, device.lon], {
            radius: 3000,
            color: "#33daff",
            weight: 1,
            fillColor: "#33daff",
            fillOpacity: 0.05 + normalized / 500,
          }).bindTooltip(`Proxy telemétrico de humedad: ${normalized.toFixed(1)}%`).addTo(layer);
        });
        if (!moistureSignals) {
          const raw = earth?.weather.soilMoisture ?? earth?.weather.humidity;
          if (raw != null) {
            const asPercent = raw <= 1 ? raw * 100 : raw;
            const normalized = Math.max(0, Math.min(100, Number(asPercent)));
            L.circle([centerLat, centerLon], {
              radius: 9000,
              color: "#33daff",
              weight: 1,
              fillColor: "#33daff",
              fillOpacity: 0.05 + normalized / 500,
              dashArray: "5 6",
            }).bindTooltip(`Contexto Open-Meteo de humedad: ${normalized.toFixed(1)}%`).addTo(layer);
          }
        }
      }

      if (satelliteMode === "NBR_RAW" && !copernicusEnabled) {
        const fireSignals = detections.length
          ? detections.map((item) => ({ lat: item.lat, lon: item.lon, label: "Proxy FIRMS de foco térmico" }))
          : alerts
              .filter((item) => item.type === "incendio")
              .map((item) => ({ lat: item.lat, lon: item.lon, label: "Alerta operativa de incendio" }));
        fireSignals.forEach((signal) => {
          L.circle([signal.lat, signal.lon], {
            radius: 4500,
            color: "#ff5d52",
            weight: 2,
            fillColor: "#ff9f45",
            fillOpacity: 0.12,
            dashArray: "4 5",
          }).bindTooltip(`${signal.label}; no representa perímetro quemado confirmado`).addTo(layer);
        });
      }

      devices.filter((item) => isInMisiones(item.lat, item.lon)).forEach((device) => {
        const color = device.status === "online"
          ? "#8ff06a"
          : device.status === "alerta"
            ? "#ff5d52"
            : "#6f8581";
        const shape = device.marker_shape || "circle";
        const icon = L.divIcon({
          className: "econexo-device-icon",
          html: `<span class="device-marker-shape ${shape}" style="--device-color:${color}"></span>`,
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        });
        L.marker([device.lat, device.lon], { icon })
          .bindPopup(devicePopup(device))
          .addTo(layer);
      });

      detections.filter((item) => isInMisiones(item.lat, item.lon)).forEach((detection) => {
        L.circleMarker([detection.lat, detection.lon], {
          radius: 8,
          color: "#ff9f45",
          fillColor: "#ff9f45",
          fillOpacity: 0.38,
          weight: 2,
        }).bindPopup(
          `<b>Detección satelital</b><br>${popupText(detection.source)} · confianza ${Math.round((detection.confidence ?? 0) * 100)}%`,
        ).addTo(layer);
      });

      reports.filter((item) => isInMisiones(item.lat, item.lon)).forEach((report) => {
        L.circleMarker([report.lat, report.lon], {
          radius: 6,
          color: "#33daff",
          fillColor: "#33daff",
          fillOpacity: 0.7,
          weight: 2,
        }).bindPopup(`<b>Reporte ciudadano</b><br>${popupText(report.type)}`).addTo(layer);
      });

      alerts.filter((item) => isInMisiones(item.lat, item.lon)).forEach((alert) => {
        const color = SEVERITY_COLOR[alert.severity] || "#ff5d52";
        L.circleMarker([alert.lat, alert.lon], {
          radius: 13,
          color,
          fillColor: color,
          fillOpacity: 0.2,
          weight: 2,
        }).on("click", () => onAlert?.(alert.id))
          .bindPopup(
            `<b>${popupText(alert.title)}</b><br>${popupText(alert.severity)} · confianza ${Math.round(alert.confidence * 100)}%`,
          )
          .addTo(layer);
      });
    });
    return () => { cancelled = true; };
  }, [
    alerts,
    copernicusEnabled,
    detections,
    devices,
    earth,
    centerLat,
    centerLon,
    onAlert,
    ready,
    reports,
    satelliteMode,
    showForestryAssets,
    territoryFeature,
    territoryOfficial,
    zones,
  ]);

  const localSignals = [
    ...devices.map((item) => ({ lat: item.lat, lon: item.lon })),
    ...alerts.map((item) => ({ lat: item.lat, lon: item.lon })),
    ...detections.map((item) => ({ lat: item.lat, lon: item.lon })),
    ...reports.map((item) => ({ lat: item.lat, lon: item.lon })),
  ];
  const outsideSignals = localSignals.filter((item) => !isInMisiones(item.lat, item.lon)).length;
  const insideSignals = localSignals.length - outsideSignals;

  const statusText: Record<SatelliteStatus, string> = {
    off: "capa desactivada",
    zoom: "acercá el mapa para cargar",
    loading: "sincronizando mosaico",
    live: "mosaico Copernicus disponible",
    fallback: satelliteMode === "MOISTURE_INDEX"
      ? "proxy de telemetría; configure Copernicus para índice satelital"
      : "proxy FIRMS; no es un perímetro quemado confirmado",
    degraded: copernicusWms
      ? "instancia o capa no disponible"
      : "requiere instancia Copernicus; la capa permanece seleccionable",
  };

  return (
    <div className="map-component">
      <div id="map" ref={containerRef} />
      <div className="map-toolbar" role="group" aria-label="Capas del mapa">
        <div className="toolbar-title"><span>◫</span> MAPA MISIONES</div>
        <div className="layer-buttons">
          {(Object.keys(SATELLITE_LABEL) as SatelliteMode[]).map((mode) => (
            <button
              key={mode}
              title={mode !== "NONE" && !copernicusEnabled
                ? "Se muestra un fallback operativo cuando existe; configure Copernicus en Admin Core para el mosaico satelital."
                : undefined}
              className={satelliteMode === mode ? "active" : ""}
              onClick={() => setSatelliteMode(mode)}
            >
              {SATELLITE_LABEL[mode]}
            </button>
          ))}
        </div>
        <label className="base-switch">
          Base
          <select value={baseMap} onChange={(event) => setBaseMap(event.target.value as BaseMap)}>
            <option value="dark">Control oscuro</option>
            <option value="street">OpenStreetMap</option>
          </select>
        </label>
      </div>
      <div className={`satellite-status ${satelliteStatus}`}>
        <span className="dot" />
        <span>
          <b>{satelliteMode === "NONE" ? "CAPAS" : SATELLITE_LABEL[satelliteMode]}</b>
          <small>{statusText[satelliteStatus]}</small>
        </span>
      </div>
      {earth && (
        <div className="map-atmosphere-hud">
          <span className="wind-arrow" style={{ transform: `rotate(${earth.weather.windDirection ?? 0}deg)` }}>↑</span>
          <span><b>{earth.weather.windSpeed?.toFixed(0) ?? "—"} km/h</b><small>viento · cobertura {earth.weather.cloudCover?.toFixed(0) ?? "—"}%</small></span>
        </div>
      )}
      <div className="map-territory-hud">
        <strong>MISIONES · 79 MUNICIPIOS</strong>
        <span>{insideSignals} señales · {zones.length} zonas · {territoryOfficial ? "límite oficial GeoRef" : "límite operativo"}</span>
        {outsideSignals > 0 && <small>{outsideSignals} señales regionales ocultas</small>}
      </div>
      <div className="map-scan" aria-hidden="true" />
    </div>
  );
}
