"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchEarthIntel, type EarthIntel } from "../app/lib/earth-intel";
import { isInMisiones, misionesLocationLabel } from "../app/lib/misiones";

interface Props {
  lat: number;
  lon: number;
  onUpdate?: (value: EarthIntel | null) => void;
}

function fmt(value: number | null, unit = "", digits = 0): string {
  return value == null ? "—" : `${value.toFixed(digits)}${unit}`;
}

function weatherLabel(code: number | null): string {
  if (code == null) return "Sin lectura";
  if (code === 0) return "Despejado";
  if (code <= 3) return "Nubosidad variable";
  if (code <= 48) return "Niebla";
  if (code <= 57) return "Llovizna";
  if (code <= 67) return "Lluvia";
  if (code <= 77) return "Nieve";
  if (code <= 82) return "Chubascos";
  if (code <= 86) return "Nieve intensa";
  return "Tormenta";
}

function cardinal(degrees: number | null): string {
  if (degrees == null) return "—";
  const points = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"];
  return points[Math.round(degrees / 45) % 8];
}

function Sparkline({ values, color }: { values: Array<number | null>; color: string }) {
  const samples = values.map((value, index) => ({ value, index })).filter((item): item is { value: number; index: number } => item.value != null);
  if (samples.length < 2) return <span className="spark-empty">sin serie</span>;
  const min = Math.min(...samples.map((item) => item.value));
  const max = Math.max(...samples.map((item) => item.value));
  const range = Math.max(max - min, 0.001);
  const width = 92;
  const height = 25;
  const path = samples.map((item, order) => {
    const x = samples.length === 1 ? 0 : (order / (samples.length - 1)) * width;
    const y = height - 3 - ((item.value - min) / range) * (height - 6);
    return `${order ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <svg className="spark" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d={`${path} L${width},${height} L0,${height} Z`} fill={color} opacity=".08" />
    </svg>
  );
}

export default function EarthIntelBar({ lat, lon, onUpdate }: Props) {
  const [intel, setIntel] = useState<EarthIntel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  const load = useCallback(async (force = false, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      if (!isInMisiones(lat, lon)) {
        throw new Error("Coordenadas fuera del territorio operativo de Misiones");
      }
      const value = await fetchEarthIntel(lat, lon, signal, force);
      setIntel(value);
      onUpdate?.(value);
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setError("Fuentes externas no disponibles");
      onUpdate?.(null);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [lat, lon, onUpdate]);

  useEffect(() => {
    const controller = new AbortController();
    void load(false, controller.signal);
    const interval = window.setInterval(() => void load(true), 15 * 60_000);
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, [load]);

  if (!intel && loading) {
    return (
      <section className="earthbar earth-loading" aria-label="Cargando inteligencia terrestre">
        <div className="earth-source"><span className="orbit-glyph">◉</span><span><strong>INTELIGENCIA TERRESTRE</strong><small>sincronizando Open‑Meteo + CAMS</small></span></div>
        {[0, 1, 2, 3, 4].map((item) => <span className="earth-skeleton" key={item} />)}
      </section>
    );
  }

  return (
    <section className={`earthbar${collapsed ? " earthbar-collapsed" : ""}`} aria-label="Condiciones meteorológicas y atmosféricas">
      <div className="earth-source">
        <button
          className="earth-collapse"
          onClick={() => setCollapsed((value) => !value)}
          aria-expanded={!collapsed}
          title={collapsed ? "Expandir inteligencia terrestre" : "Contraer inteligencia terrestre"}
          aria-label={collapsed ? "Expandir inteligencia terrestre" : "Contraer inteligencia terrestre"}
        >
          {collapsed ? "▸" : "▾"}
        </button>
        <span className="orbit-glyph">◉</span>
        <span>
          <strong>INTELIGENCIA TERRESTRE</strong>
          <small>
            {collapsed
              ? `${fmt(intel?.weather.temperature ?? null, "°", 1)} · ${weatherLabel(intel?.weather.weatherCode ?? null)}`
              : `${misionesLocationLabel(lat, lon)} · Open‑Meteo/CAMS`}
          </small>
        </span>
        <span className={`source-state ${error ? "offline" : intel?.stale ? "stale" : "live"}`}>
          {error ? "sin enlace" : intel?.stale ? "caché" : "en vivo"}
        </span>
      </div>

      <div className="earth-metric">
        <span>Tiempo</span>
        <strong>{fmt(intel?.weather.temperature ?? null, "°", 1)}</strong>
        <small>{weatherLabel(intel?.weather.weatherCode ?? null)} · ST {fmt(intel?.weather.apparentTemperature ?? null, "°")}</small>
        <Sparkline values={intel?.series.temperature ?? []} color="#8ff06a" />
      </div>
      <div className="earth-metric">
        <span>Humedad</span>
        <strong>{fmt(intel?.weather.humidity ?? null, "%")}</strong>
        <small>suelo {fmt((intel?.weather.soilMoisture ?? 0) * 100, "%")}</small>
        <Sparkline values={intel?.series.humidity ?? []} color="#33daff" />
      </div>
      <div className="earth-metric">
        <span>Viento 10 m</span>
        <strong>{fmt(intel?.weather.windSpeed ?? null, " km/h")}</strong>
        <small>{cardinal(intel?.weather.windDirection ?? null)} · ráfaga {fmt(intel?.weather.windGusts ?? null, " km/h")}</small>
        <Sparkline values={intel?.series.windSpeed ?? []} color="#ffd166" />
      </div>
      <div className="earth-metric">
        <span>PM2.5 · CAMS</span>
        <strong>{fmt(intel?.atmosphere.pm25 ?? null, " µg/m³", 1)}</strong>
        <small>PM10 {fmt(intel?.atmosphere.pm10 ?? null, " µg/m³", 1)}</small>
        <Sparkline values={intel?.series.pm25 ?? []} color="#ff9f45" />
      </div>
      <div className="earth-metric">
        <span>Aerosoles</span>
        <strong>{fmt(intel?.atmosphere.aerosolOpticalDepth ?? null, "", 2)}</strong>
        <small>polvo {fmt(intel?.atmosphere.dust ?? null, " µg/m³", 1)}</small>
        <Sparkline values={intel?.series.aerosolOpticalDepth ?? []} color="#a78bff" />
      </div>

      <button className="earth-refresh" onClick={() => void load(true)} disabled={loading} title="Actualizar fuentes externas" aria-label="Actualizar fuentes externas">
        {loading ? "···" : "↻"}
      </button>
    </section>
  );
}
