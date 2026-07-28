"""Contratos de API (Pydantic v2). Validacion estricta de entrada/salida."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from .territory import DEPARTMENTS, ensure_in_misiones, municipality_department
from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator, model_validator

# --- Auth ---
class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=256)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=6, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("La contraseña no puede comenzar ni terminar con espacios")
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("La contraseña debe incluir al menos una letra y un número")
        return value

    @model_validator(mode="after")
    def validate_password_change(self):
        if self.current_password == self.new_password:
            raise ValueError("La contraseña nueva debe ser diferente de la actual")
        return self


class EmailRegisterIn(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    vertical: Literal["municipio", "forestal", "energetica"]
    municipality: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    terms_accepted: bool = False
    legal_version: str = Field(default="2026-07-27", max_length=32)

    @field_validator("organization_name", "name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("El campo debe contener al menos 2 caracteres")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("La contraseña no puede comenzar ni terminar con espacios")
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("La contraseña debe incluir al menos una letra y un número")
        return value

    @model_validator(mode="after")
    def validate_misiones_territory(self):
        if self.municipality:
            expected = municipality_department(self.municipality)
            if expected is None:
                raise ValueError("El municipio no pertenece al catálogo vigente de Misiones")
            if self.department and self.department != expected:
                raise ValueError("El departamento no coincide con el municipio seleccionado")
            self.department = expected
        elif self.department and self.department not in DEPARTMENTS:
            raise ValueError("El departamento no pertenece a Misiones")
        return self


class GoogleAuthIn(BaseModel):
    credential: str = Field(min_length=100, max_length=8192)
    mode: Literal["login", "register"] = "login"
    organization_name: str | None = Field(default=None, min_length=2, max_length=120)
    vertical: Literal["municipio", "forestal", "energetica"] | None = None
    municipality: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    terms_accepted: bool = False
    legal_version: str = Field(default="2026-07-27", max_length=32)

    @model_validator(mode="after")
    def validate_misiones_territory(self):
        if self.mode == "register" and self.municipality:
            expected = municipality_department(self.municipality)
            if expected is None:
                raise ValueError("El municipio no pertenece al catálogo vigente de Misiones")
            if self.department and self.department != expected:
                raise ValueError("El departamento no coincide con el municipio seleccionado")
            self.department = expected
        elif self.department and self.department not in DEPARTMENTS:
            raise ValueError("El departamento no pertenece a Misiones")
        return self


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    org_id: UUID
    role: str
    name: str
    email: EmailStr
    avatar_url: str | None = None
    auth_provider: Literal["password", "google"] = "password"
    is_new_user: bool = False
    platform_admin: bool = False
    must_change_password: bool = False


class CitizenSessionOut(BaseModel):
    token: str
    expires_in_days: int


# --- Orgs ---
class OrgOut(BaseModel):
    id: UUID
    name: str
    slug: str
    vertical: str
    primary_color: str
    baseline_response_s: int
    province: str = "Misiones"
    department: str | None = None
    municipality: str | None = None
    territory_scope: str = "provincial"


# --- Devices ---
class DeviceTypeIn(BaseModel):
    name: str
    variables: list[dict[str, Any]] = []


class DeviceIn(BaseModel):
    name: str
    external_id: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    device_type_id: UUID | None = None
    tags: list[str] = []

    @model_validator(mode="after")
    def validate_misiones_location(self):
        ensure_in_misiones(self.lat, self.lon)
        return self


class DeviceOut(BaseModel):
    id: UUID
    name: str
    external_id: str
    lat: float
    lon: float
    status: str
    battery: float | None = None
    rssi: int | None = None
    tags: list[str] = []
    last_seen: datetime | None = None


class DeviceCreatedOut(DeviceOut):
    mqtt_username: str
    mqtt_password: str


# --- Rules ---
class RuleCondition(BaseModel):
    variable: str
    operator: Literal[">", ">=", "<", "<=", "==", "!="]
    threshold: float


class RuleIn(BaseModel):
    name: str
    alert_type: Literal["incendio", "anomalia_hidrica", "anomalia"] = "anomalia"
    conditions: list[RuleCondition]
    condition_logic: Literal["AND", "OR"] = "AND"
    window_seconds: int = Field(default=300, ge=1)
    zone_id: UUID | None = None
    device_tags: list[str] = []
    severity: Literal["baja", "media", "alta", "critica"] = "media"
    require_satellite: bool = False
    actions: list[str] = []
    enabled: bool = True


class RuleOut(RuleIn):
    id: UUID


# --- Alerts ---
class AlertSourceOut(BaseModel):
    source_type: str
    ref_id: UUID | None = None
    weight: float
    detail: dict[str, Any] | None = None


class AlertOut(BaseModel):
    id: UUID
    type: str
    severity: str
    status: str
    lat: float
    lon: float
    confidence: float
    title: str
    detected_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    sources: list[AlertSourceOut] = []


class AlertActionIn(BaseModel):
    action: Literal["confirmar", "descartar", "escalar", "asignar"]
    assigned_to: UUID | None = None


# --- Reports (ciudadanos) ---
class ReportOut(BaseModel):
    id: UUID
    type: str
    description: str | None
    photo_url: str | None
    lat: float
    lon: float
    status: str
    correlation_score: float | None = None
    reputation_score: float | None = None
    created_at: datetime


class ReportModerateIn(BaseModel):
    status: Literal["verificado", "rechazado"]


# --- Informes institucionales / de impacto ---
ReportKind = Literal["desempeno_operativo", "boletin_amenaza", "parte_tecnico", "episodio_ambiental"]

RecipientType = Literal[
    "organizacion",
    "municipio",
    "programa_organismo",
    "inversor",
    "aseguradora",
    "auditoria",
]


class ImpactReportCreateIn(BaseModel):
    report_kind: ReportKind = "desempeno_operativo"
    environmental_snapshot_id: UUID | None = None
    title: str = Field(min_length=4, max_length=160)
    recipient_type: RecipientType
    recipient_name: str = Field(min_length=2, max_length=160)
    period_start: date
    period_end: date
    executive_summary: str = Field(default="", max_length=4000)
    recommendations: list[str] = Field(default_factory=list, max_length=12)
    issuing_area: str = Field(default="", max_length=160)
    reviewed_by: str = Field(default="", max_length=160)
    laboratory_name: str = Field(default="", max_length=160)
    protocol_reference: str = Field(default="", max_length=160)
    sample_reference: str = Field(default="", max_length=160)
    technical_notes: str = Field(default="", max_length=6000)

    @field_validator("period_end")
    @classmethod
    def validate_period(cls, value: date, info):
        start = info.data.get("period_start")
        if start and value < start:
            raise ValueError("period_end debe ser igual o posterior a period_start")
        return value


class ImpactReportOut(BaseModel):
    id: UUID
    report_kind: ReportKind = "desempeno_operativo"
    environmental_snapshot_id: UUID | None = None
    methodology_version: str | None = None
    official_metadata: dict[str, Any] = Field(default_factory=dict)
    org_id: UUID
    org_name: str
    title: str
    recipient_type: RecipientType
    recipient_name: str
    period_start: date
    period_end: date
    executive_summary: str
    metrics: dict[str, Any]
    highlights: list[str]
    recommendations: list[str]
    status: Literal["borrador", "publicado", "archivado"]
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ImpactReportPublishOut(BaseModel):
    report: ImpactReportOut
    share_url: str
    public_token: str


class PublicImpactReportOut(BaseModel):
    report_kind: ReportKind = "desempeno_operativo"
    environmental_snapshot_id: UUID | None = None
    methodology_version: str | None = None
    official_metadata: dict[str, Any] = Field(default_factory=dict)
    org_name: str
    org_vertical: str
    primary_color: str
    title: str
    recipient_type: RecipientType
    recipient_name: str
    period_start: date
    period_end: date
    executive_summary: str
    metrics: dict[str, Any]
    highlights: list[str]
    recommendations: list[str]
    published_at: datetime


# --- Licencias modulares y Alerta IA ---
ModuleKey = Literal["core", "fire_smoke", "forestry_pests"]
ModuleStatus = Literal["trial", "active", "suspended", "expired"]


class ModuleEntitlementOut(BaseModel):
    module_key: ModuleKey
    status: ModuleStatus
    plan_name: str
    starts_at: datetime
    expires_at: datetime | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    available: bool


class AlertShareIn(BaseModel):
    channel: Literal["whatsapp", "telegram", "copiar", "email", "otro"]
    audience: Literal["medios", "organizacion", "laboratorio", "emergencia", "publico", "otro"]
    title: str = Field(min_length=3, max_length=240)
    message: str = Field(min_length=10, max_length=12000)
    module_key: ModuleKey = "core"
    snapshot_id: UUID | None = None
    alert_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlertShareOut(BaseModel):
    id: UUID
    created_at: datetime


# --- Suscripciones, límites y mensajes administrativos ---
SubscriptionPlanKey = Literal[
    "sandbox", "diagnostic", "pilot_8_weeks", "municipal",
    "province_pro", "enterprise", "academy"
]
SubscriptionStatus = Literal[
    "pending", "trial", "active", "past_due", "suspended", "expired", "cancelled"
]


class SubscriptionPlanOut(BaseModel):
    plan_key: SubscriptionPlanKey
    display_name: str
    description: str
    price_min_usd: float | None = None
    price_max_usd: float | None = None
    billing_period: Literal["trial", "one_time", "monthly", "annual", "cohort"]
    duration_days: int | None = None
    entitlements: dict[str, Any] = Field(default_factory=dict)


class SubscriptionUsageOut(BaseModel):
    users: int = 0
    devices: int = 0
    zones: int = 0
    rules: int = 0
    reports_this_month: int = 0


class SubscriptionMeOut(BaseModel):
    plan: SubscriptionPlanOut
    status: SubscriptionStatus
    starts_at: datetime
    expires_at: datetime | None = None
    available: bool
    expiry_label: str
    entitlements: dict[str, Any] = Field(default_factory=dict)
    usage: SubscriptionUsageOut
    platform_admin: bool = False
    sales_email: str | None = None


class LicenseRequestIn(BaseModel):
    requested_plan: SubscriptionPlanKey
    message: str = Field(default="", max_length=2000)


class LicenseRequestOut(BaseModel):
    id: UUID
    org_id: UUID
    org_name: str | None = None
    requested_by: UUID | None = None
    requester_name: str | None = None
    requester_email: str | None = None
    requested_plan: SubscriptionPlanKey
    message: str | None = None
    status: Literal["pending", "approved", "rejected", "cancelled"]
    created_at: datetime
    reviewed_at: datetime | None = None


class PlatformSubscriptionUpdateIn(BaseModel):
    plan_key: SubscriptionPlanKey
    status: SubscriptionStatus = "active"
    expires_at: datetime | None = None
    auto_renew: bool = False
    custom_entitlements: dict[str, Any] = Field(default_factory=dict)
    active_modules: list[ModuleKey] | None = None
    notes: str = Field(default="", max_length=4000)
    request_id: UUID | None = None


class PlatformSubscriptionRowOut(BaseModel):
    org_id: UUID
    org_name: str
    municipality: str | None = None
    plan_key: SubscriptionPlanKey
    display_name: str
    status: SubscriptionStatus
    starts_at: datetime
    expires_at: datetime | None = None
    updated_at: datetime


class AdminNotificationOut(BaseModel):
    id: UUID
    org_id: UUID
    org_name: str | None = None
    kind: str
    visibility: Literal["org_admins", "platform_admins", "both"]
    severity: Literal["info", "success", "warning", "critical"]
    title: str
    message: str
    actor_user_id: UUID | None = None
    actor_email: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    read: bool = False
    created_at: datetime


# --- Administración general de plataforma ---
class PlatformSummaryOut(BaseModel):
    organizations_total: int
    organizations_active: int
    users_total: int
    users_active: int
    platform_admins: int
    pending_license_requests: int
    logins_24h: int


class PlatformUserCreateIn(BaseModel):
    org_id: UUID
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: Literal["admin", "operador", "visualizador"] = "operador"
    temporary_password: str = Field(min_length=12, max_length=256)

    @field_validator("temporary_password")
    @classmethod
    def validate_initial_password(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("La contraseña temporal no puede tener espacios al inicio o al final")
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("La contraseña temporal debe incluir una letra y un número")
        return value


class PlatformUserOut(BaseModel):
    id: UUID
    org_id: UUID
    org_name: str
    name: str
    email: EmailStr
    role: Literal["admin", "operador", "visualizador"]
    is_active: bool
    organization_active: bool
    auth_provider: Literal["password", "google"]
    email_verified: bool
    must_change_password: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PlatformUserUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: Literal["admin", "operador", "visualizador"] | None = None
    is_active: bool | None = None


class PlatformPasswordResetIn(BaseModel):
    temporary_password: str = Field(min_length=12, max_length=256)

    @field_validator("temporary_password")
    @classmethod
    def validate_temporary_password(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("La contraseña temporal no puede tener espacios al inicio o al final")
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("La contraseña temporal debe incluir una letra y un número")
        return value


class PlatformOrganizationOut(BaseModel):
    id: UUID
    name: str
    slug: str
    vertical: str
    province: str
    municipality: str | None = None
    is_active: bool
    users_total: int
    users_active: int
    plan_key: str | None = None
    plan_name: str | None = None
    subscription_status: str | None = None
    created_at: datetime
    updated_at: datetime


class PlatformOrganizationUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None


class PlatformAuditOut(BaseModel):
    id: UUID
    org_id: UUID | None = None
    org_name: str | None = None
    user_id: UUID | None = None
    actor_name: str | None = None
    action: str
    resource: str
    resource_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# --- KPIs ---
class KpiOut(BaseModel):
    detection_time_s: float | None
    detection_target_s: int = 300
    model_precision: float | None
    precision_target: float = 0.85
    valid_reports_rate: float | None
    valid_reports_target: float = 0.70
    response_time_reduction: float | None
    response_reduction_target: float = 0.40
    global_status: Literal["normal", "atencion", "critico"]
    active_alerts: int

# --- Administracion, geocercas e inteligencia ambiental SpaceAI ---
SpaceAILevel = Literal["R0", "R1", "R2", "R3", "R4", "R5"]
ThreatDomainId = Literal["air", "heat", "moisture", "fire", "hydric", "uv", "vector"]
UserRole = Literal["admin", "operador", "visualizador"]
RiskZoneKind = Literal["incendio", "hidrica", "general"]


class OrgUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    baseline_response_s: int | None = Field(default=None, ge=60, le=604800)
    department: str | None = Field(default=None, max_length=120)
    municipality: str | None = Field(default=None, max_length=120)
    territory_scope: Literal["provincial", "departamental", "municipal", "area_operativa"] | None = None

    @model_validator(mode="after")
    def validate_misiones_territory(self):
        if self.municipality:
            expected = municipality_department(self.municipality)
            if expected is None:
                raise ValueError("El municipio no pertenece al catálogo vigente de Misiones")
            if self.department and self.department != expected:
                raise ValueError("El departamento no coincide con el municipio seleccionado")
            self.department = expected
        elif self.department and self.department not in DEPARTMENTS:
            raise ValueError("El departamento no pertenece a Misiones")
        return self


class AdminSummaryOut(BaseModel):
    users_total: int
    users_active: int
    devices_total: int
    devices_online: int
    zones_total: int
    rules_total: int
    rules_enabled: int
    reports_pending: int
    alerts_active: int
    snapshots_24h: int
    last_snapshot_level: SpaceAILevel | None = None
    last_snapshot_score: float | None = None
    last_snapshot_at: datetime | None = None


class AdminUserCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: UserRole = "operador"
    password: str = Field(min_length=10, max_length=256)


class AdminUserUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None


class AdminUserOut(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    auth_provider: Literal["password", "google"]
    email_verified: bool
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AuditEventOut(BaseModel):
    id: UUID
    user_id: UUID | None = None
    actor_name: str | None = None
    action: str
    resource: str
    resource_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RiskZoneIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    kind: RiskZoneKind = "general"
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_m: float = Field(ge=50, le=100000)

    @model_validator(mode="after")
    def validate_misiones_location(self):
        ensure_in_misiones(self.lat, self.lon)
        return self


class RiskZoneOut(RiskZoneIn):
    id: UUID
    created_at: datetime
    updated_at: datetime


class EnvironmentalSourceSettingsIn(BaseModel):
    default_latitude: float = Field(default=-26.92, ge=-90, le=90)
    default_longitude: float = Field(default=-54.78, ge=-180, le=180)
    open_meteo_enabled: bool = True
    air_quality_enabled: bool = True
    flood_enabled: bool = True
    firms_enabled: bool = True
    copernicus_enabled: bool = False
    copernicus_wms_url: str | None = Field(default=None, max_length=500)
    copernicus_true_color_layer: str = Field(default="TRUE_COLOR", min_length=1, max_length=100)
    copernicus_ndvi_layer: str = Field(default="NDVI", min_length=1, max_length=100)
    copernicus_moisture_layer: str = Field(default="MOISTURE_INDEX", min_length=1, max_length=100)
    copernicus_burn_layer: str = Field(default="NBR_RAW", min_length=1, max_length=100)
    forestry_pest_enabled: bool = True
    sinarame_radar_enabled: bool = True
    refresh_minutes: int = Field(default=10, ge=2, le=180)
    fire_radius_km: float = Field(default=50, ge=1, le=500)
    operational_alert_min_level: SpaceAILevel = "R3"
    auto_activate_alerts: bool = False

    @model_validator(mode="after")
    def validate_misiones_location_and_copernicus(self):
        ensure_in_misiones(self.default_latitude, self.default_longitude)
        value = (self.copernicus_wms_url or "").strip().rstrip("/")
        if value:
            from urllib.parse import urlparse
            parsed = urlparse(value)
            if parsed.scheme != "https" or parsed.hostname != "sh.dataspace.copernicus.eu":
                raise ValueError("La URL WMS debe usar HTTPS y el dominio oficial sh.dataspace.copernicus.eu")
            if not parsed.path.startswith("/ogc/wms/") or not parsed.path.removeprefix("/ogc/wms/").strip("/"):
                raise ValueError("Usá la URL https://sh.dataspace.copernicus.eu/ogc/wms/INSTANCE_ID")
            self.copernicus_wms_url = value
        elif self.copernicus_enabled:
            raise ValueError("Para habilitar Copernicus primero cargá la URL WMS de una instancia propia")
        return self


class EnvironmentalSourceSettingsOut(EnvironmentalSourceSettingsIn):
    org_id: UUID
    firms_map_key_configured: bool = False
    copernicus_configured: bool = False
    updated_at: datetime


class CopernicusWmsTestIn(BaseModel):
    url: str = Field(min_length=20, max_length=500)

    @model_validator(mode="after")
    def validate_url(self):
        from urllib.parse import urlparse
        value = self.url.strip().rstrip("/")
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.hostname != "sh.dataspace.copernicus.eu" or not parsed.path.startswith("/ogc/wms/"):
            raise ValueError("Solo se permite una instancia WMS oficial de Copernicus Data Space")
        self.url = value
        return self


class CopernicusWmsTestOut(BaseModel):
    ok: bool
    service_title: str | None = None
    layers: list[str] = Field(default_factory=list)
    detail: str


class EnvironmentalIndexSnapshot(BaseModel):
    id: ThreatDomainId
    label: str = Field(min_length=2, max_length=120)
    level: SpaceAILevel
    score: float = Field(ge=0, le=100)
    value: float | None = None
    unit: str = Field(default="", max_length=120)
    status: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0, le=1)
    action: str = Field(default="", max_length=1500)
    health_impacts: list[str] = Field(default_factory=list, max_length=20)
    evidence: list[str] = Field(default_factory=list, max_length=30)


class EnvironmentalAlertSnapshot(BaseModel):
    id: str = Field(min_length=2, max_length=160)
    domain: ThreatDomainId
    level: SpaceAILevel
    severity: Literal["baja", "media", "alta", "critica"]
    title: str = Field(min_length=2, max_length=300)
    summary: str = Field(default="", max_length=1500)
    action: str = Field(default="", max_length=1500)
    source: str = Field(default="", max_length=500)
    confidence: float = Field(ge=0, le=1)


class EnvironmentalHotspotsSnapshot(BaseModel):
    count_48h: int = Field(default=0, ge=0, le=100000)
    high_confidence_count_48h: int = Field(default=0, ge=0, le=100000)
    maximum_frp_mw: float | None = Field(default=None, ge=0)
    nearest_distance_km: float | None = Field(default=None, ge=0)


class EnvironmentalSnapshot(BaseModel):
    methodology_version: str = Field(min_length=2, max_length=250)
    generated_at: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    overall_score: float = Field(ge=0, le=100)
    overall_level: SpaceAILevel
    overall_label: str = Field(min_length=1, max_length=120)
    observations: dict[str, float | None] = Field(default_factory=dict, max_length=100)
    indices: list[EnvironmentalIndexSnapshot] = Field(default_factory=list, max_length=30)
    alerts: list[EnvironmentalAlertSnapshot] = Field(default_factory=list, max_length=50)
    hotspots: EnvironmentalHotspotsSnapshot = Field(default_factory=EnvironmentalHotspotsSnapshot)
    sources: dict[str, str] = Field(default_factory=dict, max_length=30)
    limitations: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_misiones_location(self):
        ensure_in_misiones(self.latitude, self.longitude)
        return self


class EnvironmentalSnapshotRecordOut(BaseModel):
    id: UUID
    org_id: UUID
    created_by: UUID | None = None
    origin: str
    activated_alerts: int = 0
    snapshot: EnvironmentalSnapshot
    created_at: datetime
