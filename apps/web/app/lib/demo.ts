import type {
  AdminSummary,
  AdminUser,
  Alert,
  AuditEvent,
  Detection,
  Device,
  EnvironmentalSnapshot,
  EnvironmentalSnapshotRecord,
  EnvironmentalSourceSettings,
  ImpactReport,
  ImpactReportPublishResult,
  Kpi,
  ModuleEntitlement,
  AdminNotification,
  LicenseRequest,
  SubscriptionMe,
  SubscriptionPlan,
  SubscriptionPlanKey,
  Org,
  PublicImpactReport,
  Report,
  RiskZone,
  Rule,
  Session,
} from "./types";
import type { EmailRegisterInput, GoogleAuthInput, RegistrationPending } from "./api";

const DEMO_EMAIL = "admin@misiones.econexo.ar";
const DEMO_PASSWORD = "econexo123";
const STORAGE_KEY = "econexo_cloudflare_demo_v2";
const DEMO_ACCOUNT_KEY = "econexo_demo_account_v1";

interface DemoState {
  org: Org;
  alerts: Alert[];
  reports: Report[];
  rules: Rule[];
  impactReports: ImpactReport[];
  publicLinks: Record<string, string>;
  users: AdminUser[];
  zones: RiskZone[];
  sourceSettings: EnvironmentalSourceSettings;
  snapshots: EnvironmentalSnapshotRecord[];
  audit: AuditEvent[];
  notifications: AdminNotification[];
  licenseRequests: LicenseRequest[];
  subscriptionPlanKey: SubscriptionPlanKey;
}

const ORG: Org = {
  id: "org-misiones",
  name: "EcoNexo Misiones · Corredor Yabotí",
  slug: "econexo-misiones-yaboti",
  vertical: "forestal",
  primary_color: "#2E7D5B",
  baseline_response_s: 1440,
  province: "Misiones",
  department: "San Pedro",
  municipality: "San Pedro",
  territory_scope: "area_operativa",
};

function isoAgo(minutes: number): string {
  return new Date(Date.now() - minutes * 60_000).toISOString();
}

function initialDevices(): Device[] {
  const base = (device: Omit<Device, "marker_shape" | "telemetry_mode" | "zone_id" | "zone_name" | "pipeline_enabled" | "telemetry_config" | "last_pipeline_at" | "last_pipeline_status" | "latest_readings">, index: number): Device => ({
    ...device,
    marker_shape: (["square", "triangle", "circle"] as const)[index % 3],
    telemetry_mode: index < 4 ? "mqtt" : "manual",
    zone_id: index < 3 ? "zone-incendio-demo" : "zone-general-demo",
    zone_name: index < 3 ? "Anillo preventivo Mirador Este" : "Corredor Yabotí",
    pipeline_enabled: true,
    telemetry_config: { provider: index < 4 ? "mqtt" : "manual", demo: true },
    last_pipeline_at: isoAgo(5 + index),
    last_pipeline_status: device.status === "offline" ? "stale" : "ok",
    latest_readings: {
      temp: 25 + index * 3.4,
      humidity: Math.max(18, 76 - index * 9),
      soil_moisture: Math.max(12, 54 - index * 6),
      wind_gust: 14 + index * 7,
    },
  });

  return [
    base({
      id: "dev-norte", name: "Guardaparque Norte", external_id: "ESP32-FOR-001",
      lat: -26.789, lon: -54.469, status: "online", battery: 92, rssi: -61,
      tags: ["temperatura", "humo", "MQ-4"], last_seen: isoAgo(1),
    }, 0),
    base({
      id: "dev-arroyo", name: "Arroyo Verde", external_id: "ESP32-FOR-002",
      lat: -26.815, lon: -54.432, status: "online", battery: 78, rssi: -67,
      tags: ["humedad", "PM2.5"], last_seen: isoAgo(2),
    }, 1),
    base({
      id: "dev-mirador", name: "Mirador Este", external_id: "ESP32-FOR-003",
      lat: -26.837, lon: -54.401, status: "alerta", battery: 66, rssi: -73,
      tags: ["temperatura", "humo", "viento"], last_seen: isoAgo(1),
    }, 2),
    base({
      id: "dev-reserva", name: "Reserva Yabotí", external_id: "ESP32-FOR-004",
      lat: -26.862, lon: -54.474, status: "online", battery: 84, rssi: -58,
      tags: ["temperatura", "humedad"], last_seen: isoAgo(3),
    }, 3),
    base({
      id: "dev-oeste", name: "Puesto Oeste", external_id: "ESP32-FOR-005",
      lat: -26.806, lon: -54.507, status: "offline", battery: 19, rssi: -91,
      tags: ["PM2.5", "MQ-4"], last_seen: isoAgo(49),
    }, 4),
    base({
      id: "dev-ruta", name: "Acceso Ruta 12", external_id: "ESP32-FOR-006",
      lat: -26.846, lon: -54.526, status: "online", battery: 73, rssi: -69,
      tags: ["temperatura", "humo"], last_seen: isoAgo(4),
    }, 5),
  ];
}

function initialAlerts(): Alert[] {
  return [
    {
      id: "alert-foco-este", type: "incendio", severity: "critica", status: "activa",
      lat: -26.834, lon: -54.407, confidence: 0.92,
      title: "Posible foco de incendio con evidencia multifuente en Mirador Este", detected_at: isoAgo(7),
      acknowledged_at: null, resolved_at: null,
      sources: [
        { source_type: "sensor", ref_id: "dev-mirador", weight: 0.45, detail: { temp: 46.8, mq4: 812 } },
        { source_type: "satelite", ref_id: "det-firms-1", weight: 0.35, detail: { brightness: 331.4 } },
        { source_type: "ciudadano", ref_id: "report-humo-1", weight: 0.20, detail: { type: "humo" } },
      ],
    },
    {
      id: "alert-pm25", type: "calidad_aire", severity: "alta", status: "activa",
      lat: -26.813, lon: -54.435, confidence: 0.78,
      title: "PM2.5 elevado en corredor Arroyo Verde", detected_at: isoAgo(24),
      acknowledged_at: null, resolved_at: null,
      sources: [
        { source_type: "sensor", ref_id: "dev-arroyo", weight: 0.70, detail: { pm25: 89 } },
        { source_type: "satelite", ref_id: "det-firms-2", weight: 0.30, detail: { distance_km: 3.2 } },
      ],
    },
    {
      id: "alert-bateria", type: "infraestructura", severity: "media", status: "activa",
      lat: -26.806, lon: -54.507, confidence: 0.68,
      title: "Nodo Puesto Oeste sin heartbeat", detected_at: isoAgo(49),
      acknowledged_at: null, resolved_at: null,
      sources: [
        { source_type: "sensor", ref_id: "dev-oeste", weight: 1, detail: { battery: 19 } },
      ],
    },
  ];
}

function initialReports(): Report[] {
  return [
    {
      id: "report-humo-1", type: "humo", description: "Columna de humo visible desde el sendero este.",
      photo_url: null, lat: -26.832, lon: -54.410, status: "pendiente",
      correlation_score: 0.89, reputation_score: 0.82, created_at: isoAgo(9),
    },
    {
      id: "report-olor-1", type: "otro", description: "Olor fuerte cerca del arroyo.",
      photo_url: null, lat: -26.816, lon: -54.436, status: "verificado",
      correlation_score: 0.71, reputation_score: 0.76, created_at: isoAgo(81),
    },
    {
      id: "report-falsa-1", type: "incendio", description: "Posible fuego junto a la ruta.",
      photo_url: null, lat: -26.851, lon: -54.522, status: "rechazado",
      correlation_score: 0.18, reputation_score: 0.44, created_at: isoAgo(193),
    },
  ];
}

function initialRules(): Rule[] {
  return [
    {
      id: "rule-fire", name: "Incendio multifuente", alert_type: "incendio",
      conditions: [{ variable: "temp", operator: ">=", threshold: 44 }, { variable: "mq4", operator: ">", threshold: 650 }],
      condition_logic: "AND", window_seconds: 300, severity: "critica", require_satellite: true, enabled: true,
    },
    {
      id: "rule-air", name: "Calidad de aire degradada", alert_type: "calidad_aire",
      conditions: [{ variable: "pm25", operator: ">", threshold: 55 }],
      condition_logic: "AND", window_seconds: 600, severity: "alta", require_satellite: false, enabled: true,
    },
    {
      id: "rule-heartbeat", name: "Nodo sin heartbeat", alert_type: "infraestructura",
      conditions: [{ variable: "heartbeat_min", operator: ">", threshold: 15 }],
      condition_logic: "AND", window_seconds: 900, severity: "media", require_satellite: false, enabled: true,
    },
  ];
}

function dateAgo(days: number): string {
  const value = new Date(Date.now() - days * 86_400_000);
  return value.toISOString().slice(0, 10);
}

function initialImpactReports(): ImpactReport[] {
  const now = new Date().toISOString();
  return [{
    id: "impact-demo-1",
    org_id: ORG.id,
    org_name: ORG.name,
    report_kind: "desempeno_operativo",
    environmental_snapshot_id: null,
    methodology_version: null,
    official_metadata: {},
    title: "Informe de desempeño ambiental y respuesta temprana",
    recipient_type: "programa_organismo",
    recipient_name: "Programa Provincial de Vigilancia Ambiental",
    period_start: dateAgo(30),
    period_end: dateAgo(0),
    executive_summary: "EcoNexo consolido sensores IoT, observacion satelital y reportes ciudadanos para priorizar incidentes y reducir el tiempo de respuesta en el territorio monitoreado.",
    metrics: {
      devices_total: 6, devices_online: 5, alerts_total: 7, critical_alerts: 2,
      alerts_confirmed: 5, model_precision: 0.89, average_detection_seconds: 42,
      average_response_seconds: 778, response_time_reduction: 0.46,
      citizen_reports_total: 11, citizen_reports_verified: 8, valid_reports_rate: 0.73,
    },
    highlights: [
      "Disponibilidad de la red de sensores: 83%.",
      "Tiempo medio de deteccion: 42 segundos.",
      "Reduccion estimada del tiempo de respuesta frente al baseline: 46%.",
      "Ocho reportes ciudadanos fueron verificados durante el periodo.",
    ],
    recommendations: [
      "Reemplazar la bateria del nodo Puesto Oeste y revisar cobertura de red.",
      "Formalizar el protocolo de escalamiento para alertas criticas multifuente.",
      "Validar trimestralmente las metricas con una fuente independiente.",
    ],
    status: "borrador", published_at: null, created_at: now, updated_at: now,
  }];
}

function initialUsers(): AdminUser[] {
  const now = new Date().toISOString();
  return [
    { id: "user-demo-admin", name: "Administración EcoNexo Misiones", email: DEMO_EMAIL, role: "admin", is_active: true, auth_provider: "password", email_verified: true, avatar_url: null, last_login_at: now, created_at: now, updated_at: now },
    { id: "user-demo-operator", name: "Operador Territorial", email: "operador@misiones.econexo.ar", role: "operador", is_active: true, auth_provider: "password", email_verified: false, avatar_url: null, last_login_at: isoAgo(85), created_at: isoAgo(24000), updated_at: isoAgo(85) },
  ];
}

function initialZones(): RiskZone[] {
  const now = new Date().toISOString();
  return [
    { id: "zone-yaboti", name: "Corredor Yabotí", kind: "incendio", lat: -26.86, lon: -54.47, radius_m: 8500, created_at: now, updated_at: now },
    { id: "zone-arroyo", name: "Microcuenca Arroyo Verde", kind: "hidrica", lat: -26.815, lon: -54.432, radius_m: 3200, created_at: now, updated_at: now },
  ];
}

function initialSourceSettings(): EnvironmentalSourceSettings {
  return {
    org_id: ORG.id,
    default_latitude: -26.82,
    default_longitude: -54.45,
    open_meteo_enabled: true,
    air_quality_enabled: true,
    flood_enabled: true,
    firms_enabled: true,
    copernicus_enabled: true,
    copernicus_use_system_default: true,
    copernicus_wms_url: null,
    copernicus_true_color_layer: "TRUE_COLOR",
    copernicus_ndvi_layer: "NDVI",
    copernicus_moisture_layer: "NDMI",
    copernicus_burn_layer: "NBR",
    forestry_pest_enabled: true,
    sinarame_radar_enabled: true,
    refresh_minutes: 10,
    fire_radius_km: 50,
    operational_alert_min_level: "R3",
    auto_activate_alerts: false,
    firms_map_key_configured: false,
    copernicus_configured: false,
    copernicus_provider: "none",
    copernicus_process_configured: false,
    copernicus_wms_configured: false,
    copernicus_system_default: true,
    copernicus_effective_wms_url: null,
    copernicus_last_test_at: null,
    copernicus_last_test_ok: null,
    copernicus_last_error: null,
    copernicus_available_layers: [],
    updated_at: new Date().toISOString(),
  };
}

function initialAudit(): AuditEvent[] {
  return [{
    id: "audit-demo-init", user_id: "user-demo-admin", actor_name: "Administración EcoNexo Misiones",
    action: "bootstrap", resource: "demo_environment", resource_id: null,
    metadata: { mode: "cloudflare", dataset: "v3" }, created_at: new Date().toISOString(),
  }];
}

function initialState(): DemoState {
  return {
    org: copy(ORG),
    alerts: initialAlerts(),
    reports: initialReports(),
    rules: initialRules(),
    impactReports: initialImpactReports(),
    publicLinks: {},
    users: initialUsers(),
    zones: initialZones(),
    sourceSettings: initialSourceSettings(),
    snapshots: [],
    audit: initialAudit(),
    notifications: [{
      id: "notification-demo-welcome", org_id: ORG.id, org_name: ORG.name,
      kind: "organization_registered", visibility: "both", severity: "success",
      title: "EcoNexo listo para operar", message: "La organización demo fue habilitada con un Piloto 8 semanas.",
      actor_user_id: "user-demo-admin", actor_email: DEMO_EMAIL,
      metadata: { provider: "demo", plan: "pilot_8_weeks" }, read: false, created_at: new Date().toISOString(),
    }],
    licenseRequests: [],
    subscriptionPlanKey: "pilot_8_weeks",
  };
}

function readState(): DemoState {
  if (typeof window === "undefined") return initialState();
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as Partial<DemoState>;
      const initial = initialState();
      const migrated: DemoState = {
        ...initial,
        ...parsed,
        org: { ...initial.org, ...(parsed.org || {}) },
        sourceSettings: { ...initial.sourceSettings, ...(parsed.sourceSettings || {}) },
        users: parsed.users || initial.users,
        zones: parsed.zones || initial.zones,
        snapshots: parsed.snapshots || initial.snapshots,
        audit: parsed.audit || initial.audit,
        notifications: parsed.notifications || initial.notifications,
        licenseRequests: parsed.licenseRequests || initial.licenseRequests,
        subscriptionPlanKey: parsed.subscriptionPlanKey || initial.subscriptionPlanKey,
      };
      writeState(migrated);
      return migrated;
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }
  const state = initialState();
  writeState(state);
  return state;
}

function writeState(state: DemoState): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }
}

function copy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function newId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

function pushAudit(state: DemoState, action: string, resource: string, resourceId: string | null, metadata: Record<string, unknown> = {}): void {
  state.audit.unshift({
    id: newId("audit"),
    user_id: "user-demo-admin",
    actor_name: "Administración EcoNexo Misiones",
    action,
    resource,
    resource_id: resourceId,
    metadata,
    created_at: new Date().toISOString(),
  });
  state.audit = state.audit.slice(0, 250);
}

function readings(deviceId: string, variable: string): { ts: string; value: number }[] {
  const bases: Record<string, number> = { temp: 29, humidity: 58, pm25: 21, mq4: 245, nivel: 1.8, turbidez: 13 };
  const amplitudes: Record<string, number> = { temp: 5.5, humidity: 12, pm25: 18, mq4: 105, nivel: 0.25, turbidez: 6 };
  const base = (bases[variable] ?? 20) + (deviceId === "dev-mirador" ? (variable === "temp" ? 11 : 2) : 0);
  const amplitude = amplitudes[variable] ?? 5;
  const offset = [...deviceId].reduce((sum, char) => sum + char.charCodeAt(0), 0) % 11;

  return Array.from({ length: 49 }, (_, index) => {
    const ageHours = 48 - index;
    const wave = Math.sin((index + offset) / 4.2) + Math.cos((index + offset) / 8.7) * 0.35;
    return {
      ts: new Date(Date.now() - ageHours * 3_600_000).toISOString(),
      value: Number((base + wave * amplitude).toFixed(2)),
    };
  });
}

function kpis(state: DemoState): Kpi {
  const active = state.alerts.filter((alert) => !["descartada", "resuelta"].includes(alert.status));
  const hasCritical = active.some((alert) => alert.severity === "critica");
  const hasHigh = active.some((alert) => alert.severity === "alta");
  const moderated = state.reports.filter((report) => report.status !== "pendiente");
  const valid = moderated.filter((report) => report.status === "verificado").length;

  return {
    detection_time_s: 42,
    detection_target_s: 300,
    model_precision: 0.89,
    precision_target: 0.85,
    valid_reports_rate: moderated.length ? valid / moderated.length : null,
    valid_reports_target: 0.70,
    response_time_reduction: 0.46,
    response_reduction_target: 0.40,
    global_status: hasCritical ? "critico" : hasHigh ? "atencion" : "normal",
    active_alerts: active.length,
  };
}

interface DemoAccount {
  email: string;
  password_digest: string;
  name: string;
  org_id: string;
}

async function demoPasswordDigest(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (item) => item.toString(16).padStart(2, "0")).join("");
}

function readDemoAccount(): DemoAccount | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(DEMO_ACCOUNT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as DemoAccount;
  } catch {
    window.sessionStorage.removeItem(DEMO_ACCOUNT_KEY);
    return null;
  }
}

export async function demoLogin(email: string, password: string): Promise<Session> {
  const normalizedEmail = email.trim().toLowerCase();
  const state = readState();
  const localAccount = readDemoAccount();
  const fixedAccount = normalizedEmail === DEMO_EMAIL && password === DEMO_PASSWORD;
  const localAccountMatches = Boolean(
    localAccount
    && normalizedEmail === localAccount.email
    && await demoPasswordDigest(password) === localAccount.password_digest
  );
  if (!fixedAccount && !localAccountMatches) {
    throw new Error("Credenciales inválidas");
  }
  const loginEmail = localAccountMatches && localAccount ? localAccount.email : DEMO_EMAIL;
  const loginName = localAccountMatches && localAccount ? localAccount.name : "Administración EcoNexo Misiones";
  state.notifications.unshift({
    id: newId("notification"), org_id: state.org.id, org_name: state.org.name,
    kind: "login_success", visibility: "both", severity: "info",
    title: "Nuevo ingreso a EcoNexo", message: `${loginName} ingresó al centro de comando.`,
    actor_user_id: state.users[0]?.id || null, actor_email: loginEmail,
    metadata: { provider: "password", ip_masked: "demo" }, read: false, created_at: new Date().toISOString(),
  });
  writeState(state);
  return {
    access_token: "cloudflare-demo-session",
    org_id: state.org.id,
    role: "admin",
    name: loginName,
    email: loginEmail,
    avatar_url: null,
    auth_provider: "password",
    is_new_user: false,
  };
}

async function demoCreateAccount(input: EmailRegisterInput): Promise<Session> {
  if (!input.organization_name.trim() || !input.name.trim() || !input.terms_accepted) {
    throw new Error("Completá la organización, tus datos y aceptá los términos.");
  }
  if (input.password.length < 8 || !/[A-Za-zÁÉÍÓÚáéíóúÑñ]/.test(input.password) || !/\d/.test(input.password)) {
    throw new Error("La contraseña debe tener 8 caracteres e incluir una letra y un número.");
  }

  const state = readState();
  const normalizedEmail = input.email.trim().toLowerCase();
  state.org = {
    ...state.org,
    name: input.organization_name.trim(),
    slug: input.organization_name.trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48) || "organizacion-demo",
    vertical: input.vertical,
    province: "Misiones",
    department: input.department || null,
    municipality: input.municipality || null,
    territory_scope: input.municipality ? "municipal" : input.department ? "departamental" : "provincial",
  };
  const now = new Date().toISOString();
  state.users = [{
    id: "user-demo-registered",
    name: input.name.trim(),
    email: normalizedEmail,
    role: "admin",
    is_active: true,
    auth_provider: "password",
    email_verified: false,
    avatar_url: null,
    last_login_at: now,
    created_at: now,
    updated_at: now,
  }, ...state.users.filter((user) => user.email.toLowerCase() !== normalizedEmail)];
  state.impactReports = state.impactReports.map((report) => ({
    ...report,
    org_id: state.org.id,
    org_name: state.org.name,
  }));
  pushAudit(state, "create", "organization", state.org.id, { source: "email_registration_demo", vertical: input.vertical });
  state.subscriptionPlanKey = "sandbox";
  state.notifications.unshift({
    id: newId("notification"), org_id: state.org.id, org_name: state.org.name,
    kind: "organization_registered", visibility: "both", severity: "success",
    title: "Nueva organización registrada", message: `${state.org.name} creó su espacio institucional en EcoNexo.`,
    actor_user_id: "user-demo-registered", actor_email: normalizedEmail,
    metadata: { provider: "password", plan: "sandbox" }, read: false, created_at: now,
  });
  writeState(state);

  const account: DemoAccount = {
    email: normalizedEmail,
    password_digest: await demoPasswordDigest(input.password),
    name: input.name.trim(),
    org_id: state.org.id,
  };
  window.sessionStorage.setItem(DEMO_ACCOUNT_KEY, JSON.stringify(account));

  return {
    access_token: "cloudflare-demo-registered-session",
    org_id: state.org.id,
    role: "admin",
    name: account.name,
    email: account.email,
    avatar_url: null,
    auth_provider: "password",
    is_new_user: true,
  };
}

/** Alta institucional: crea la solicitud pero no habilita el acceso. */
export async function demoRegisterEmail(input: EmailRegisterInput): Promise<RegistrationPending> {
  if (!input.phone?.trim()) {
    throw new Error("Ingresá un teléfono de contacto.");
  }
  const session = await demoCreateAccount(input);
  return {
    status: "pending_approval",
    organization_id: session.org_id,
    organization_name: input.organization_name.trim(),
    email: session.email,
    phone: input.phone,
    detail:
      "Recibimos tu solicitud. Administración general va a contactarte por WhatsApp " +
      `al ${input.phone} para coordinar la licencia y habilitar el acceso.`,
  };
}

/** Cuenta comunitaria de EcoNexoFoI: gratuita e inmediata, sin aprobación. */
export async function demoRegisterCommunity(input: EmailRegisterInput): Promise<Session> {
  return { ...await demoCreateAccount(input), account_type: "community" };
}

export async function demoGoogleLogin(input: GoogleAuthInput): Promise<Session> {
  await Promise.resolve();
  if (input.mode === "register" && (!input.organization_name || !input.terms_accepted)) {
    throw new Error("Completá la organización y aceptá los términos");
  }
  const state = readState();
  const isNew = input.mode === "register";
  if (isNew) {
    state.org = { ...state.org, name: input.organization_name || state.org.name, vertical: input.vertical || state.org.vertical };
    state.subscriptionPlanKey = "sandbox";
  }
  state.notifications.unshift({
    id: newId("notification"), org_id: state.org.id, org_name: state.org.name,
    kind: isNew ? "organization_registered" : "login_success", visibility: "both", severity: isNew ? "success" : "info",
    title: isNew ? "Nueva organización registrada con Google" : "Nuevo ingreso con Google",
    message: isNew ? `${state.org.name} creó su espacio institucional en EcoNexo.` : "Valentina EcoNexo ingresó al centro de comando mediante Google.",
    actor_user_id: state.users[0]?.id || null, actor_email: "valentina@misiones.econexo.ar",
    metadata: { provider: "google", plan: isNew ? "sandbox" : state.subscriptionPlanKey, ip_masked: "demo" },
    read: false, created_at: new Date().toISOString(),
  });
  writeState(state);
  return {
    access_token: "cloudflare-google-demo-session",
    org_id: state.org.id,
    role: "admin",
    name: "Valentina EcoNexo",
    email: "valentina@misiones.econexo.ar",
    avatar_url: null,
    auth_provider: "google",
    is_new_user: isNew,
  };
}

function demoPlans(): SubscriptionPlan[] {
  return [
    { plan_key: "sandbox", display_name: "Sandbox calificado", description: "Evaluación comercial limitada.", price_min_usd: 0, price_max_usd: 0, billing_period: "trial", duration_days: 14, entitlements: { max_users: 2, max_devices: 2, max_zones: 1, max_rules: 2, max_critical_layers: 1, municipality_limit: 1, included_modules: ["core", "agro"] } },
    { plan_key: "diagnostic", display_name: "Diagnóstico territorial", description: "Mapa base, lectura de riesgo y propuesta de piloto.", price_min_usd: 2000, price_max_usd: 4000, billing_period: "one_time", duration_days: 30, entitlements: { max_users: 3, max_devices: 0, max_zones: 1, max_rules: 0, max_critical_layers: 1, municipality_limit: 1, included_modules: ["core", "agro"] } },
    { plan_key: "pilot_8_weeks", display_name: "Piloto 8 semanas", description: "Dashboard, tres capas críticas, validación, reportes y capacitación.", price_min_usd: 18000, price_max_usd: 35000, billing_period: "one_time", duration_days: 56, entitlements: { max_users: 10, max_devices: 25, max_zones: 2, max_rules: 12, max_critical_layers: 3, municipality_limit: 2, report_frequency: "semanal o quincenal", api_access: false, audit_export: true, custom_models: false, sla: false, included_modules: ["core", "fire_smoke", "forestry_pests", "agro"] } },
    { plan_key: "municipal", display_name: "SaaS Municipal", description: "Un municipio, alertas base, reportes mensuales y soporte limitado.", price_min_usd: 800, price_max_usd: 1500, billing_period: "monthly", duration_days: null, entitlements: { max_users: 10, max_devices: 50, max_zones: 5, max_rules: 20, max_critical_layers: 3, municipality_limit: 1, report_frequency: "mensual", api_access: false, audit_export: false, custom_models: false, sla: false, included_modules: ["core", "agro"] } },
    { plan_key: "province_pro", display_name: "SaaS Provincia / Pro", description: "Múltiples zonas, reportes quincenales y usuarios internos.", price_min_usd: 3500, price_max_usd: 8000, billing_period: "monthly", duration_days: null, entitlements: { max_users: 50, max_devices: 500, max_zones: 30, max_rules: 100, max_critical_layers: 12, municipality_limit: 79, report_frequency: "quincenal", api_access: false, audit_export: true, custom_models: false, sla: false, included_modules: ["core", "agro"] } },
    { plan_key: "enterprise", display_name: "Enterprise minero / energético", description: "SLA, integraciones, API, auditoría y modelos personalizados.", price_min_usd: 12000, price_max_usd: null, billing_period: "monthly", duration_days: null, entitlements: { max_users: 250, max_devices: 5000, max_zones: 250, max_rules: 1000, max_critical_layers: 50, municipality_limit: 79, report_frequency: "personalizada", api_access: true, audit_export: true, custom_models: true, sla: true, included_modules: ["core", "fire_smoke", "forestry_pests", "agro"] } },
    { plan_key: "agro_productor", display_name: "EcoNexo AG · Productor", description: "Lotes, fenología, balance hídrico y ventanas de aplicación sobre datos meteorológicos reales.", price_min_usd: 400, price_max_usd: 1200, billing_period: "monthly", duration_days: null, entitlements: { max_users: 8, max_devices: 25, max_zones: 10, max_rules: 25, max_critical_layers: 3, municipality_limit: 3, report_frequency: "quincenal", api_access: false, audit_export: true, custom_models: false, sla: false, included_modules: ["core", "agro"] } },
    { plan_key: "academy", display_name: "Academia EcoNexo", description: "Capacitación, manuales, certificación interna y simulacros.", price_min_usd: 2000, price_max_usd: 6000, billing_period: "cohort", duration_days: 45, entitlements: { max_users: 40, max_devices: 0, max_zones: 1, max_rules: 0, max_critical_layers: 1, municipality_limit: 1, report_frequency: "simulación", api_access: false, audit_export: false, custom_models: false, sla: false, included_modules: ["core", "agro"] } },
  ];
}

function demoSubscription(state: DemoState): SubscriptionMe {
  const plan = demoPlans().find((item) => item.plan_key === state.subscriptionPlanKey) || demoPlans()[0];
  const remainingDays = plan.plan_key === "sandbox" ? 13 : plan.plan_key === "pilot_8_weeks" ? 55 : plan.duration_days;
  return {
    plan, status: plan.billing_period === "monthly" ? "active" : "trial", starts_at: isoAgo(1440), expires_at: remainingDays ? new Date(Date.now() + remainingDays * 86_400_000).toISOString() : null,
    available: true, expiry_label: remainingDays ? `${remainingDays} días restantes` : "sin vencimiento", entitlements: plan.entitlements,
    usage: { users: state.users.filter((item) => item.is_active).length, devices: initialDevices().length, zones: state.zones.length, rules: state.rules.length, reports_this_month: state.impactReports.length },
    platform_admin: false, sales_email: "comercial@econexo.ar",
  };
}

const AGRO_SIN_DEMO =
  "EcoNexo AG procesa datos meteorológicos reales y no tiene modo demo: mostrar " +
  "indicadores agronómicos inventados sería peor que no mostrarlos. Conectá la API " +
  "productiva para usar el módulo.";

export async function demoGet<T>(path: string): Promise<T> {
  await Promise.resolve();
  const state = readState();

  if (path.startsWith("/agro/")) throw new Error(AGRO_SIN_DEMO);

  if (path === "/orgs/me") return copy(state.org) as T;
  if (path === "/orgs/public") {
    return copy([{ id: state.org.id, name: state.org.name, vertical: state.org.vertical }]) as T;
  }
  if (path === "/kpis") return copy(kpis(state)) as T;
  if (path === "/environment/source-settings" || path === "/admin/source-settings") return copy(state.sourceSettings) as T;
  if (path === "/environment/snapshots/latest") {
    if (!state.snapshots.length) throw new Error("No hay snapshots ambientales registrados");
    return copy(state.snapshots[0]) as T;
  }
  if (path.startsWith("/environment/snapshots")) return copy(state.snapshots) as T;
  if (path === "/admin/users") return copy(state.users) as T;
  if (path === "/zones") return copy(state.zones) as T;
  if (path.startsWith("/admin/audit")) return copy(state.audit) as T;
  if (path === "/admin/notifications/unread-count") return copy({ unread: state.notifications.filter((item) => !item.read).length }) as T;
  if (path.startsWith("/admin/notifications")) {
    const unreadOnly = path.includes("unread_only=true");
    return copy(unreadOnly ? state.notifications.filter((item) => !item.read) : state.notifications) as T;
  }
  if (path === "/subscriptions/plans") return copy(demoPlans()) as T;
  if (path === "/subscriptions/me") return copy(demoSubscription(state)) as T;
  if (path === "/subscriptions/requests") return copy(state.licenseRequests) as T;
  if (path.startsWith("/subscriptions/platform/requests")) return copy([]) as T;
  if (path === "/subscriptions/platform/organizations") return copy([]) as T;
  if (path === "/admin/summary") {
    const last = state.snapshots[0];
    const value: AdminSummary = {
      users_total: state.users.length,
      users_active: state.users.filter((item) => item.is_active).length,
      devices_total: initialDevices().length,
      devices_online: initialDevices().filter((item) => item.status === "online").length,
      zones_total: state.zones.length,
      rules_total: state.rules.length,
      rules_enabled: state.rules.filter((item) => item.enabled).length,
      reports_pending: state.reports.filter((item) => item.status === "pendiente").length,
      alerts_active: state.alerts.filter((item) => !["descartada", "resuelta"].includes(item.status)).length,
      snapshots_24h: state.snapshots.filter((item) => Date.now() - new Date(item.created_at).getTime() < 86_400_000).length,
      last_snapshot_level: last?.snapshot.overall_level || null,
      last_snapshot_score: last?.snapshot.overall_score ?? null,
      last_snapshot_at: last?.created_at || null,
    };
    return copy(value) as T;
  }
  if (path === "/alerts") return copy(state.alerts) as T;
  if (path === "/devices") return copy(initialDevices()) as T;
  if (path.startsWith("/satellite/detections")) {
    const detections: Detection[] = [
      {
        id: "det-firms-1", source: "NASA FIRMS", lat: -26.836, lon: -54.405,
        brightness: 331.4, confidence: 0.91, frp: 18.7, acquired_at: isoAgo(11),
      },
      {
        id: "det-firms-2", source: "NASA FIRMS", lat: -26.802, lon: -54.458,
        brightness: 309.8, confidence: 0.66, frp: 7.2, acquired_at: isoAgo(94),
      },
    ];
    return copy(detections) as T;
  }
  if (path === "/reports") return copy(state.reports) as T;
  if (path === "/modules/me") {
    const modules: ModuleEntitlement[] = [
      { module_key: "core", status: "active", plan_name: "Plataforma EcoNexo", starts_at: isoAgo(40000), expires_at: null, config: { human_approval_required: true }, available: true },
      { module_key: "fire_smoke", status: "trial", plan_name: "Focos de incendio forestal y humo", starts_at: isoAgo(1000), expires_at: new Date(Date.now() + 30 * 86_400_000).toISOString(), config: { plain_language: true, emergency_numbers: ["911", "100", "103", "105"] }, available: true },
      { module_key: "forestry_pests", status: "trial", plan_name: "Vigilancia de plagas forestales", starts_at: isoAgo(1000), expires_at: new Date(Date.now() + 30 * 86_400_000).toISOString(), config: { plain_language: true, focus_area: "San Antonio - General Manuel Belgrano" }, available: true },
      { module_key: "agro", status: "suspended", plan_name: "EcoNexo AG · inteligencia agronómica", starts_at: isoAgo(1000), expires_at: null, config: {}, available: false },
    ];
    return copy(modules) as T;
  }
  if (path === "/rules") return copy(state.rules) as T;
  if (path === "/reports/citizen-session") {
    return copy({ token: `demo-citizen-${crypto.randomUUID()}`, expires_in_days: 180 }) as T;
  }
  if (path === "/impact-reports") return copy(state.impactReports) as T;
  const publicMatch = path.match(/^\/impact-reports\/public\/view\/(.+)$/);
  if (publicMatch) {
    const reportId = state.publicLinks[publicMatch[1]];
    const report = state.impactReports.find((item) => item.id === reportId && item.status === "publicado");
    if (!report || !report.published_at) throw new Error("Informe no encontrado o enlace revocado");
    const publicReport: PublicImpactReport = {
      report_kind: report.report_kind,
      environmental_snapshot_id: report.environmental_snapshot_id,
      methodology_version: report.methodology_version,
      official_metadata: report.official_metadata,
      org_name: report.org_name, org_vertical: state.org.vertical, primary_color: state.org.primary_color,
      title: report.title, recipient_type: report.recipient_type, recipient_name: report.recipient_name,
      period_start: report.period_start, period_end: report.period_end,
      executive_summary: report.executive_summary, metrics: report.metrics,
      highlights: report.highlights, recommendations: report.recommendations,
      published_at: report.published_at,
    };
    return copy(publicReport) as T;
  }

  const readingMatch = path.match(/^\/devices\/([^/]+)\/readings\?(.+)$/);
  if (readingMatch) {
    const params = new URLSearchParams(readingMatch[2]);
    return copy(readings(readingMatch[1], params.get("variable") || "temp")) as T;
  }

  throw new Error(`Ruta demo no implementada: GET ${path}`);
}

export async function demoPost<T>(path: string, body: unknown): Promise<T> {
  await Promise.resolve();
  const state = readState();
  if (path === "/admin/notifications/read-all") {
    state.notifications = state.notifications.map((item) => ({ ...item, read: true })); writeState(state); return undefined as T;
  }
  const notificationRead = path.match(/^\/admin\/notifications\/([^/]+)\/read$/);
  if (notificationRead) {
    state.notifications = state.notifications.map((item) => item.id === notificationRead[1] ? { ...item, read: true } : item); writeState(state); return undefined as T;
  }
  if (path === "/subscriptions/request-change") {
    const input = body as { requested_plan: LicenseRequest["requested_plan"]; message?: string };
    const request: LicenseRequest = {
      id: newId("license-request"), org_id: state.org.id, org_name: state.org.name,
      requested_by: state.users[0]?.id || null, requester_name: state.users[0]?.name || null,
      requester_email: state.users[0]?.email || null, requested_plan: input.requested_plan,
      message: input.message || null, status: "pending", created_at: new Date().toISOString(), reviewed_at: null,
    };
    state.licenseRequests.unshift(request);
    state.notifications.unshift({
      id: newId("notification"), org_id: state.org.id, org_name: state.org.name,
      kind: "license_request_created", visibility: "org_admins", severity: "success",
      title: "Solicitud enviada", message: `La solicitud para ${input.requested_plan} quedó registrada.`,
      actor_user_id: state.users[0]?.id || null, actor_email: state.users[0]?.email || null,
      metadata: { requested_plan: input.requested_plan }, read: false, created_at: new Date().toISOString(),
    });
    writeState(state); return copy(request) as T;
  }
  if (path === "/admin/copernicus/test") {
    const url = String((body as { url?: string })?.url || "");
    const ok = /^https:\/\/sh\.dataspace\.copernicus\.eu\/ogc\/wms\/[A-Za-z0-9-]+\/?$/.test(url);
    return copy({ ok, service_title: ok ? "Copernicus Data Space Sentinel Hub WMS" : null, layers: ok ? ["TRUE_COLOR", "NDVI", "MOISTURE_INDEX", "NBR_RAW"] : [], detail: ok ? "Formato válido en modo demo. La prueba real se ejecuta contra la API productiva." : "La URL no corresponde a una instancia WMS oficial." }) as T;
  }

  if (path.startsWith("/environment/snapshots")) {
    const snapshot = body as EnvironmentalSnapshot;
    const query = path.includes("?") ? new URLSearchParams(path.split("?", 2)[1]) : new URLSearchParams();
    const activate = query.get("activate_alerts") === "true";
    const ranks: Record<string, number> = { R0: 0, R1: 1, R2: 2, R3: 3, R4: 4, R5: 5 };
    const minimum = ranks[state.sourceSettings.operational_alert_min_level] ?? 3;
    const activated = activate ? snapshot.alerts.filter((item) => (ranks[item.level] ?? 0) >= minimum).length : 0;
    const record: EnvironmentalSnapshotRecord = {
      id: newId("snapshot"), org_id: state.org.id, created_by: "user-demo-admin",
      origin: query.get("origin") || "observatorio_web", activated_alerts: activated,
      snapshot, created_at: new Date().toISOString(),
    };
    state.snapshots.unshift(record);
    pushAudit(state, "create", "environmental_snapshot", record.id, { level: snapshot.overall_level, score: snapshot.overall_score, activated_alerts: activated });
    writeState(state);
    return copy(record) as T;
  }

  if (path === "/admin/users") {
    const input = body as { name: string; email: string; role: AdminUser["role"]; password: string };
    if (state.users.some((item) => item.email.toLowerCase() === input.email.toLowerCase())) throw new Error("El correo ya está registrado");
    const now = new Date().toISOString();
    const created: AdminUser = { id: newId("user"), name: input.name, email: input.email.toLowerCase(), role: input.role, is_active: true, auth_provider: "password", email_verified: false, avatar_url: null, last_login_at: null, created_at: now, updated_at: now };
    state.users.push(created); pushAudit(state, "create", "user", created.id, { email: created.email, role: created.role }); writeState(state);
    return copy(created) as T;
  }

  if (path === "/zones") {
    const input = body as Omit<RiskZone, "id" | "created_at" | "updated_at">;
    const now = new Date().toISOString();
    const zone: RiskZone = { ...input, id: newId("zone"), created_at: now, updated_at: now };
    state.zones.unshift(zone); pushAudit(state, "create", "risk_zone", zone.id, { name: zone.name, kind: zone.kind, radius_m: zone.radius_m }); writeState(state);
    return copy(zone) as T;
  }

  const alertMatch = path.match(/^\/alerts\/([^/]+)\/action$/);
  if (alertMatch) {
    const input = body as { action: string };
    const alert = state.alerts.find((item) => item.id === alertMatch[1]);
    if (!alert) throw new Error("Alerta no encontrada");
    const statuses: Record<string, string> = {
      confirmar: "confirmada",
      descartar: "descartada",
      escalar: "escalada",
    };
    alert.status = statuses[input.action] || alert.status;
    alert.acknowledged_at = input.action === "descartar" ? alert.acknowledged_at : new Date().toISOString();
    if (input.action === "descartar") alert.resolved_at = new Date().toISOString();
    writeState(state);
    return copy(alert) as T;
  }

  if (path === "/rules") {
    const input = body as Omit<Rule, "id">;
    const rule: Rule = { ...input, id: newId("rule") };
    state.rules.unshift(rule);
    writeState(state);
    return copy(rule) as T;
  }

  if (path === "/modules/alert-share") {
    return copy({ id: newId("share"), created_at: new Date().toISOString() }) as T;
  }

  if (path === "/impact-reports") {
    const input = body as { report_kind?: ImpactReport["report_kind"]; environmental_snapshot_id?: string | null; title: string; recipient_type: ImpactReport["recipient_type"]; recipient_name: string; period_start: string; period_end: string; executive_summary?: string; recommendations?: string[] };
    const now = new Date().toISOString();
    const snapshotRecord = input.environmental_snapshot_id
      ? state.snapshots.find((item) => item.id === input.environmental_snapshot_id)
      : input.report_kind && input.report_kind !== "desempeno_operativo" ? state.snapshots[0] : undefined;
    const report: ImpactReport = {
      id: newId("impact"), org_id: state.org.id, org_name: state.org.name,
      report_kind: input.report_kind || "desempeno_operativo",
      environmental_snapshot_id: snapshotRecord?.id || null,
      methodology_version: snapshotRecord?.snapshot.methodology_version || null,
      official_metadata: snapshotRecord ? { spaceai: snapshotRecord.snapshot, document_class: input.report_kind, disclaimer: "Documento emitido por EcoNexo; no constituye certificación de autoridad pública." } : {},
      title: input.title, recipient_type: input.recipient_type, recipient_name: input.recipient_name,
      period_start: input.period_start, period_end: input.period_end,
      executive_summary: input.executive_summary || "EcoNexo consolido evidencia multifuente y metricas operativas para el periodo seleccionado.",
      metrics: { devices_total: 6, devices_online: 5, alerts_total: state.alerts.length + 4, critical_alerts: 2, alerts_confirmed: 5, model_precision: 0.89, average_detection_seconds: 42, average_response_seconds: 778, response_time_reduction: 0.46, citizen_reports_total: state.reports.length + 8, citizen_reports_verified: state.reports.filter((item) => item.status === "verificado").length + 7, valid_reports_rate: 0.73 },
      highlights: snapshotRecord
        ? [`Health Threat Index: ${snapshotRecord.snapshot.overall_level} · ${Math.round(snapshotRecord.snapshot.overall_score)}/100.`, "Disponibilidad de la red de sensores: 83%.", "Tiempo medio de deteccion: 42 segundos."]
        : ["Disponibilidad de la red de sensores: 83%.", "Tiempo medio de deteccion: 42 segundos.", "Reduccion estimada del tiempo de respuesta: 46%."],
      recommendations: input.recommendations?.filter(Boolean) || ["Revisar alertas criticas y documentar acciones."],
      status: "borrador", published_at: null, created_at: now, updated_at: now,
    };
    state.impactReports.unshift(report); pushAudit(state, "create", "impact_report", report.id, { report_kind: report.report_kind, snapshot_id: report.environmental_snapshot_id }); writeState(state); return copy(report) as T;
  }

  const publishMatch = path.match(/^\/impact-reports\/([^/]+)\/publish$/);
  if (publishMatch) {
    const report = state.impactReports.find((item) => item.id === publishMatch[1]);
    if (!report) throw new Error("Informe no encontrado");
    const token = crypto.randomUUID().replaceAll("-", "") + crypto.randomUUID().replaceAll("-", "");
    report.status = "publicado"; report.published_at = new Date().toISOString(); report.updated_at = report.published_at;
    state.publicLinks[token] = report.id; writeState(state);
    const result: ImpactReportPublishResult = { report: copy(report), public_token: token, share_url: `${window.location.origin}/informe?token=${token}` };
    return result as T;
  }

  const revokeMatch = path.match(/^\/impact-reports\/([^/]+)\/revoke$/);
  if (revokeMatch) {
    const report = state.impactReports.find((item) => item.id === revokeMatch[1]);
    if (!report) throw new Error("Informe no encontrado");
    report.status = "borrador"; report.published_at = null; report.updated_at = new Date().toISOString();
    Object.entries(state.publicLinks).forEach(([token, id]) => { if (id === report.id) delete state.publicLinks[token]; });
    writeState(state); return copy(report) as T;
  }

  const moderateMatch = path.match(/^\/reports\/([^/]+)\/moderate$/);
  if (moderateMatch) {
    const input = body as { status: string };
    const report = state.reports.find((item) => item.id === moderateMatch[1]);
    if (!report) throw new Error("Reporte no encontrado");
    report.status = input.status;
    writeState(state);
    return copy(report) as T;
  }

  if (path.startsWith("/agro/")) throw new Error(AGRO_SIN_DEMO);
  throw new Error(`Ruta demo no implementada: POST ${path}`);
}

export async function demoPatch<T>(path: string, body?: unknown): Promise<T> {
  await Promise.resolve();
  const state = readState();

  const ruleMatch = path.match(/^\/rules\/([^/]+)\/toggle$/);
  if (ruleMatch) {
    const rule = state.rules.find((item) => item.id === ruleMatch[1]);
    if (!rule) throw new Error("Regla no encontrada");
    rule.enabled = !rule.enabled;
    pushAudit(state, "toggle", "rule", rule.id, { enabled: rule.enabled });
    writeState(state);
    return copy(rule) as T;
  }

  const userMatch = path.match(/^\/admin\/users\/([^/]+)$/);
  if (userMatch) {
    const user = state.users.find((item) => item.id === userMatch[1]);
    if (!user) throw new Error("Usuario no encontrado");
    Object.assign(user, body as Partial<Pick<AdminUser, "name" | "role" | "is_active">>, { updated_at: new Date().toISOString() });
    pushAudit(state, "update", "user", user.id, body as Record<string, unknown>);
    writeState(state);
    return copy(user) as T;
  }

  if (path === "/admin/organization") {
    Object.assign(state.org, body as Partial<Org>);
    pushAudit(state, "update", "organization", state.org.id, body as Record<string, unknown>);
    writeState(state);
    return copy(state.org) as T;
  }

  if (path === "/admin/source-settings") {
    state.sourceSettings = { ...state.sourceSettings, ...(body as Partial<EnvironmentalSourceSettings>), copernicus_configured: Boolean((body as Partial<EnvironmentalSourceSettings>).copernicus_wms_url ?? state.sourceSettings.copernicus_wms_url), updated_at: new Date().toISOString() };
    pushAudit(state, "update", "environmental_source_settings", state.org.id, body as Record<string, unknown>);
    writeState(state);
    return copy(state.sourceSettings) as T;
  }

  const zoneMatch = path.match(/^\/zones\/([^/]+)$/);
  if (zoneMatch) {
    const zone = state.zones.find((item) => item.id === zoneMatch[1]);
    if (!zone) throw new Error("Zona no encontrada");
    Object.assign(zone, body as Partial<RiskZone>, { updated_at: new Date().toISOString() });
    pushAudit(state, "update", "risk_zone", zone.id, body as Record<string, unknown>);
    writeState(state);
    return copy(zone) as T;
  }

  if (path.startsWith("/agro/")) throw new Error(AGRO_SIN_DEMO);
  throw new Error(`Ruta demo no implementada: PATCH ${path}`);
}

export async function demoDelete(path: string): Promise<void> {
  await Promise.resolve();
  const state = readState();
  const ruleMatch = path.match(/^\/rules\/([^/]+)$/);
  if (ruleMatch) {
    state.rules = state.rules.filter((item) => item.id !== ruleMatch[1]);
    pushAudit(state, "delete", "rule", ruleMatch[1]);
    writeState(state); return;
  }
  const reportMatch = path.match(/^\/impact-reports\/([^/]+)$/);
  if (reportMatch) {
    state.impactReports = state.impactReports.filter((item) => item.id !== reportMatch[1]);
    Object.entries(state.publicLinks).forEach(([token, id]) => { if (id === reportMatch[1]) delete state.publicLinks[token]; });
    pushAudit(state, "delete", "impact_report", reportMatch[1]);
    writeState(state); return;
  }
  const userMatch = path.match(/^\/admin\/users\/([^/]+)$/);
  if (userMatch) {
    const user = state.users.find((item) => item.id === userMatch[1]);
    if (!user) throw new Error("Usuario no encontrado");
    if (user.id === "user-demo-admin") throw new Error("No puedes desactivar tu propia cuenta");
    user.is_active = false; user.updated_at = new Date().toISOString();
    pushAudit(state, "deactivate", "user", user.id);
    writeState(state); return;
  }
  const zoneMatch = path.match(/^\/zones\/([^/]+)$/);
  if (zoneMatch) {
    state.zones = state.zones.filter((item) => item.id !== zoneMatch[1]);
    pushAudit(state, "delete", "risk_zone", zoneMatch[1]);
    writeState(state); return;
  }
  const snapshotMatch = path.match(/^\/environment\/snapshots\/([^/]+)$/);
  if (snapshotMatch) {
    state.snapshots = state.snapshots.filter((item) => item.id !== snapshotMatch[1]);
    pushAudit(state, "delete", "environmental_snapshot", snapshotMatch[1]);
    writeState(state); return;
  }
  if (path.startsWith("/agro/")) throw new Error(AGRO_SIN_DEMO);
  throw new Error(`Ruta demo no implementada: DELETE ${path}`);
}

export async function demoSubmitReport(form: FormData): Promise<void> {
  await Promise.resolve();
  const state = readState();
  const report: Report = {
    id: newId("report"),
    type: String(form.get("type") || "otro"),
    description: form.get("description") ? String(form.get("description")) : null,
    photo_url: null,
    lat: Number(form.get("lat")) || -26.82,
    lon: Number(form.get("lon")) || -54.45,
    status: "pendiente",
    correlation_score: 0.74,
    reputation_score: 0.80,
    created_at: new Date().toISOString(),
  };
  state.reports.unshift(report);
  writeState(state);
}

