export interface Session {
  access_token: string;
  org_id: string;
  role: string;
  name: string;
  email: string;
  avatar_url: string | null;
  auth_provider: "password" | "google";
  is_new_user?: boolean;
  platform_admin?: boolean;
  must_change_password?: boolean;
}
export interface Org { id: string; name: string; slug: string; vertical: string; primary_color: string; baseline_response_s: number; province: string; department: string | null; municipality: string | null; territory_scope: "provincial" | "departamental" | "municipal" | "area_operativa"; }
export interface Device { id: string; name: string; external_id: string; lat: number; lon: number; status: string; battery: number | null; rssi: number | null; tags: string[]; last_seen: string | null; }
export interface AlertSource { source_type: string; ref_id: string | null; weight: number; detail: Record<string, unknown> | null; }
export interface Alert { id: string; type: string; severity: string; status: string; lat: number; lon: number; confidence: number; title: string; detected_at: string; acknowledged_at: string | null; resolved_at: string | null; sources: AlertSource[]; }
export interface Detection { id: string; source: string; lat: number; lon: number; brightness: number | null; confidence: number | null; frp: number | null; acquired_at: string; }
export interface Report { id: string; type: string; description: string | null; photo_url: string | null; lat: number; lon: number; status: string; correlation_score: number | null; reputation_score: number | null; created_at: string; }
export interface Kpi { detection_time_s: number | null; detection_target_s: number; model_precision: number | null; precision_target: number; valid_reports_rate: number | null; valid_reports_target: number; response_time_reduction: number | null; response_reduction_target: number; global_status: "normal" | "atencion" | "critico"; active_alerts: number; }
export interface Rule { id: string; name: string; alert_type: string; conditions: {variable:string;operator:string;threshold:number}[]; condition_logic: string; window_seconds: number; severity: string; require_satellite: boolean; enabled: boolean; }

export type ReportKind = "desempeno_operativo" | "boletin_amenaza" | "parte_tecnico" | "episodio_ambiental";
export type RecipientType = "organizacion" | "municipio" | "programa_organismo" | "inversor" | "aseguradora" | "auditoria";
export interface ImpactMetrics {
  devices_total: number;
  devices_online: number;
  alerts_total: number;
  critical_alerts: number;
  alerts_confirmed: number;
  model_precision: number | null;
  average_detection_seconds: number | null;
  average_response_seconds: number | null;
  response_time_reduction: number | null;
  citizen_reports_total: number;
  citizen_reports_verified: number;
  valid_reports_rate: number | null;
  [key: string]: number | null;
}
export interface ImpactReport {
  id: string;
  report_kind: ReportKind;
  environmental_snapshot_id: string | null;
  methodology_version: string | null;
  official_metadata: Record<string, unknown>;
  org_id: string;
  org_name: string;
  title: string;
  recipient_type: RecipientType;
  recipient_name: string;
  period_start: string;
  period_end: string;
  executive_summary: string;
  metrics: ImpactMetrics;
  highlights: string[];
  recommendations: string[];
  status: "borrador" | "publicado" | "archivado";
  published_at: string | null;
  created_at: string;
  updated_at: string;
}
export interface PublicImpactReport {
  report_kind: ReportKind;
  environmental_snapshot_id: string | null;
  methodology_version: string | null;
  official_metadata: Record<string, unknown>;
  org_name: string;
  org_vertical: string;
  primary_color: string;
  title: string;
  recipient_type: RecipientType;
  recipient_name: string;
  period_start: string;
  period_end: string;
  executive_summary: string;
  metrics: ImpactMetrics;
  highlights: string[];
  recommendations: string[];
  published_at: string;
}
export interface ImpactReportPublishResult {
  report: ImpactReport;
  share_url: string;
  public_token: string;
}

// --- SpaceAI / inteligencia ambiental ---
export type SpaceAILevel = "R0" | "R1" | "R2" | "R3" | "R4" | "R5";
export type ThreatDomainId = "air" | "heat" | "moisture" | "fire" | "hydric" | "uv" | "vector";
export type UserRole = "admin" | "operador" | "visualizador";
export type RiskZoneKind = "incendio" | "hidrica" | "general";

export interface EnvironmentalIndexSnapshot {
  id: ThreatDomainId;
  label: string;
  level: SpaceAILevel;
  score: number;
  value: number | null;
  unit: string;
  status: string;
  source: string;
  confidence: number;
  action: string;
  health_impacts: string[];
  evidence: string[];
}

export interface EnvironmentalAlertSnapshot {
  id: string;
  domain: ThreatDomainId;
  level: SpaceAILevel;
  severity: "baja" | "media" | "alta" | "critica";
  title: string;
  summary: string;
  action: string;
  source: string;
  confidence: number;
}

export interface EnvironmentalObservations {
  temperature_c: number | null;
  relative_humidity_pct: number | null;
  soil_moisture_pct: number | null;
  heat_index_c: number | null;
  wet_bulb_c: number | null;
  pm25_24h_ug_m3: number | null;
  us_aqi: number | null;
  uv_index: number | null;
  river_discharge_m3_s: number | null;
  river_discharge_ratio: number | null;
  precipitation_24h_mm: number | null;
  precipitation_7d_mm: number | null;
  precipitation_forecast_7d_mm: number | null;
  humidity_balance_index: number | null;
  wind_gust_kmh: number | null;
  vapour_pressure_deficit_kpa: number | null;
  [key: string]: number | null;
}

export interface EnvironmentalSnapshot {
  methodology_version: string;
  generated_at: string;
  latitude: number;
  longitude: number;
  overall_score: number;
  overall_level: SpaceAILevel;
  overall_label: string;
  observations: EnvironmentalObservations;
  indices: EnvironmentalIndexSnapshot[];
  alerts: EnvironmentalAlertSnapshot[];
  hotspots: {
    count_48h: number;
    high_confidence_count_48h: number;
    maximum_frp_mw: number | null;
    nearest_distance_km: number | null;
  };
  sources: Record<string, string>;
  limitations: string[];
}

export interface EnvironmentalSnapshotRecord {
  id: string;
  org_id: string;
  created_by: string | null;
  origin: string;
  activated_alerts: number;
  snapshot: EnvironmentalSnapshot;
  created_at: string;
}

export interface EnvironmentalSourceSettings {
  org_id: string;
  default_latitude: number;
  default_longitude: number;
  open_meteo_enabled: boolean;
  air_quality_enabled: boolean;
  flood_enabled: boolean;
  firms_enabled: boolean;
  copernicus_enabled: boolean;
  copernicus_wms_url: string | null;
  copernicus_true_color_layer: string;
  copernicus_ndvi_layer: string;
  copernicus_moisture_layer: string;
  copernicus_burn_layer: string;
  forestry_pest_enabled: boolean;
  sinarame_radar_enabled: boolean;
  refresh_minutes: number;
  fire_radius_km: number;
  operational_alert_min_level: SpaceAILevel;
  auto_activate_alerts: boolean;
  firms_map_key_configured: boolean;
  copernicus_configured: boolean;
  updated_at: string;
}

export interface RiskZone {
  id: string;
  name: string;
  kind: RiskZoneKind;
  lat: number;
  lon: number;
  radius_m: number;
  created_at: string;
  updated_at: string;
}

export interface AdminSummary {
  users_total: number;
  users_active: number;
  devices_total: number;
  devices_online: number;
  zones_total: number;
  rules_total: number;
  rules_enabled: number;
  reports_pending: number;
  alerts_active: number;
  snapshots_24h: number;
  last_snapshot_level: SpaceAILevel | null;
  last_snapshot_score: number | null;
  last_snapshot_at: string | null;
}

export interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  auth_provider: "password" | "google";
  email_verified: boolean;
  avatar_url: string | null;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  user_id: string | null;
  actor_name: string | null;
  action: string;
  resource: string;
  resource_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

// --- Licencias modulares y trazabilidad de Alerta IA ---
export interface ModuleEntitlement {
  module_key: "core" | "fire_smoke" | "forestry_pests";
  status: "trial" | "active" | "suspended" | "expired";
  plan_name: string;
  starts_at: string;
  expires_at: string | null;
  config: Record<string, unknown>;
  available: boolean;
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

export interface AlertShareResult { id: string; created_at: string; }

// --- Suscripciones comerciales y mensajes administrativos ---
export type SubscriptionPlanKey = "sandbox" | "diagnostic" | "pilot_8_weeks" | "municipal" | "province_pro" | "enterprise" | "academy";
export type SubscriptionStatus = "pending" | "trial" | "active" | "past_due" | "suspended" | "expired" | "cancelled";

export interface SubscriptionPlan {
  plan_key: SubscriptionPlanKey;
  display_name: string;
  description: string;
  price_min_usd: number | null;
  price_max_usd: number | null;
  billing_period: "trial" | "one_time" | "monthly" | "annual" | "cohort";
  duration_days: number | null;
  entitlements: Record<string, unknown>;
}

export interface SubscriptionUsage {
  users: number;
  devices: number;
  zones: number;
  rules: number;
  reports_this_month: number;
}

export interface SubscriptionMe {
  plan: SubscriptionPlan;
  status: SubscriptionStatus;
  starts_at: string;
  expires_at: string | null;
  available: boolean;
  expiry_label: string;
  entitlements: Record<string, unknown>;
  usage: SubscriptionUsage;
  platform_admin: boolean;
  sales_email: string | null;
}

export interface LicenseRequest {
  id: string;
  org_id: string;
  org_name: string | null;
  requested_by: string | null;
  requester_name: string | null;
  requester_email: string | null;
  requested_plan: SubscriptionPlanKey;
  message: string | null;
  status: "pending" | "approved" | "rejected" | "cancelled";
  created_at: string;
  reviewed_at: string | null;
}

export interface PlatformSubscriptionRow {
  org_id: string;
  org_name: string;
  municipality: string | null;
  plan_key: SubscriptionPlanKey;
  display_name: string;
  status: SubscriptionStatus;
  starts_at: string;
  expires_at: string | null;
  updated_at: string;
}

export interface AdminNotification {
  id: string;
  org_id: string;
  org_name: string | null;
  kind: string;
  visibility: "org_admins" | "platform_admins" | "both";
  severity: "info" | "success" | "warning" | "critical";
  title: string;
  message: string;
  actor_user_id: string | null;
  actor_email: string | null;
  metadata: Record<string, unknown>;
  read: boolean;
  created_at: string;
}


// --- Consola oculta del administrador general ---
export interface PlatformSummary {
  organizations_total: number;
  organizations_active: number;
  users_total: number;
  users_active: number;
  platform_admins: number;
  pending_license_requests: number;
  logins_24h: number;
}

export interface PlatformUser {
  id: string;
  org_id: string;
  org_name: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  organization_active: boolean;
  auth_provider: "password" | "google";
  email_verified: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformOrganization {
  id: string;
  name: string;
  slug: string;
  vertical: string;
  province: string;
  municipality: string | null;
  is_active: boolean;
  users_total: number;
  users_active: number;
  plan_key: string | null;
  plan_name: string | null;
  subscription_status: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformAudit {
  id: string;
  org_id: string | null;
  org_name: string | null;
  user_id: string | null;
  actor_name: string | null;
  action: string;
  resource: string;
  resource_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}
