const FORECAST_ENDPOINT = process.env.NEXT_PUBLIC_OPEN_METEO_FORECAST_URL
  || "https://api.open-meteo.com/v1/forecast";
const AIR_QUALITY_ENDPOINT = process.env.NEXT_PUBLIC_OPEN_METEO_AIR_URL
  || "https://air-quality-api.open-meteo.com/v1/air-quality";
const FLOOD_ENDPOINT = process.env.NEXT_PUBLIC_OPEN_METEO_FLOOD_URL
  || "https://flood-api.open-meteo.com/v1/flood";
const CACHE_PREFIX = "econexo_earth_intel_v2";
const DEFAULT_CACHE_TTL_MINUTES = 10;

export type EarthSourceState = "live" | "unavailable" | "disabled";

export interface EarthIntelOptions {
  weatherEnabled?: boolean;
  airQualityEnabled?: boolean;
  floodEnabled?: boolean;
  cacheTtlMinutes?: number;
}

interface NormalizedEarthIntelOptions {
  weatherEnabled: boolean;
  airQualityEnabled: boolean;
  floodEnabled: boolean;
  cacheTtlMinutes: number;
}

function normalizeOptions(options?: EarthIntelOptions): NormalizedEarthIntelOptions {
  return {
    weatherEnabled: options?.weatherEnabled ?? true,
    airQualityEnabled: options?.airQualityEnabled ?? true,
    floodEnabled: options?.floodEnabled ?? true,
    cacheTtlMinutes: Math.min(180, Math.max(2, options?.cacheTtlMinutes ?? DEFAULT_CACHE_TTL_MINUTES)),
  };
}

export interface EarthSeries {
  weatherTime: string[];
  currentWeatherIndex: number;
  temperature: Array<number | null>;
  humidity: Array<number | null>;
  precipitation: Array<number | null>;
  precipitationProbability: Array<number | null>;
  windSpeed: Array<number | null>;
  windGusts: Array<number | null>;
  soilMoisture: Array<number | null>;
  vapourPressureDeficit: Array<number | null>;
  evapotranspiration: Array<number | null>;
  airTime: string[];
  currentAirIndex: number;
  pm25: Array<number | null>;
  pm10: Array<number | null>;
  usAqi: Array<number | null>;
  uvIndex: Array<number | null>;
  aerosolOpticalDepth: Array<number | null>;
  dust: Array<number | null>;
}

export interface EarthDaily {
  time: string[];
  temperatureMax: Array<number | null>;
  temperatureMin: Array<number | null>;
  apparentTemperatureMax: Array<number | null>;
  precipitationSum: Array<number | null>;
  precipitationProbabilityMax: Array<number | null>;
  windGustsMax: Array<number | null>;
  evapotranspiration: Array<number | null>;
}

export interface EarthFlood {
  time: string[];
  currentIndex: number;
  riverDischarge: Array<number | null>;
  riverDischargeMean: Array<number | null>;
  riverDischargeMax: Array<number | null>;
  riverDischargeP75: Array<number | null>;
  currentDischarge: number | null;
  baselineMedian: number | null;
  forecastMax: number | null;
  referenceP75: number | null;
}

export interface EarthIntel {
  latitude: number;
  longitude: number;
  timezone: string;
  weather: {
    observedAt: string;
    temperature: number | null;
    apparentTemperature: number | null;
    humidity: number | null;
    precipitation: number | null;
    weatherCode: number | null;
    cloudCover: number | null;
    visibility: number | null;
    windSpeed: number | null;
    windDirection: number | null;
    windGusts: number | null;
    soilMoisture: number | null;
    vapourPressureDeficit: number | null;
    evapotranspiration: number | null;
  };
  atmosphere: {
    observedAt: string;
    pm25: number | null;
    pm10: number | null;
    carbonMonoxide: number | null;
    nitrogenDioxide: number | null;
    sulphurDioxide: number | null;
    ozone: number | null;
    aerosolOpticalDepth: number | null;
    dust: number | null;
    uvIndex: number | null;
    usAqi: number | null;
  };
  daily: EarthDaily;
  flood: EarthFlood;
  series: EarthSeries;
  sources: {
    weather: EarthSourceState;
    airQuality: EarthSourceState;
    flood: EarthSourceState;
  };
  fetchedAt: string;
  stale: boolean;
}

interface OpenMeteoPayload {
  latitude?: number;
  longitude?: number;
  timezone?: string;
  current?: Record<string, unknown>;
  hourly?: Record<string, unknown>;
  daily?: Record<string, unknown>;
}

interface CachedEarthIntel {
  savedAt: number;
  value: EarthIntel;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringOrEmpty(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function numberSeries(value: unknown): Array<number | null> {
  if (!Array.isArray(value)) return [];
  return value.map(numberOrNull);
}

function stringSeries(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map(stringOrEmpty);
}

function closestIndex(times: string[], target: string): number {
  if (!times.length) return -1;
  const exact = times.indexOf(target);
  if (exact >= 0) return exact;
  const targetMs = new Date(target).getTime();
  if (!Number.isFinite(targetMs)) return Math.max(0, times.length - 1);
  let best = 0;
  let distance = Number.POSITIVE_INFINITY;
  times.forEach((time, index) => {
    const value = new Date(time).getTime();
    const nextDistance = Math.abs(value - targetMs);
    if (Number.isFinite(nextDistance) && nextDistance < distance) {
      best = index;
      distance = nextDistance;
    }
  });
  return best;
}

function maximum(values: Array<number | null>): number | null {
  const clean = values.filter((value): value is number => value != null);
  return clean.length ? Math.max(...clean) : null;
}

function median(values: Array<number | null>): number | null {
  const clean = values.filter((value): value is number => value != null).sort((a, b) => a - b);
  if (!clean.length) return null;
  const middle = Math.floor(clean.length / 2);
  return clean.length % 2 ? clean[middle] : (clean[middle - 1] + clean[middle]) / 2;
}

function cacheKey(latitude: number, longitude: number, options: NormalizedEarthIntelOptions): string {
  const sourceMask = `${Number(options.weatherEnabled)}${Number(options.airQualityEnabled)}${Number(options.floodEnabled)}`;
  return `${CACHE_PREFIX}:${latitude.toFixed(3)}:${longitude.toFixed(3)}:${sourceMask}`;
}

function readCache(latitude: number, longitude: number, options: NormalizedEarthIntelOptions): CachedEarthIntel | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(cacheKey(latitude, longitude, options));
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CachedEarthIntel;
  } catch {
    window.localStorage.removeItem(cacheKey(latitude, longitude, options));
    return null;
  }
}

function writeCache(value: EarthIntel, options: NormalizedEarthIntelOptions): void {
  if (typeof window === "undefined") return;
  const payload: CachedEarthIntel = { savedAt: Date.now(), value };
  window.localStorage.setItem(cacheKey(value.latitude, value.longitude, options), JSON.stringify(payload));
}

function forecastUrl(latitude: number, longitude: number): string {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    current: [
      "temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation",
      "weather_code", "cloud_cover", "visibility", "wind_speed_10m", "wind_direction_10m",
      "wind_gusts_10m", "soil_moisture_0_to_1cm", "vapour_pressure_deficit",
      "et0_fao_evapotranspiration",
    ].join(","),
    hourly: [
      "temperature_2m", "relative_humidity_2m", "precipitation", "precipitation_probability",
      "wind_speed_10m", "wind_gusts_10m", "soil_moisture_0_to_1cm",
      "vapour_pressure_deficit", "et0_fao_evapotranspiration",
    ].join(","),
    daily: [
      "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max",
      "precipitation_sum", "precipitation_probability_max", "wind_gusts_10m_max",
      "et0_fao_evapotranspiration",
    ].join(","),
    past_days: "7",
    forecast_days: "7",
    timezone: "auto",
  });
  return `${FORECAST_ENDPOINT}?${params}`;
}

function airQualityUrl(latitude: number, longitude: number): string {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    current: [
      "pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide",
      "ozone", "aerosol_optical_depth", "dust", "uv_index", "us_aqi",
    ].join(","),
    hourly: "pm2_5,pm10,us_aqi,uv_index,aerosol_optical_depth,dust",
    past_days: "1",
    forecast_days: "5",
    timezone: "auto",
    domains: "cams_global",
  });
  return `${AIR_QUALITY_ENDPOINT}?${params}`;
}

function floodUrl(latitude: number, longitude: number): string {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    daily: "river_discharge,river_discharge_mean,river_discharge_max,river_discharge_p75",
    past_days: "30",
    forecast_days: "14",
    timezone: "auto",
  });
  return `${FLOOD_ENDPOINT}?${params}`;
}

async function requestJson(url: string, signal?: AbortSignal): Promise<OpenMeteoPayload> {
  const response = await fetch(url, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Open-Meteo respondió ${response.status}`);
  return response.json() as Promise<OpenMeteoPayload>;
}

function emptyPayload(): OpenMeteoPayload {
  return { current: {}, hourly: {}, daily: {} };
}

function resultValue(result: PromiseSettledResult<OpenMeteoPayload>): OpenMeteoPayload {
  return result.status === "fulfilled" ? result.value : emptyPayload();
}

export function futureSeries(values: Array<number | null>, currentIndex: number, hours = 12): Array<number | null> {
  if (!values.length) return [];
  const start = currentIndex >= 0 ? currentIndex : 0;
  return values.slice(start, start + hours);
}

export async function fetchEarthIntel(
  latitude: number,
  longitude: number,
  signal?: AbortSignal,
  force = false,
  options?: EarthIntelOptions,
): Promise<EarthIntel> {
  const sourceOptions = normalizeOptions(options);
  const cached = readCache(latitude, longitude, sourceOptions);
  if (!force && cached && Date.now() - cached.savedAt < sourceOptions.cacheTtlMinutes * 60_000) {
    return { ...cached.value, stale: false };
  }

  const requests: Array<Promise<OpenMeteoPayload>> = [
    sourceOptions.weatherEnabled ? requestJson(forecastUrl(latitude, longitude), signal) : Promise.resolve(emptyPayload()),
    sourceOptions.airQualityEnabled ? requestJson(airQualityUrl(latitude, longitude), signal) : Promise.resolve(emptyPayload()),
    sourceOptions.floodEnabled ? requestJson(floodUrl(latitude, longitude), signal) : Promise.resolve(emptyPayload()),
  ];
  const enabled = [sourceOptions.weatherEnabled, sourceOptions.airQualityEnabled, sourceOptions.floodEnabled];
  const results = await Promise.allSettled(requests);

  if (signal?.aborted) throw new DOMException("Solicitud cancelada", "AbortError");
  const enabledSources = enabled.filter(Boolean).length;
  const failedEnabledSources = results.filter((result, index) => enabled[index] && result.status === "rejected").length;
  if (enabledSources > 0 && failedEnabledSources === enabledSources) {
    if (cached) return { ...cached.value, stale: true };
    const first = results.find((result, index): result is PromiseRejectedResult => enabled[index] && result.status === "rejected");
    throw first?.reason instanceof Error ? first.reason : new Error("Fuentes ambientales no disponibles");
  }

  const forecast = resultValue(results[0]);
  const air = resultValue(results[1]);
  const floodPayload = resultValue(results[2]);
  const weather = forecast.current || {};
  const atmosphere = air.current || {};
  const weatherHourly = forecast.hourly || {};
  const airHourly = air.hourly || {};
  const weatherDaily = forecast.daily || {};
  const floodDaily = floodPayload.daily || {};

  const weatherTime = stringSeries(weatherHourly.time);
  const airTime = stringSeries(airHourly.time);
  const floodTime = stringSeries(floodDaily.time);
  const weatherObservedAt = stringOrEmpty(weather.time);
  const airObservedAt = stringOrEmpty(atmosphere.time);
  const today = new Date().toISOString().slice(0, 10);
  const floodCurrentIndex = closestIndex(floodTime, today);
  const floodDischarge = numberSeries(floodDaily.river_discharge);
  const historicalDischarge = floodCurrentIndex > 0
    ? floodDischarge.slice(Math.max(0, floodCurrentIndex - 30), floodCurrentIndex)
    : [];
  const futureDischarge = floodCurrentIndex >= 0
    ? floodDischarge.slice(floodCurrentIndex, floodCurrentIndex + 15)
    : floodDischarge;
  const floodMax = numberSeries(floodDaily.river_discharge_max);
  const floodP75 = numberSeries(floodDaily.river_discharge_p75);
  const futureMaxValues = floodCurrentIndex >= 0
    ? floodMax.slice(floodCurrentIndex, floodCurrentIndex + 15)
    : floodMax;
  const futureP75Values = floodCurrentIndex >= 0
    ? floodP75.slice(floodCurrentIndex, floodCurrentIndex + 15)
    : floodP75;

  const value: EarthIntel = {
    latitude: numberOrNull(forecast.latitude) ?? numberOrNull(air.latitude) ?? numberOrNull(floodPayload.latitude) ?? latitude,
    longitude: numberOrNull(forecast.longitude) ?? numberOrNull(air.longitude) ?? numberOrNull(floodPayload.longitude) ?? longitude,
    timezone: stringOrEmpty(forecast.timezone) || stringOrEmpty(air.timezone) || stringOrEmpty(floodPayload.timezone) || "auto",
    weather: {
      observedAt: weatherObservedAt,
      temperature: numberOrNull(weather.temperature_2m),
      apparentTemperature: numberOrNull(weather.apparent_temperature),
      humidity: numberOrNull(weather.relative_humidity_2m),
      precipitation: numberOrNull(weather.precipitation),
      weatherCode: numberOrNull(weather.weather_code),
      cloudCover: numberOrNull(weather.cloud_cover),
      visibility: numberOrNull(weather.visibility),
      windSpeed: numberOrNull(weather.wind_speed_10m),
      windDirection: numberOrNull(weather.wind_direction_10m),
      windGusts: numberOrNull(weather.wind_gusts_10m),
      soilMoisture: numberOrNull(weather.soil_moisture_0_to_1cm),
      vapourPressureDeficit: numberOrNull(weather.vapour_pressure_deficit),
      evapotranspiration: numberOrNull(weather.et0_fao_evapotranspiration),
    },
    atmosphere: {
      observedAt: airObservedAt,
      pm25: numberOrNull(atmosphere.pm2_5),
      pm10: numberOrNull(atmosphere.pm10),
      carbonMonoxide: numberOrNull(atmosphere.carbon_monoxide),
      nitrogenDioxide: numberOrNull(atmosphere.nitrogen_dioxide),
      sulphurDioxide: numberOrNull(atmosphere.sulphur_dioxide),
      ozone: numberOrNull(atmosphere.ozone),
      aerosolOpticalDepth: numberOrNull(atmosphere.aerosol_optical_depth),
      dust: numberOrNull(atmosphere.dust),
      uvIndex: numberOrNull(atmosphere.uv_index),
      usAqi: numberOrNull(atmosphere.us_aqi),
    },
    daily: {
      time: stringSeries(weatherDaily.time),
      temperatureMax: numberSeries(weatherDaily.temperature_2m_max),
      temperatureMin: numberSeries(weatherDaily.temperature_2m_min),
      apparentTemperatureMax: numberSeries(weatherDaily.apparent_temperature_max),
      precipitationSum: numberSeries(weatherDaily.precipitation_sum),
      precipitationProbabilityMax: numberSeries(weatherDaily.precipitation_probability_max),
      windGustsMax: numberSeries(weatherDaily.wind_gusts_10m_max),
      evapotranspiration: numberSeries(weatherDaily.et0_fao_evapotranspiration),
    },
    flood: {
      time: floodTime,
      currentIndex: floodCurrentIndex,
      riverDischarge: floodDischarge,
      riverDischargeMean: numberSeries(floodDaily.river_discharge_mean),
      riverDischargeMax: floodMax,
      riverDischargeP75: floodP75,
      currentDischarge: floodCurrentIndex >= 0 ? floodDischarge[floodCurrentIndex] ?? null : null,
      baselineMedian: median(historicalDischarge),
      forecastMax: maximum(futureMaxValues) ?? maximum(futureDischarge),
      referenceP75: median(futureP75Values),
    },
    series: {
      weatherTime,
      currentWeatherIndex: closestIndex(weatherTime, weatherObservedAt),
      temperature: numberSeries(weatherHourly.temperature_2m),
      humidity: numberSeries(weatherHourly.relative_humidity_2m),
      precipitation: numberSeries(weatherHourly.precipitation),
      precipitationProbability: numberSeries(weatherHourly.precipitation_probability),
      windSpeed: numberSeries(weatherHourly.wind_speed_10m),
      windGusts: numberSeries(weatherHourly.wind_gusts_10m),
      soilMoisture: numberSeries(weatherHourly.soil_moisture_0_to_1cm),
      vapourPressureDeficit: numberSeries(weatherHourly.vapour_pressure_deficit),
      evapotranspiration: numberSeries(weatherHourly.et0_fao_evapotranspiration),
      airTime,
      currentAirIndex: closestIndex(airTime, airObservedAt),
      pm25: numberSeries(airHourly.pm2_5),
      pm10: numberSeries(airHourly.pm10),
      usAqi: numberSeries(airHourly.us_aqi),
      uvIndex: numberSeries(airHourly.uv_index),
      aerosolOpticalDepth: numberSeries(airHourly.aerosol_optical_depth),
      dust: numberSeries(airHourly.dust),
    },
    sources: {
      weather: sourceOptions.weatherEnabled ? (results[0].status === "fulfilled" ? "live" : "unavailable") : "disabled",
      airQuality: sourceOptions.airQualityEnabled ? (results[1].status === "fulfilled" ? "live" : "unavailable") : "disabled",
      flood: sourceOptions.floodEnabled ? (results[2].status === "fulfilled" ? "live" : "unavailable") : "disabled",
    },
    fetchedAt: new Date().toISOString(),
    stale: false,
  };
  writeCache(value, sourceOptions);
  return value;
}
