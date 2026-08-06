import type { EarthIntel } from "./earth-intel";
import type {
  Detection,
  EnvironmentalAlertSnapshot,
  EnvironmentalIndexSnapshot,
  EnvironmentalSnapshot,
  SpaceAILevel,
  ThreatDomainId,
} from "./types";

export const SPACEAI_METHODOLOGY_VERSION = "SpaceAI 1.0 · Matriz técnica 2026-06-03 · EcoNexo HTI 0.3";

const LEVEL_LABELS: Record<SpaceAILevel, string> = {
  R0: "Basal",
  R1: "Vigilancia",
  R2: "Alerta",
  R3: "Amenaza alta",
  R4: "Crítico",
  R5: "Emergencia",
};
const LEVEL_RANK: Record<SpaceAILevel, number> = { R0: 0, R1: 1, R2: 2, R3: 3, R4: 4, R5: 5 };
const LEVEL_FLOOR: Record<SpaceAILevel, number> = { R0: 0, R1: 20, R2: 35, R3: 55, R4: 75, R5: 92 };

export interface SpaceAIIndex extends EnvironmentalIndexSnapshot {
  persistence: number;
  trend: Array<number | null>;
}

export interface HotspotSummary {
  count48h: number;
  highConfidence48h: number;
  maximumFrp: number | null;
  nearestDistanceKm: number | null;
  radiusKm: number;
  enabled: boolean;
}

export interface SpaceAIOptions {
  fireRadiusKm?: number;
  firmsEnabled?: boolean;
}

export interface SpaceAIThreatAssessment {
  methodologyVersion: string;
  generatedAt: string;
  overallScore: number;
  overallLevel: SpaceAILevel;
  overallLabel: string;
  indices: SpaceAIIndex[];
  alerts: EnvironmentalAlertSnapshot[];
  indexSeries: number[];
  hotspots: HotspotSummary;
  snapshot: EnvironmentalSnapshot;
}

function clamp(value: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, value));
}

function round(value: number, digits = 0): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function present(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function average(values: Array<number | null>): number | null {
  const clean = values.filter((value): value is number => value != null);
  return clean.length ? clean.reduce((sum, value) => sum + value, 0) / clean.length : null;
}

function sum(values: Array<number | null>): number | null {
  const clean = values.filter((value): value is number => value != null);
  return clean.length ? clean.reduce((total, value) => total + value, 0) : null;
}

function max(values: Array<number | null>): number | null {
  const clean = values.filter((value): value is number => value != null);
  return clean.length ? Math.max(...clean) : null;
}

function beforeCurrent(values: Array<number | null>, currentIndex: number, count: number): Array<number | null> {
  if (!values.length) return [];
  const end = currentIndex >= 0 ? currentIndex + 1 : values.length;
  return values.slice(Math.max(0, end - count), end);
}

function fromCurrent(values: Array<number | null>, currentIndex: number, count: number): Array<number | null> {
  if (!values.length) return [];
  const start = currentIndex >= 0 ? currentIndex : 0;
  return values.slice(start, start + count);
}

function dailyCurrentIndex(intel: EarthIntel): number {
  const observedDay = intel.weather.observedAt.slice(0, 10) || new Date().toISOString().slice(0, 10);
  const exact = intel.daily.time.indexOf(observedDay);
  return exact >= 0 ? exact : Math.max(0, intel.daily.time.length - 1);
}

function dailyRecent(values: Array<number | null>, intel: EarthIntel, count = 7): Array<number | null> {
  const index = dailyCurrentIndex(intel);
  return values.slice(Math.max(0, index - count + 1), index + 1);
}

function dailyFuture(values: Array<number | null>, intel: EarthIntel, count = 7): Array<number | null> {
  const index = dailyCurrentIndex(intel);
  return values.slice(index, index + count);
}

function levelAtLeast(level: SpaceAILevel, floor: SpaceAILevel): SpaceAILevel {
  return LEVEL_RANK[level] >= LEVEL_RANK[floor] ? level : floor;
}

function levelFromScore(score: number): SpaceAILevel {
  if (score >= 92) return "R5";
  if (score >= 75) return "R4";
  if (score >= 55) return "R3";
  if (score >= 35) return "R2";
  if (score >= 20) return "R1";
  return "R0";
}

function levelFromRelativePercent(relative: number | null): SpaceAILevel {
  if (relative == null) return "R0";
  if (relative >= 200) return "R4";
  if (relative >= 150) return "R3";
  if (relative >= 100) return "R2";
  if (relative >= 80) return "R1";
  return "R0";
}

function scoreFromRelativePercent(relative: number | null): number {
  if (relative == null) return 0;
  if (relative < 80) return clamp(relative / 80) * 19;
  if (relative < 100) return 20 + ((relative - 80) / 20) * 14;
  if (relative < 150) return 35 + ((relative - 100) / 50) * 19;
  if (relative < 200) return 55 + ((relative - 150) / 50) * 19;
  return 75 + clamp((relative - 200) / 200) * 20;
}

function scoreForLevel(level: SpaceAILevel, detail = 0.5): number {
  const rank = LEVEL_RANK[level];
  const next = rank === 5 ? 100 : LEVEL_FLOOR[`R${rank + 1}` as SpaceAILevel];
  return round(LEVEL_FLOOR[level] + (next - LEVEL_FLOOR[level]) * clamp(detail), 1);
}

function levelMax(...levels: SpaceAILevel[]): SpaceAILevel {
  return levels.reduce((current, level) => LEVEL_RANK[level] > LEVEL_RANK[current] ? level : current, "R0");
}

function aqiLevel(aqi: number | null): SpaceAILevel {
  if (aqi == null) return "R0";
  if (aqi > 300) return "R5";
  if (aqi >= 201) return "R4";
  if (aqi >= 151) return "R3";
  if (aqi >= 101) return "R2";
  if (aqi >= 51) return "R1";
  return "R0";
}

function uvLevel(uv: number | null): SpaceAILevel {
  if (uv == null) return "R0";
  if (uv >= 11) return "R5";
  if (uv >= 8) return "R4";
  if (uv >= 6) return "R3";
  if (uv >= 3) return "R2";
  return "R0";
}

function heatIndexCelsius(temperatureC: number | null, humidity: number | null): number | null {
  if (temperatureC == null || humidity == null) return null;
  if (temperatureC < 26.7) return temperatureC;
  const temperatureF = temperatureC * 9 / 5 + 32;
  let heatIndex = -42.379
    + 2.04901523 * temperatureF
    + 10.14333127 * humidity
    - 0.22475541 * temperatureF * humidity
    - 0.00683783 * temperatureF ** 2
    - 0.05481717 * humidity ** 2
    + 0.00122874 * temperatureF ** 2 * humidity
    + 0.00085282 * temperatureF * humidity ** 2
    - 0.00000199 * temperatureF ** 2 * humidity ** 2;

  if (humidity < 13 && temperatureF >= 80 && temperatureF <= 112) {
    heatIndex -= ((13 - humidity) / 4) * Math.sqrt((17 - Math.abs(temperatureF - 95)) / 17);
  } else if (humidity > 85 && temperatureF >= 80 && temperatureF <= 87) {
    heatIndex += ((humidity - 85) / 10) * ((87 - temperatureF) / 5);
  }
  return round((heatIndex - 32) * 5 / 9, 1);
}

function wetBulbCelsius(temperatureC: number | null, humidity: number | null): number | null {
  if (temperatureC == null || humidity == null) return null;
  const rh = clamp(humidity, 1, 100);
  const result = temperatureC * Math.atan(0.151977 * Math.sqrt(rh + 8.313659))
    + Math.atan(temperatureC + rh)
    - Math.atan(rh - 1.676331)
    + 0.00391838 * rh ** 1.5 * Math.atan(0.023101 * rh)
    - 4.686035;
  return round(result, 1);
}

function heatLevel(heatIndex: number | null, wetBulb: number | null): SpaceAILevel {
  let level: SpaceAILevel = "R0";
  if (heatIndex != null) {
    if (heatIndex >= 52) level = "R5";
    else if (heatIndex >= 39) level = "R4";
    else if (heatIndex >= 32) level = "R3";
    else if (heatIndex >= 27) level = "R2";
    else if (heatIndex >= 24) level = "R1";
  }
  if (wetBulb != null && wetBulb >= 35) return "R5";
  if (wetBulb != null && wetBulb >= 32) level = levelAtLeast(level, "R4");
  return level;
}

function distanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const radius = 6371;
  const toRad = (value: number) => value * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function hotspotSummary(
  latitude: number,
  longitude: number,
  detections: Detection[],
  radiusKm = 50,
  enabled = true,
  now = Date.now(),
): HotspotSummary {
  const normalizedRadius = Math.min(500, Math.max(1, radiusKm));
  const recent = enabled ? detections
    .map((detection) => ({ detection, distance: distanceKm(latitude, longitude, detection.lat, detection.lon) }))
    .filter(({ detection, distance }) => distance <= normalizedRadius && now - new Date(detection.acquired_at).getTime() <= 48 * 3_600_000) : [];
  const nearest = recent.length ? Math.min(...recent.map((item) => item.distance)) : null;
  const frp = max(recent.map(({ detection }) => detection.frp));
  return {
    count48h: recent.length,
    highConfidence48h: recent.filter(({ detection }) => (detection.confidence ?? 0) >= 0.6).length,
    maximumFrp: frp == null ? null : round(frp, 1),
    nearestDistanceKm: nearest == null ? null : round(nearest, 1),
    radiusKm: normalizedRadius,
    enabled,
  };
}

function evidenceValue(label: string, value: number | null, unit: string, digits = 1): string {
  return `${label}: ${value == null ? "sin dato" : `${value.toFixed(digits)}${unit}`}`;
}

function airIndex(intel: EarthIntel): SpaceAIIndex {
  const past24 = beforeCurrent(intel.series.pm25, intel.series.currentAirIndex, 24);
  const pm25Average = average(past24) ?? intel.atmosphere.pm25;
  const relative = pm25Average == null ? null : pm25Average / 15 * 100;
  const aqi = intel.atmosphere.usAqi;
  const level = levelMax(levelFromRelativePercent(relative), aqiLevel(aqi));
  const score = Math.max(scoreFromRelativePercent(relative), scoreForLevel(aqiLevel(aqi), aqi == null ? 0 : clamp(aqi / 500)));
  const persistentHours = past24.filter((value) => value != null && value >= 15).length;
  return {
    id: "air",
    label: "Calidad del aire",
    level,
    score: round(score, 1),
    value: pm25Average == null ? null : round(pm25Average, 1),
    unit: "µg/m³ PM2.5 · 24 h",
    status: aqi != null ? `AQI ${Math.round(aqi)} · ${LEVEL_LABELS[level]}` : LEVEL_LABELS[level],
    source: "Open-Meteo Air Quality · Copernicus CAMS",
    confidence: intel.sources.airQuality === "live" ? 0.74 : 0.35,
    persistence: 1 + clamp(persistentHours / 24) * 0.5,
    action: level === "R0" ? "Monitoreo rutinario." : level === "R1" ? "Aumentar frecuencia y observar grupos sensibles." : "Contrastar con estación o sensor calibrado y emitir comunicación preventiva si persiste.",
    health_impacts: ["Crisis asmática y bronquitis aguda", "Descompensación de EPOC", "Eventos cardiovasculares en población vulnerable"],
    evidence: [
      evidenceValue("PM2.5 promedio estimado", pm25Average, " µg/m³"),
      evidenceValue("Umbral OMS 24 h", 15, " µg/m³", 0),
      evidenceValue("AQI EE. UU.", aqi, "", 0),
    ],
    trend: fromCurrent(intel.series.pm25, intel.series.currentAirIndex, 12),
  };
}

function heatIndex(intel: EarthIntel): SpaceAIIndex {
  const currentHeat = heatIndexCelsius(intel.weather.temperature, intel.weather.humidity);
  const wetBulb = wetBulbCelsius(intel.weather.temperature, intel.weather.humidity);
  const level = heatLevel(currentHeat, wetBulb);
  const futureTemperature = fromCurrent(intel.series.temperature, intel.series.currentWeatherIndex, 12);
  const futureHumidity = fromCurrent(intel.series.humidity, intel.series.currentWeatherIndex, 12);
  const futureHeat = futureTemperature.map((temperature, index) => heatIndexCelsius(temperature, futureHumidity[index] ?? null));
  const persistent = futureHeat.filter((value) => value != null && value >= 32).length;
  return {
    id: "heat",
    label: "Estrés térmico",
    level,
    score: scoreForLevel(level, currentHeat == null ? 0 : clamp((currentHeat - 24) / 30)),
    value: currentHeat,
    unit: "°C índice de calor",
    status: wetBulb != null ? `${LEVEL_LABELS[level]} · Tw ${wetBulb.toFixed(1)}°C` : LEVEL_LABELS[level],
    source: "Open-Meteo · cálculo NOAA de índice de calor",
    confidence: intel.sources.weather === "live" ? 0.84 : 0.4,
    persistence: 1 + clamp(persistent / 12) * 0.5,
    action: level === "R0" ? "Monitoreo rutinario." : level === "R1" || level === "R2" ? "Hidratación, pausas y seguimiento de población sensible." : "Activar protocolo de calor, limitar exposición y coordinar respuesta sanitaria.",
    health_impacts: ["Fatiga, calambres y agotamiento", "Golpe de calor", "Descompensación cardiovascular, renal o respiratoria"],
    evidence: [
      evidenceValue("Temperatura", intel.weather.temperature, " °C"),
      evidenceValue("Humedad relativa", intel.weather.humidity, "%", 0),
      evidenceValue("Índice de calor", currentHeat, " °C"),
      evidenceValue("Bulbo húmedo estimado", wetBulb, " °C"),
    ],
    trend: futureHeat,
  };
}

function moistureIndex(intel: EarthIntel): SpaceAIIndex {
  const humidity = intel.weather.humidity;
  const soilMoisture = intel.weather.soilMoisture;
  const soilMoisturePct = soilMoisture == null ? null : soilMoisture * 100;
  const precipitation24 = sum(beforeCurrent(intel.series.precipitation, intel.series.currentWeatherIndex, 24));
  const precipitation7d = sum(dailyRecent(intel.daily.precipitationSum, intel));
  const vpd = intel.weather.vapourPressureDeficit;

  const humidityComponent = humidity == null ? 0.5 : clamp((humidity - 20) / 80);
  const soilComponent = soilMoisture == null ? 0.45 : clamp(soilMoisture / 0.45);
  const rainComponent = precipitation7d == null ? 0.35 : clamp(precipitation7d / 70);
  const vpdComponent = vpd == null ? 0.5 : 1 - clamp(vpd / 2.2);
  const balance = 100 * (
    humidityComponent * 0.35 + soilComponent * 0.38 + rainComponent * 0.17 + vpdComponent * 0.10
  );

  let level: SpaceAILevel = "R0";
  let riskScore = 0;
  let state = "equilibrio operativo";
  if (balance < 5) { level = "R4"; riskScore = 78; state = "déficit extremo"; }
  else if (balance < 15) { level = "R3"; riskScore = 62; state = "déficit severo"; }
  else if (balance < 25) { level = "R2"; riskScore = 44; state = "déficit"; }
  else if (balance < 35) { level = "R1"; riskScore = 25; state = "tendencia seca"; }
  else if (balance >= 94 && ((precipitation24 ?? 0) >= 30 || (soilMoisture ?? 0) >= 0.45)) { level = "R4"; riskScore = 79; state = "saturación crítica"; }
  else if (balance >= 88) { level = "R3"; riskScore = 62; state = "saturación alta"; }
  else if (balance >= 78) { level = "R2"; riskScore = 44; state = "exceso de humedad"; }
  else if (balance >= 68) { level = "R1"; riskScore = 25; state = "tendencia húmeda"; }

  const trendHumidity = fromCurrent(intel.series.humidity, intel.series.currentWeatherIndex, 12);
  const trendSoil = fromCurrent(intel.series.soilMoisture, intel.series.currentWeatherIndex, 12);
  const trendVpd = fromCurrent(intel.series.vapourPressureDeficit, intel.series.currentWeatherIndex, 12);
  const trend = Array.from({ length: Math.max(trendHumidity.length, trendSoil.length, trendVpd.length) }, (_, index) => {
    const rh = trendHumidity[index];
    const soil = trendSoil[index];
    const localVpd = trendVpd[index];
    const rhComponent = rh == null ? humidityComponent : clamp((rh - 20) / 80);
    const localSoil = soil == null ? soilComponent : clamp(soil / 0.45);
    const localVpdComponent = localVpd == null ? vpdComponent : 1 - clamp(localVpd / 2.2);
    return round(100 * (rhComponent * 0.43 + localSoil * 0.43 + localVpdComponent * 0.14), 1);
  });

  return {
    id: "moisture",
    label: "Índice de humedad",
    level,
    score: round(riskScore, 1),
    value: round(balance, 1),
    unit: "/100 balance ambiental",
    status: `${LEVEL_LABELS[level]} · ${state}`,
    source: "Open-Meteo Forecast · índice eco-hídrico EcoNexo",
    confidence: intel.sources.weather === "live" ? 0.76 : 0.35,
    persistence: 1.1,
    action: level === "R0" ? "Monitoreo rutinario del balance de humedad." : balance < 35 ? "Elevar vigilancia de sequedad, combustible vegetal, polvo y disponibilidad hídrica." : "Contrastar saturación con drenajes, anegamientos y sensores locales de suelo o nivel.",
    health_impacts: [
      "Déficit: mayor peligro de incendio, polvo y estrés hídrico",
      "Exceso persistente: anegamiento, criaderos y deterioro de condiciones sanitarias",
      "No equivale a humedad interior ni diagnostica moho",
    ],
    evidence: [
      evidenceValue("Humedad relativa exterior", humidity, "%", 0),
      evidenceValue("Humedad superficial de suelo", soilMoisturePct, "%"),
      evidenceValue("Precipitación reciente 7 d", precipitation7d, " mm"),
      evidenceValue("Déficit de presión de vapor", vpd, " kPa"),
    ],
    trend,
  };
}

function fireIndex(intel: EarthIntel, hotspots: HotspotSummary): SpaceAIIndex {
  const soilMoisturePct = present(intel.weather.soilMoisture) ? intel.weather.soilMoisture * 100 : null;
  const dryness = soilMoisturePct == null ? 0.35 : clamp((25 - soilMoisturePct) / 20);
  const lowHumidity = intel.weather.humidity == null ? 0.25 : clamp((55 - intel.weather.humidity) / 35);
  const vpd = intel.weather.vapourPressureDeficit == null ? 0.25 : clamp((intel.weather.vapourPressureDeficit - 0.4) / 1.6);
  const wind = intel.weather.windGusts == null ? 0.2 : clamp(intel.weather.windGusts / 70);
  const precipitation24 = sum(beforeCurrent(intel.series.precipitation, intel.series.currentWeatherIndex, 24)) ?? 0;
  const rainDeficit = 1 - clamp(precipitation24 / 12);
  const smoke = clamp(((intel.atmosphere.pm25 ?? 0) / 60 + (intel.atmosphere.aerosolOpticalDepth ?? 0) / 1.5) / 2);
  const hotspotSignal = hotspots.highConfidence48h ? clamp(0.55 + hotspots.highConfidence48h * 0.15) : 0;
  let score = 100 * (
    dryness * 0.20 + lowHumidity * 0.13 + vpd * 0.13 + wind * 0.12
    + rainDeficit * 0.12 + smoke * 0.12 + hotspotSignal * 0.18
  );
  let level = levelFromScore(score);
  if (hotspots.highConfidence48h > 0) level = levelAtLeast(level, "R3");
  if (hotspots.highConfidence48h >= 2 && (intel.atmosphere.usAqi ?? 0) >= 151 && (hotspots.nearestDistanceKm ?? 100) <= 15) {
    level = "R5";
    score = Math.max(score, 94);
  } else if (hotspots.highConfidence48h > 0 && ((intel.atmosphere.pm25 ?? 0) >= 30 || smoke >= 0.55)) {
    level = levelAtLeast(level, "R4");
    score = Math.max(score, 78);
  }
  const trend = fromCurrent(intel.series.soilMoisture, intel.series.currentWeatherIndex, 12).map((moisture, index) => {
    const rh = fromCurrent(intel.series.humidity, intel.series.currentWeatherIndex, 12)[index];
    const gust = fromCurrent(intel.series.windGusts, intel.series.currentWeatherIndex, 12)[index];
    const localDryness = moisture == null ? dryness : clamp((0.25 - moisture) / 0.20);
    const localRh = rh == null ? lowHumidity : clamp((55 - rh) / 35);
    const localWind = gust == null ? wind : clamp(gust / 70);
    return round(100 * (localDryness * 0.46 + localRh * 0.31 + localWind * 0.23), 1);
  });
  return {
    id: "fire",
    label: "Incendio y humo",
    level,
    score: round(Math.max(score, LEVEL_FLOOR[level]), 1),
    value: hotspots.count48h,
    unit: "focos FIRMS · 48 h",
    status: !hotspots.enabled
      ? `${LEVEL_LABELS[level]} · FIRMS deshabilitado`
      : hotspots.count48h ? `${hotspots.count48h} foco(s) a ≤${hotspots.radiusKm} km` : `${LEVEL_LABELS[level]} · sin focos cercanos`,
    source: hotspots.enabled ? "NASA FIRMS + Open-Meteo + Copernicus CAMS" : "Open-Meteo + Copernicus CAMS · FIRMS deshabilitado",
    confidence: !hotspots.enabled ? (intel.sources.weather === "live" ? 0.58 : 0.3) : hotspots.count48h ? 0.9 : intel.sources.weather === "live" ? 0.7 : 0.35,
    persistence: 1 + clamp(rainDeficit * 0.25 + dryness * 0.25),
    action: hotspots.count48h ? "Validar en terreno, revisar dirección del viento y escalar a la autoridad competente." : level === "R0" || level === "R1" ? "Monitoreo preventivo." : "Elevar vigilancia de combustibles, humo y focos térmicos.",
    health_impacts: ["Asma y EPOC descompensado", "Eventos cardiovasculares", "Irritación ocular y riesgo por monóxido de carbono"],
    evidence: [
      hotspots.enabled
        ? `${hotspots.count48h} detección(es) térmica(s) FIRMS en 48 h dentro de ${hotspots.radiusKm} km`
        : "NASA FIRMS deshabilitado por la política de fuentes de la organización",
      evidenceValue("Humedad de suelo", soilMoisturePct, "%"),
      evidenceValue("Ráfaga", intel.weather.windGusts, " km/h"),
      evidenceValue("PM2.5", intel.atmosphere.pm25, " µg/m³"),
      "Open-Meteo aporta peligro meteorológico; los focos reales provienen de NASA FIRMS.",
    ],
    trend,
  };
}

function hydricIndex(intel: EarthIntel): SpaceAIIndex {
  const current = intel.flood.currentDischarge;
  const baseline = intel.flood.baselineMedian ?? intel.flood.referenceP75;
  const ratio = current != null && baseline != null && baseline > 0 ? current / baseline : null;
  const precipitation24 = sum(beforeCurrent(intel.series.precipitation, intel.series.currentWeatherIndex, 24));
  const precipitationRecent7d = sum(dailyRecent(intel.daily.precipitationSum, intel));
  const precipitationForecast7d = sum(dailyFuture(intel.daily.precipitationSum, intel));
  const forecastMax = intel.flood.forecastMax;
  const forecastRatio = forecastMax != null && baseline != null && baseline > 0 ? forecastMax / baseline : ratio;

  let floodScore = 0;
  let floodLevel: SpaceAILevel = "R0";
  const riskRatio = Math.max(ratio ?? 0, forecastRatio ?? 0);
  if (riskRatio >= 2.2) { floodLevel = "R4"; floodScore = 82; }
  else if (riskRatio >= 1.6) { floodLevel = "R3"; floodScore = 64; }
  else if (riskRatio >= 1.25) { floodLevel = "R2"; floodScore = 45; }
  else if (riskRatio >= 1.05) { floodLevel = "R1"; floodScore = 25; }
  if ((precipitationForecast7d ?? 0) >= 120) floodScore += 12;
  else if ((precipitationForecast7d ?? 0) >= 70) floodScore += 7;
  floodScore = Math.min(89, floodScore);
  floodLevel = levelMax(floodLevel, levelFromScore(floodScore));
  if (LEVEL_RANK[floodLevel] > LEVEL_RANK.R4) floodLevel = "R4";

  const soilMoisturePct = present(intel.weather.soilMoisture) ? intel.weather.soilMoisture * 100 : null;
  const drySoil = soilMoisturePct == null ? 0.3 : clamp((18 - soilMoisturePct) / 13);
  const vpd = intel.weather.vapourPressureDeficit == null ? 0.25 : clamp((intel.weather.vapourPressureDeficit - 0.7) / 1.5);
  const rainDeficit = 1 - clamp((precipitationRecent7d ?? 0) / 35);
  const et0 = sum(dailyRecent(intel.daily.evapotranspiration, intel)) ?? 0;
  const evapDemand = clamp(et0 / 35);
  const droughtScore = 100 * (drySoil * 0.38 + vpd * 0.23 + rainDeficit * 0.27 + evapDemand * 0.12);
  let droughtLevel = levelFromScore(droughtScore);
  if (LEVEL_RANK[droughtLevel] > LEVEL_RANK.R3) droughtLevel = "R3";

  const useFlood = floodScore >= droughtScore;
  const level = useFlood ? floodLevel : droughtLevel;
  const score = useFlood ? floodScore : droughtScore;
  const status = useFlood
    ? `${LEVEL_LABELS[level]} · descarga ${ratio == null ? "s/d" : `${ratio.toFixed(2)}× base`}`
    : `${LEVEL_LABELS[level]} · estrés hídrico meteorológico`;
  return {
    id: "hydric",
    label: "Riesgo hídrico",
    level,
    score: round(score, 1),
    value: useFlood ? (ratio == null ? current : round(ratio, 2)) : soilMoisturePct == null ? null : round(soilMoisturePct, 1),
    unit: useFlood ? (ratio == null ? "m³/s" : "× mediana reciente") : "% humedad de suelo",
    status,
    source: "Open-Meteo Flood · GloFAS + Open-Meteo Forecast",
    confidence: intel.sources.flood === "live" ? 0.68 : 0.4,
    persistence: 1 + clamp(Math.max(riskRatio - 1, droughtScore / 100) * 0.35),
    action: level === "R0" || level === "R1" ? "Monitoreo y calibración con hidrometría local." : useFlood ? "Contrastar con estaciones y reportes de anegamiento; proteger agua segura y servicios esenciales." : "Verificar reservas, incendios, abastecimiento y condiciones de higiene.",
    health_impacts: ["Diarreas y leptospirosis ante inundación", "Contaminación de pozos e interrupción de servicios", "Escasez de agua, polvo e incremento del peligro de incendio"],
    evidence: [
      evidenceValue("Descarga modelada", current, " m³/s"),
      evidenceValue("Relación con mediana reciente", ratio, "×", 2),
      evidenceValue("Precipitación 24 h", precipitation24, " mm"),
      evidenceValue("Precipitación reciente 7 d", precipitationRecent7d, " mm"),
      evidenceValue("Precipitación prevista 7 d", precipitationForecast7d, " mm"),
      "El índice es un proxy operativo; no equivale a SPI ni a un umbral hidrológico oficial local.",
    ],
    trend: fromCurrent(intel.flood.riverDischarge, intel.flood.currentIndex, 12),
  };
}

function uvIndex(intel: EarthIntel): SpaceAIIndex {
  const uv = intel.atmosphere.uvIndex;
  const level = uvLevel(uv);
  return {
    id: "uv",
    label: "Radiación UV",
    level,
    score: scoreForLevel(level, uv == null ? 0 : clamp(uv / 14)),
    value: uv == null ? null : round(uv, 1),
    unit: "índice UV",
    status: LEVEL_LABELS[level],
    source: "Open-Meteo Air Quality · Copernicus CAMS",
    confidence: intel.sources.airQuality === "live" ? 0.72 : 0.35,
    persistence: 1,
    action: uv == null || uv < 3 ? "Protección solar habitual." : uv < 8 ? "Protección de piel y ojos; limitar exposición prolongada." : "Evitar exposición al mediodía y reforzar comunicación preventiva.",
    health_impacts: ["Quemadura solar", "Daño ocular y cataratas", "Fotoenvejecimiento y cáncer de piel por exposición acumulada"],
    evidence: [evidenceValue("Índice UV", uv, "")],
    trend: fromCurrent(intel.series.uvIndex, intel.series.currentAirIndex, 12),
  };
}

function vectorIndex(intel: EarthIntel): SpaceAIIndex {
  const temperature = intel.weather.temperature;
  const humidity = intel.weather.humidity;
  const precipitationRecent7d = sum(dailyRecent(intel.daily.precipitationSum, intel));
  const precipitationForecast7d = sum(dailyFuture(intel.daily.precipitationSum, intel));
  const precipitationSignal = Math.max(precipitationRecent7d ?? 0, precipitationForecast7d ?? 0);
  const temperatureSuitability = temperature == null ? 0.35 : temperature >= 25 && temperature <= 30
    ? 1
    : temperature >= 20 && temperature < 25
      ? (temperature - 20) / 5
      : temperature > 30 && temperature <= 35
        ? (35 - temperature) / 5
        : 0;
  const humiditySuitability = humidity == null ? 0.35 : clamp((humidity - 45) / 25);
  const rainSuitability = precipitationRecent7d == null && precipitationForecast7d == null ? 0.35 : clamp(precipitationSignal / 70);
  const score = 100 * (temperatureSuitability * 0.42 + humiditySuitability * 0.33 + rainSuitability * 0.25);
  let level: SpaceAILevel = score >= 72 ? "R3" : score >= 52 ? "R2" : score >= 32 ? "R1" : "R0";
  if (LEVEL_RANK[level] > LEVEL_RANK.R3) level = "R3";
  const trendTemperature = fromCurrent(intel.series.temperature, intel.series.currentWeatherIndex, 12);
  const trendHumidity = fromCurrent(intel.series.humidity, intel.series.currentWeatherIndex, 12);
  const trend = trendTemperature.map((value, index) => {
    if (value == null) return null;
    const t = value >= 25 && value <= 30 ? 1 : value >= 20 && value < 25 ? (value - 20) / 5 : value > 30 && value <= 35 ? (35 - value) / 5 : 0;
    const h = trendHumidity[index] == null ? 0.35 : clamp(((trendHumidity[index] as number) - 45) / 25);
    return round(100 * (t * 0.58 + h * 0.42), 1);
  });
  return {
    id: "vector",
    label: "Aptitud vectorial",
    level,
    score: round(score, 1),
    value: round(score, 0),
    unit: "/100 eco-climático",
    status: `${LEVEL_LABELS[level]} · dengue/Aedes`,
    source: "Open-Meteo · modelo compuesto SpaceAI",
    confidence: 0.58,
    persistence: 1.15,
    action: level === "R0" ? "Vigilancia rutinaria." : "Cruzar con ovitrampas, criaderos y casos humanos; reforzar eliminación de recipientes con agua.",
    health_impacts: ["Mayor probabilidad ambiental de transmisión de dengue", "Zika y chikungunya", "No implica presencia confirmada de vector ni brote"],
    evidence: [
      evidenceValue("Temperatura", temperature, " °C"),
      evidenceValue("Humedad relativa", humidity, "%", 0),
      evidenceValue("Lluvia reciente 7 d", precipitationRecent7d, " mm"),
      evidenceValue("Lluvia prevista 7 d", precipitationForecast7d, " mm"),
      "La lluvia de 7 días es un proxy preliminar; el documento técnico recomienda calibrar rezagos de 2 a 8 semanas.",
      "El nivel se limita a R3 sin evidencia entomológica o casos humanos sobre la línea base.",
    ],
    trend,
  };
}

function alertSeverity(level: SpaceAILevel): EnvironmentalAlertSnapshot["severity"] {
  if (level === "R4" || level === "R5") return "critica";
  if (level === "R3") return "alta";
  if (level === "R2") return "media";
  return "baja";
}

function buildAlerts(indices: SpaceAIIndex[]): EnvironmentalAlertSnapshot[] {
  return indices
    .filter((index) => LEVEL_RANK[index.level] >= LEVEL_RANK.R2)
    .sort((a, b) => LEVEL_RANK[b.level] - LEVEL_RANK[a.level] || b.score - a.score)
    .map((index) => ({
      id: `spaceai-${index.id}`,
      domain: index.id,
      level: index.level,
      severity: alertSeverity(index.level),
      title: `${index.label}: ${index.status}`,
      summary: index.evidence.slice(0, 2).join(" · "),
      action: index.action,
      source: index.source,
      confidence: index.confidence,
    }));
}

function overallIndexSeries(intel: EarthIntel): number[] {
  const temperature = fromCurrent(intel.series.temperature, intel.series.currentWeatherIndex, 12);
  const humidity = fromCurrent(intel.series.humidity, intel.series.currentWeatherIndex, 12);
  const moisture = fromCurrent(intel.series.soilMoisture, intel.series.currentWeatherIndex, 12);
  const gusts = fromCurrent(intel.series.windGusts, intel.series.currentWeatherIndex, 12);
  const pm25 = fromCurrent(intel.series.pm25, intel.series.currentAirIndex, 12);
  return Array.from({ length: 12 }, (_, index) => {
    const heat = heatLevel(heatIndexCelsius(temperature[index] ?? null, humidity[index] ?? null), wetBulbCelsius(temperature[index] ?? null, humidity[index] ?? null));
    const heatScore = scoreForLevel(heat, 0.45);
    const airScore = scoreFromRelativePercent(pm25[index] == null ? null : (pm25[index] as number) / 15 * 100);
    const dry = moisture[index] == null ? 0.35 : clamp((0.25 - (moisture[index] as number)) / 0.20);
    const lowRh = humidity[index] == null ? 0.25 : clamp((55 - (humidity[index] as number)) / 35);
    const wind = gusts[index] == null ? 0.2 : clamp((gusts[index] as number) / 70);
    const fireScore = 100 * (dry * 0.48 + lowRh * 0.30 + wind * 0.22);
    return round(airScore * 0.36 + heatScore * 0.27 + fireScore * 0.37, 1);
  });
}

function sourceLabel(state: EarthIntel["sources"][keyof EarthIntel["sources"]]): string {
  if (state === "live") return "sincronizada";
  if (state === "disabled") return "deshabilitada";
  return "no disponible";
}

export function buildSpaceAIThreatAssessment(
  intel: EarthIntel | null,
  detections: Detection[],
  options: SpaceAIOptions = {},
): SpaceAIThreatAssessment | null {
  if (!intel) return null;
  const hotspots = hotspotSummary(
    intel.latitude,
    intel.longitude,
    detections,
    options.fireRadiusKm ?? 50,
    options.firmsEnabled ?? true,
  );
  const indices = [
    airIndex(intel),
    heatIndex(intel),
    moistureIndex(intel),
    fireIndex(intel, hotspots),
    hydricIndex(intel),
    uvIndex(intel),
    vectorIndex(intel),
  ];
  const weights: Record<ThreatDomainId, number> = {
    air: 0.21,
    heat: 0.16,
    moisture: 0.11,
    fire: 0.19,
    hydric: 0.16,
    uv: 0.07,
    vector: 0.10,
  };
  const weighted = indices.reduce((total, index) => total + weights[index.id] * index.score * index.persistence * index.confidence, 0)
    / indices.reduce((total, index) => total + weights[index.id], 0);
  // The global HTI represents weighted co-exposure. A critical domain keeps its
  // own alert, but must not pin the aggregate to the exact R4 floor (75).
  const overallScore = clamp(weighted, 0, 100);
  const overallLevel = levelFromScore(overallScore);
  const alerts = buildAlerts(indices);
  const pm25Average = average(beforeCurrent(intel.series.pm25, intel.series.currentAirIndex, 24)) ?? intel.atmosphere.pm25;
  const precipitation24 = sum(beforeCurrent(intel.series.precipitation, intel.series.currentWeatherIndex, 24));
  const precipitationRecent7d = sum(dailyRecent(intel.daily.precipitationSum, intel));
  const precipitationForecast7d = sum(dailyFuture(intel.daily.precipitationSum, intel));
  const heat = heatIndexCelsius(intel.weather.temperature, intel.weather.humidity);
  const wetBulb = wetBulbCelsius(intel.weather.temperature, intel.weather.humidity);
  const dischargeRatio = intel.flood.currentDischarge != null && intel.flood.baselineMedian != null && intel.flood.baselineMedian > 0
    ? intel.flood.currentDischarge / intel.flood.baselineMedian
    : null;
  const generatedAt = new Date().toISOString();

  const snapshot: EnvironmentalSnapshot = {
    methodology_version: SPACEAI_METHODOLOGY_VERSION,
    generated_at: generatedAt,
    latitude: intel.latitude,
    longitude: intel.longitude,
    overall_score: round(overallScore, 1),
    overall_level: overallLevel,
    overall_label: LEVEL_LABELS[overallLevel],
    observations: {
      temperature_c: intel.weather.temperature,
      relative_humidity_pct: intel.weather.humidity,
      soil_moisture_pct: intel.weather.soilMoisture == null ? null : round(intel.weather.soilMoisture * 100, 1),
      heat_index_c: heat,
      wet_bulb_c: wetBulb,
      pm25_24h_ug_m3: pm25Average == null ? null : round(pm25Average, 1),
      us_aqi: intel.atmosphere.usAqi,
      uv_index: intel.atmosphere.uvIndex,
      river_discharge_m3_s: intel.flood.currentDischarge,
      river_discharge_ratio: dischargeRatio == null ? null : round(dischargeRatio, 2),
      precipitation_24h_mm: precipitation24 == null ? null : round(precipitation24, 1),
      precipitation_7d_mm: precipitationRecent7d == null ? null : round(precipitationRecent7d, 1),
      precipitation_forecast_7d_mm: precipitationForecast7d == null ? null : round(precipitationForecast7d, 1),
      humidity_balance_index: indices.find((index) => index.id === "moisture")?.value ?? null,
      wind_gust_kmh: intel.weather.windGusts,
      vapour_pressure_deficit_kpa: intel.weather.vapourPressureDeficit,
    },
    indices: indices.map(({ persistence: _persistence, trend: _trend, ...index }) => index),
    alerts,
    hotspots: {
      count_48h: hotspots.count48h,
      high_confidence_count_48h: hotspots.highConfidence48h,
      maximum_frp_mw: hotspots.maximumFrp,
      nearest_distance_km: hotspots.nearestDistanceKm,
    },
    sources: {
      weather: `Open-Meteo Forecast (${sourceLabel(intel.sources.weather)})`,
      air_quality: `Copernicus CAMS vía Open-Meteo (${sourceLabel(intel.sources.airQuality)})`,
      flood: `GloFAS vía Open-Meteo Flood (${sourceLabel(intel.sources.flood)})`,
      hotspots: hotspots.enabled
        ? `NASA FIRMS / detecciones satelitales EcoNexo · radio ${hotspots.radiusKm} km`
        : "NASA FIRMS (deshabilitado por configuración)",
    },
    limitations: [
      "Open-Meteo, CAMS y GloFAS son datos de modelos o reanálisis geoespaciales; no son lecturas del sensor físico instalado en el nodo.",
      "Los umbrales SpaceAI son referencias sanitarias y operativas; no sustituyen normativa argentina, diagnóstico clínico ni protocolo de emergencia.",
      "El riesgo hídrico es un proxy y debe calibrarse con estaciones, percentiles y antecedentes locales; no equivale a SPI oficial.",
      "La aptitud vectorial no confirma mosquitos ni brote: requiere ovitrampas, vigilancia entomológica y casos humanos.",
      "Los focos térmicos provienen de NASA FIRMS; Open-Meteo sólo aporta el contexto meteorológico y atmosférico.",
    ],
  };

  return {
    methodologyVersion: SPACEAI_METHODOLOGY_VERSION,
    generatedAt,
    overallScore: round(overallScore, 1),
    overallLevel,
    overallLabel: LEVEL_LABELS[overallLevel],
    indices,
    alerts,
    indexSeries: overallIndexSeries(intel),
    hotspots,
    snapshot,
  };
}

export function levelLabel(level: SpaceAILevel): string {
  return LEVEL_LABELS[level];
}
