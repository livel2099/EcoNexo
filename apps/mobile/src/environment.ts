import type { Detection, EarthNow } from "./types";
import { isInMisiones } from "./territory";

const FORECAST_URL = process.env.EXPO_PUBLIC_OPEN_METEO_FORECAST_URL || "https://api.open-meteo.com/v1/forecast";
const AIR_URL = process.env.EXPO_PUBLIC_OPEN_METEO_AIR_URL || "https://air-quality-api.open-meteo.com/v1/air-quality";

interface OpenMeteoResponse {
  current?: Record<string, unknown>;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function query(params: Record<string, string>): string {
  return Object.entries(params)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join("&");
}

async function json(url: string): Promise<OpenMeteoResponse> {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`La fuente ambiental respondió ${response.status}.`);
  return response.json() as Promise<OpenMeteoResponse>;
}

export async function fetchEarthNow(latitude: number, longitude: number): Promise<EarthNow> {
  if (!isInMisiones(latitude, longitude)) throw new Error("El contexto ambiental de este lanzamiento se limita a Misiones.");
  const forecast = `${FORECAST_URL}?${query({
    latitude: String(latitude),
    longitude: String(longitude),
    current: [
      "temperature_2m",
      "relative_humidity_2m",
      "precipitation",
      "wind_speed_10m",
      "wind_direction_10m",
      "wind_gusts_10m",
      "soil_moisture_0_to_1cm",
      "vapour_pressure_deficit",
    ].join(","),
    timezone: "auto",
  })}`;
  const air = `${AIR_URL}?${query({
    latitude: String(latitude),
    longitude: String(longitude),
    current: "pm2_5,pm10,us_aqi,uv_index",
    timezone: "auto",
    domains: "cams_global",
  })}`;

  const [weatherResult, airResult] = await Promise.allSettled([json(forecast), json(air)]);
  if (weatherResult.status === "rejected" && airResult.status === "rejected") {
    throw new Error("No se pudieron consultar Open-Meteo ni CAMS en este momento.");
  }
  const weather = weatherResult.status === "fulfilled" ? weatherResult.value.current || {} : {};
  const atmosphere = airResult.status === "fulfilled" ? airResult.value.current || {} : {};
  return {
    fetchedAt: new Date().toISOString(),
    latitude,
    longitude,
    temperature: numberOrNull(weather.temperature_2m),
    humidity: numberOrNull(weather.relative_humidity_2m),
    precipitation: numberOrNull(weather.precipitation),
    windSpeed: numberOrNull(weather.wind_speed_10m),
    windDirection: numberOrNull(weather.wind_direction_10m),
    windGusts: numberOrNull(weather.wind_gusts_10m),
    soilMoisture: numberOrNull(weather.soil_moisture_0_to_1cm),
    vapourPressureDeficit: numberOrNull(weather.vapour_pressure_deficit),
    pm25: numberOrNull(atmosphere.pm2_5),
    pm10: numberOrNull(atmosphere.pm10),
    usAqi: numberOrNull(atmosphere.us_aqi),
    uvIndex: numberOrNull(atmosphere.uv_index),
  };
}

export function distanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const radius = 6371;
  const toRad = (value: number) => value * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function compass(direction: number | null): string {
  if (direction == null) return "sin dirección disponible";
  const points = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"];
  return points[Math.round(direction / 45) % 8];
}

export function relativeTime(value: string): string {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60_000));
  if (minutes < 60) return `hace ${minutes} min`;
  if (minutes < 1440) return `hace ${Math.round(minutes / 60)} h`;
  return `hace ${Math.round(minutes / 1440)} d`;
}

export interface FireReading {
  level: "normal" | "atencion" | "critico";
  headline: string;
  explanation: string;
  nearest: { detection: Detection; distance: number } | null;
  detections48h: number;
  dry: boolean;
  highWind: boolean;
}

export function buildFireReading(
  latitude: number,
  longitude: number,
  detections: Detection[],
  earth: EarthNow | null,
  hasCriticalAlert: boolean,
): FireReading {
  const active = detections
    .filter((item) => isInMisiones(item.lat, item.lon) && Date.now() - new Date(item.acquired_at).getTime() <= 48 * 3_600_000)
    .map((detection) => ({ detection, distance: distanceKm(latitude, longitude, detection.lat, detection.lon) }))
    .sort((a, b) => a.distance - b.distance);
  const nearest = active[0] || null;
  const dry = (earth?.soilMoisture ?? 0.3) < 0.18 || (earth?.humidity ?? 70) < 42;
  const highWind = (earth?.windGusts ?? earth?.windSpeed ?? 0) >= 35;
  const poorAir = (earth?.pm25 ?? 0) >= 35 || (earth?.usAqi ?? 0) >= 151;
  const level = hasCriticalAlert
    ? "critico"
    : nearest && (nearest.detection.confidence ?? 0) >= 0.6
      ? "atencion"
      : poorAir || (dry && highWind)
        ? "atencion"
        : "normal";
  const headline = level === "critico"
    ? "Hay señales que requieren verificación inmediata"
    : level === "atencion"
      ? "Hay condiciones para prestar atención"
      : "No aparecen señales cercanas de incendio activo";
  const explanation = nearest
    ? `El satélite marcó un punto caliente a ${nearest.distance.toFixed(1)} km, ${relativeTime(nearest.detection.acquired_at)}. No confirma por sí solo un incendio: hace falta verificar humo, cámaras y terreno.`
    : dry && highWind
      ? "El ambiente está seco y hay viento. No aparece un punto caliente cercano, pero un fuego podría propagarse rápido."
      : "No se registraron puntos calientes cercanos en las últimas 48 horas dentro de la información disponible.";
  return { level, headline, explanation, nearest, detections48h: active.length, dry, highWind };
}

export function firePublicMessage(
  latitude: number,
  longitude: number,
  reading: FireReading,
  earth: EarthNow | null,
): string {
  return [
    "🔥 *EcoNexo · Focos de incendio y humo*",
    "",
    `*${reading.headline}*`,
    reading.explanation,
    "",
    `📍 Zona: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`,
    `💨 Viento: ${earth?.windSpeed?.toFixed(0) ?? "s/d"} km/h hacia ${compass(earth?.windDirection ?? null)}`,
    `🌫️ Aire: PM2.5 ${earth?.pm25?.toFixed(1) ?? "s/d"} µg/m³ · AQI ${earth?.usAqi?.toFixed(0) ?? "s/d"}`,
    `🛰️ Puntos calientes en 48 h: ${reading.detections48h}`,
    "",
    "Recomendación: verificar en terreno y llamar al 911 si hay fuego o humo visible.",
    "Lectura preventiva: no reemplaza una alerta oficial ni una pericia técnica.",
  ].join("\n");
}
