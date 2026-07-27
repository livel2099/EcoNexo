import * as SecureStore from "expo-secure-store";

import type {
  Alert,
  CitizenReport,
  DashboardBundle,
  Detection,
  Device,
  EnvironmentalSnapshotRecord,
  Kpi,
  ModuleEntitlement,
  Organization,
  Session,
} from "./types";

export const API_URL = (process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
export const DEMO_MODE = process.env.EXPO_PUBLIC_DEMO_MODE === "true";

const SESSION_KEY = "econexo_mobile_session_v1";
const REQUEST_TIMEOUT_MS = 15_000;

export interface RegisterInput {
  organization_name: string;
  vertical: "municipio" | "forestal" | "energetica";
  municipality?: string;
  department?: string;
  name: string;
  email: string;
  password: string;
  terms_accepted: boolean;
  legal_version?: string;
}

export interface GoogleAuthInput {
  credential: string;
  mode: "login" | "register";
  organization_name?: string;
  vertical?: "municipio" | "forestal" | "energetica";
  municipality?: string;
  department?: string;
  terms_accepted?: boolean;
  legal_version?: string;
}

export interface AlertShareInput {
  channel: "whatsapp" | "telegram" | "copiar" | "email" | "otro";
  audience: "medios" | "organizacion" | "laboratorio" | "emergencia" | "publico" | "otro";
  title: string;
  message: string;
  module_key: "core" | "fire_smoke" | "forestry_pests";
  snapshot_id?: string | null;
  alert_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface MobileReportInput {
  type: "humo" | "incendio" | "inundacion" | "vertido" | "otro";
  description: string;
  lat: number;
  lon: number;
  photo?: {
    uri: string;
    fileName?: string | null;
    mimeType?: string | null;
  } | null;
}

function buildDemoSession(email = "demo@misiones.econexo.app"): Session {
  return {
    access_token: "demo-mobile-token",
    token_type: "bearer",
    org_id: "00000000-0000-4000-8000-000000000001",
    role: "admin",
    name: "Operador EcoNexo",
    email,
    avatar_url: null,
    auth_provider: "password",
    is_new_user: false,
  };
}

const demoOrg: Organization = {
  id: "00000000-0000-4000-8000-000000000001",
  name: "EcoNexo Misiones",
  slug: "econexo-misiones",
  vertical: "forestal",
  primary_color: "#35e6df",
  baseline_response_s: 1800,
  province: "Misiones",
  department: "Capital",
  municipality: "Posadas",
  territory_scope: "provincial",
};

function nowMinus(minutes: number): string {
  return new Date(Date.now() - minutes * 60_000).toISOString();
}

const demoDevices: Device[] = [
  {
    id: "10000000-0000-4000-8000-000000000001",
    name: "Nodo Selva 01",
    external_id: "ECX-SELVA-01",
    lat: -27.3621,
    lon: -55.9007,
    status: "online",
    battery: 87,
    rssi: -63,
    tags: ["humo", "temperatura", "humedad"],
    last_seen: nowMinus(3),
  },
  {
    id: "10000000-0000-4000-8000-000000000002",
    name: "Nodo Ribera 02",
    external_id: "ECX-RIBERA-02",
    lat: -27.4109,
    lon: -55.9441,
    status: "online",
    battery: 73,
    rssi: -71,
    tags: ["nivel", "humedad"],
    last_seen: nowMinus(8),
  },
];

const demoAlerts: Alert[] = [
  {
    id: "20000000-0000-4000-8000-000000000001",
    type: "incendio",
    severity: "alta",
    status: "activa",
    lat: -27.391,
    lon: -55.858,
    confidence: 0.79,
    title: "Señal térmica para verificar",
    detected_at: nowMinus(26),
    acknowledged_at: null,
    resolved_at: null,
    sources: [{ source_type: "satelite", ref_id: null, weight: 0.75, detail: { source: "VIIRS" } }],
  },
  {
    id: "20000000-0000-4000-8000-000000000002",
    type: "calidad_aire",
    severity: "media",
    status: "activa",
    lat: -27.367,
    lon: -55.896,
    confidence: 0.68,
    title: "Partículas en aumento",
    detected_at: nowMinus(51),
    acknowledged_at: null,
    resolved_at: null,
    sources: [{ source_type: "modelo", ref_id: null, weight: 0.65, detail: { source: "CAMS" } }],
  },
];

const demoDetections: Detection[] = [
  {
    id: "30000000-0000-4000-8000-000000000001",
    source: "NASA FIRMS / VIIRS",
    lat: -27.391,
    lon: -55.858,
    brightness: 338.4,
    confidence: 0.79,
    frp: 12.8,
    acquired_at: nowMinus(26),
  },
  {
    id: "30000000-0000-4000-8000-000000000002",
    source: "NASA FIRMS / MODIS",
    lat: -27.477,
    lon: -55.973,
    brightness: 321.1,
    confidence: 0.61,
    frp: 7.3,
    acquired_at: nowMinus(143),
  },
];

const demoReports: CitizenReport[] = [
  {
    id: "40000000-0000-4000-8000-000000000001",
    type: "humo",
    description: "Se observa una columna fina de humo hacia el este.",
    photo_url: null,
    lat: -27.374,
    lon: -55.882,
    status: "pendiente",
    correlation_score: 0.72,
    reputation_score: 0.91,
    created_at: nowMinus(34),
  },
];

const demoModules: ModuleEntitlement[] = [
  {
    module_key: "core",
    status: "active",
    plan_name: "Plataforma EcoNexo",
    starts_at: nowMinus(5000),
    expires_at: null,
    config: {},
    available: true,
  },
  {
    module_key: "fire_smoke",
    status: "trial",
    plan_name: "Focos de incendio forestal y humo",
    starts_at: nowMinus(5000),
    expires_at: new Date(Date.now() + 30 * 86_400_000).toISOString(),
    config: { plain_language: true, human_approval_required: true, emergency_number: "911" },
    available: true,
  },
];

const demoSnapshot: EnvironmentalSnapshotRecord = {
  id: "50000000-0000-4000-8000-000000000001",
  org_id: demoOrg.id,
  created_by: null,
  origin: "mobile-demo",
  activated_alerts: 0,
  created_at: nowMinus(10),
  snapshot: {
    methodology_version: "SpaceAI v1.0 / EcoNexo 0.3",
    generated_at: nowMinus(10),
    latitude: -27.3621,
    longitude: -55.9007,
    overall_score: 48,
    overall_level: "R2",
    overall_label: "Alerta preventiva",
    observations: { pm25: 22.4, humidity: 44, wind_speed: 17.2, soil_moisture: 0.16 },
    indices: [
      {
        id: "fire",
        label: "Incendio y humo",
        level: "R3",
        score: 68,
        value: 68,
        unit: "score",
        status: "Condiciones de propagación y señal térmica a verificar",
        source: "FIRMS + Open-Meteo + CAMS",
        confidence: 0.76,
        action: "Verificar en terreno y mantener comunicación preventiva.",
        health_impacts: ["Irritación respiratoria", "Riesgo para personas con asma"],
        evidence: ["2 señales térmicas en 48 h", "Suelo seco", "Viento moderado"],
        formula: "Score_i = severidad_i × persistencia_i × confiabilidad_i",
        relative_exceedance_pct: 149,
        weighted_contribution: 14.2,
      },
      {
        id: "air",
        label: "Calidad del aire",
        level: "R2",
        score: 48,
        value: 22.4,
        unit: "µg/m³ PM2.5",
        status: "Por encima de la referencia sanitaria de 24 h",
        source: "CAMS",
        confidence: 0.67,
        action: "Reducir exposición de grupos sensibles si persiste.",
        health_impacts: ["Irritación", "Exacerbación respiratoria"],
        evidence: ["PM2.5 estimado: 22.4 µg/m³"],
        formula: "Excedencia = valor observado / referencia × 100",
        relative_exceedance_pct: 149.3,
        weighted_contribution: 8.6,
      },
    ],
    alerts: [
      {
        id: "fire-demo",
        domain: "fire",
        level: "R3",
        severity: "alta",
        title: "Señal térmica y ambiente seco",
        summary: "Hay una combinación que merece verificación, sin confirmación oficial de incendio.",
        action: "Confirmar visualmente, no acercarse y llamar al 911 si hay fuego o humo visible.",
        source: "FIRMS + Open-Meteo",
        confidence: 0.76,
      },
    ],
    hotspots: {
      count_48h: 2,
      high_confidence_count_48h: 1,
      maximum_frp_mw: 12.8,
      nearest_distance_km: 5.1,
    },
    sources: { weather: "Open-Meteo", air: "CAMS", fire: "NASA FIRMS" },
    limitations: [
      "Una señal térmica satelital no confirma por sí sola un incendio.",
      "La lectura debe validarse con observación de terreno y fuentes oficiales.",
    ],
  },
};

function demoBundle(): DashboardBundle {
  return {
    org: demoOrg,
    kpi: {
      detection_time_s: 162,
      detection_target_s: 300,
      model_precision: 0.88,
      precision_target: 0.85,
      valid_reports_rate: 0.81,
      valid_reports_target: 0.7,
      response_time_reduction: 0.44,
      response_reduction_target: 0.4,
      global_status: "atencion",
      active_alerts: 2,
    },
    devices: demoDevices,
    alerts: demoAlerts,
    detections: demoDetections,
    reports: demoReports,
    modules: demoModules,
    latestSnapshot: demoSnapshot,
  };
}

export async function saveSession(session: Session): Promise<void> {
  await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(session));
}

export async function loadSession(): Promise<Session | null> {
  const raw = await SecureStore.getItemAsync(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    await clearSession();
    return null;
  }
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(SESSION_KEY);
}

function timeoutSignal(timeoutMs = REQUEST_TIMEOUT_MS): { signal: AbortSignal; clear: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return { signal: controller.signal, clear: () => clearTimeout(timer) };
}

async function parseError(response: Response, fallback: string): Promise<Error> {
  try {
    const body = await response.json() as { detail?: string | Array<{ msg?: string }> };
    if (typeof body.detail === "string") return new Error(body.detail);
    if (Array.isArray(body.detail)) {
      const messages = body.detail.map((item) => item.msg).filter(Boolean);
      if (messages.length) return new Error(messages.join(" · "));
    }
  } catch {
    // La respuesta puede no contener JSON.
  }
  return new Error(`${fallback} (${response.status})`);
}

async function request<T>(path: string, init: RequestInit = {}, token?: string, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  const timeout = timeoutSignal(timeoutMs);
  const headers = new Headers(init.headers || {});
  headers.set("Accept", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  try {
    const response = await fetch(`${API_URL}${path}`, { ...init, headers, signal: timeout.signal });
    if (!response.ok) throw await parseError(response, `No se pudo completar ${path}`);
    if (response.status === 204) return undefined as T;
    return await response.json() as T;
  } catch (cause) {
    if (cause instanceof Error && cause.name === "AbortError") {
      throw new Error(`La API no respondió a tiempo en ${API_URL}.`);
    }
    if (cause instanceof Error) throw cause;
    throw new Error(`No se pudo conectar con EcoNexo en ${API_URL}.`);
  } finally {
    timeout.clear();
  }
}

export async function apiHealth(): Promise<boolean> {
  if (DEMO_MODE) return true;
  try {
    await request<{ status: string }>("/health", {}, undefined, 5_000);
    return true;
  } catch {
    return false;
  }
}

export async function login(email: string, password: string): Promise<Session> {
  if (DEMO_MODE) return buildDemoSession(email);
  return request<Session>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });
}

export async function register(input: RegisterInput): Promise<Session> {
  if (DEMO_MODE) return { ...buildDemoSession(input.email), name: input.name, is_new_user: true };
  return request<Session>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, legal_version: input.legal_version || "2026-07-23" }),
  });
}

export async function authenticateGoogle(input: GoogleAuthInput): Promise<Session> {
  if (DEMO_MODE) return { ...buildDemoSession("google.demo@econexo.app"), auth_provider: "google" };
  return request<Session>("/auth/google", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function getDashboardBundle(session: Session): Promise<DashboardBundle> {
  if (DEMO_MODE) return demoBundle();
  const token = session.access_token;
  const [org, kpi, devices, alerts, detections, reports, modules, snapshot] = await Promise.all([
    request<Organization>("/orgs/me", {}, token),
    request<Kpi>("/kpis", {}, token),
    request<Device[]>("/devices", {}, token),
    request<Alert[]>("/alerts", {}, token),
    request<Detection[]>("/satellite/detections?hours=48", {}, token),
    request<CitizenReport[]>("/reports", {}, token),
    request<ModuleEntitlement[]>("/modules/me", {}, token),
    request<EnvironmentalSnapshotRecord>("/environment/snapshots/latest", {}, token).catch(() => null),
  ]);
  return { org, kpi, devices, alerts, detections, reports, modules, latestSnapshot: snapshot };
}

export async function submitInternalReport(session: Session, input: MobileReportInput): Promise<CitizenReport> {
  if (DEMO_MODE) {
    return {
      id: `demo-report-${Date.now()}`,
      type: input.type,
      description: input.description || null,
      photo_url: input.photo?.uri || null,
      lat: input.lat,
      lon: input.lon,
      status: "pendiente",
      correlation_score: 0.64,
      reputation_score: 1,
      created_at: new Date().toISOString(),
    };
  }
  const form = new FormData();
  form.append("type", input.type);
  form.append("description", input.description.trim());
  form.append("lat", String(input.lat));
  form.append("lon", String(input.lon));
  if (input.photo) {
    form.append("photo", {
      uri: input.photo.uri,
      name: input.photo.fileName || `econexo-${Date.now()}.jpg`,
      type: input.photo.mimeType || "image/jpeg",
    } as unknown as Blob);
  }
  return request<CitizenReport>("/reports/internal", { method: "POST", body: form }, session.access_token, 30_000);
}

export async function registerAlertShare(session: Session, input: AlertShareInput): Promise<{ id: string; created_at: string }> {
  if (DEMO_MODE) return { id: `demo-share-${Date.now()}`, created_at: new Date().toISOString() };
  return request<{ id: string; created_at: string }>("/modules/alert-share", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, metadata: input.metadata || {} }),
  }, session.access_token);
}

export async function actOnAlert(
  session: Session,
  alertId: string,
  action: "confirmar" | "descartar" | "escalar" | "asignar",
): Promise<Alert> {
  if (DEMO_MODE) {
    const alert = demoAlerts.find((item) => item.id === alertId) || demoAlerts[0];
    return { ...alert, status: action === "descartar" ? "descartada" : action === "confirmar" ? "confirmada" : "escalada" };
  }
  return request<Alert>(`/alerts/${alertId}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  }, session.access_token);
}
