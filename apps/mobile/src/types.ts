export interface Session {
  access_token: string;
  token_type: string;
  org_id: string;
  role: string;
  name: string;
  email: string;
  avatar_url: string | null;
  auth_provider: "password" | "google";
  is_new_user?: boolean;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  vertical: string;
  primary_color: string;
  baseline_response_s: number;
  province: string;
  department: string | null;
  municipality: string | null;
  territory_scope: "provincial" | "departamental" | "municipal" | "area_operativa";
}

export interface Kpi {
  detection_time_s: number | null;
  detection_target_s: number;
  model_precision: number | null;
  precision_target: number;
  valid_reports_rate: number | null;
  valid_reports_target: number;
  response_time_reduction: number | null;
  response_reduction_target: number;
  global_status: "normal" | "atencion" | "critico";
  active_alerts: number;
}

export interface Device {
  id: string;
  name: string;
  external_id: string;
  lat: number;
  lon: number;
  status: string;
  battery: number | null;
  rssi: number | null;
  tags: string[];
  last_seen: string | null;
}

export interface AlertSource {
  source_type: string;
  ref_id: string | null;
  weight: number;
  detail: Record<string, unknown> | null;
}

export interface Alert {
  id: string;
  type: string;
  severity: string;
  status: string;
  lat: number;
  lon: number;
  confidence: number;
  title: string;
  detected_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  sources: AlertSource[];
}

export interface Detection {
  id: string;
  source: string;
  lat: number;
  lon: number;
  brightness: number | null;
  confidence: number | null;
  frp: number | null;
  acquired_at: string;
}

export interface CitizenReport {
  id: string;
  type: string;
  description: string | null;
  photo_url: string | null;
  lat: number;
  lon: number;
  status: string;
  correlation_score: number | null;
  reputation_score: number | null;
  created_at: string;
}

export interface ModuleEntitlement {
  module_key: "core" | "fire_smoke" | "forestry_pests";
  status: "trial" | "active" | "suspended" | "expired";
  plan_name: string;
  starts_at: string;
  expires_at: string | null;
  config: Record<string, unknown>;
  available: boolean;
}

export interface EnvironmentalIndex {
  id: string;
  label: string;
  level: string;
  score: number;
  value: number | null;
  unit: string;
  status: string;
  source: string;
  confidence: number;
  action: string;
  health_impacts: string[];
  evidence: string[];
  formula?: string | null;
  relative_exceedance_pct?: number | null;
  weighted_contribution?: number | null;
}

export interface EnvironmentalSnapshot {
  methodology_version: string;
  generated_at: string;
  latitude: number;
  longitude: number;
  overall_score: number;
  overall_level: string;
  overall_label: string;
  observations: Record<string, number | null>;
  indices: EnvironmentalIndex[];
  alerts: Array<{
    id: string;
    domain: string;
    level: string;
    severity: string;
    title: string;
    summary: string;
    action: string;
    source: string;
    confidence: number;
  }>;
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

export interface EarthNow {
  fetchedAt: string;
  latitude: number;
  longitude: number;
  temperature: number | null;
  humidity: number | null;
  precipitation: number | null;
  windSpeed: number | null;
  windDirection: number | null;
  windGusts: number | null;
  soilMoisture: number | null;
  vapourPressureDeficit: number | null;
  pm25: number | null;
  pm10: number | null;
  usAqi: number | null;
  uvIndex: number | null;
}

export interface DashboardBundle {
  org: Organization;
  kpi: Kpi;
  devices: Device[];
  alerts: Alert[];
  detections: Detection[];
  reports: CitizenReport[];
  modules: ModuleEntitlement[];
  latestSnapshot: EnvironmentalSnapshotRecord | null;
}
