"""Contratos de API (Pydantic v2). Validacion estricta de entrada/salida."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# --- Auth ---
class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    org_id: UUID
    role: str
    name: str


# --- Orgs ---
class OrgOut(BaseModel):
    id: UUID
    name: str
    slug: str
    vertical: str
    primary_color: str
    baseline_response_s: int


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
    # credenciales MQTT mostradas una sola vez
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
