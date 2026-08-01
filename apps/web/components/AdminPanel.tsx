"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { IS_DEMO, apiDelete, apiGet, apiPatch, apiPost } from "../app/lib/api";
import type {
  AdminSummary,
  AdminUser,
  AuditEvent,
  EnvironmentalSourceSettings,
  Org,
  RiskZone,
  RiskZoneKind,
  UserRole,
} from "../app/lib/types";
import AdminNotificationsPanel from "./AdminNotificationsPanel";
import SubscriptionPanel from "./SubscriptionPanel";
import TelemetryAdminPanel from "./TelemetryAdminPanel";
import { MISIONES_CENTER, MISIONES_MUNICIPALITIES, assertMisionesCoordinates, misionesLocationLabel, municipalityDepartment } from "../app/lib/misiones";

type Tab = "overview" | "messages" | "subscription" | "users" | "zones" | "telemetry" | "organization" | "sources" | "launch" | "audit";
type BoundaryStatus = { province: string; available: boolean; official: boolean; boundaries: Array<{ source: string; is_official: boolean; fetched_at?: string | null; area_km2?: number | string }> };
type CopernicusTestResult = { ok: boolean; provider: "process_api" | "wms" | "none"; configured: boolean; service_title: string | null; layers: string[]; detail: string };
type ZoneDraft = {
  name: string;
  kind: RiskZoneKind;
  lat: string;
  lon: string;
  radius_m: string;
};

const LEVELS = ["R0", "R1", "R2", "R3", "R4", "R5"] as const;
const EMPTY_ZONE: ZoneDraft = { name: "", kind: "general", lat: String(MISIONES_CENTER[0]), lon: String(MISIONES_CENTER[1]), radius_m: "2500" };
const ZONE_LABEL: Record<RiskZoneKind, string> = { incendio: "Incendio", hidrica: "Hídrica", general: "Multiamenaza" };

function ago(value: string | null): string {
  if (!value) return "sin registro";
  const seconds = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);
  if (seconds < 60) return `hace ${Math.round(seconds)} s`;
  if (seconds < 3600) return `hace ${Math.round(seconds / 60)} min`;
  if (seconds < 86400) return `hace ${Math.round(seconds / 3600)} h`;
  return `hace ${Math.round(seconds / 86400)} d`;
}

function metadataText(metadata: Record<string, unknown>): string {
  const entries = Object.entries(metadata || {});
  if (!entries.length) return "—";
  return entries.slice(0, 4).map(([key, value]) => `${key}: ${String(value)}`).join(" · ");
}

export default function AdminPanel({
  token,
  org,
  onOrgUpdate,
  onSourceSettingsUpdate,
}: {
  token: string;
  org: Org | null;
  onOrgUpdate: (value: Org) => void;
  onSourceSettingsUpdate?: (value: EnvironmentalSourceSettings) => void;
}) {
  const [tab, setTab] = useState<Tab>("overview");
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [zones, setZones] = useState<RiskZone[]>([]);
  const [settings, setSettings] = useState<EnvironmentalSourceSettings | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [boundaryStatus, setBoundaryStatus] = useState<BoundaryStatus | null>(null);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [copernicusTest, setCopernicusTest] = useState<CopernicusTestResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [newUser, setNewUser] = useState({ name: "", email: "", role: "operador" as UserRole, password: "" });
  const [zoneDraft, setZoneDraft] = useState<ZoneDraft>(EMPTY_ZONE);
  const [editingZoneId, setEditingZoneId] = useState<string | null>(null);
  const [orgDraft, setOrgDraft] = useState({ name: org?.name || "", primary_color: org?.primary_color || "#2E7D5B", baseline_response_s: String(org?.baseline_response_s || 3600), municipality: org?.municipality || "Posadas", department: org?.department || "Capital", territory_scope: org?.territory_scope || "municipal" });

  useEffect(() => {
    setOrgDraft({ name: org?.name || "", primary_color: org?.primary_color || "#2E7D5B", baseline_response_s: String(org?.baseline_response_s || 3600), municipality: org?.municipality || "Posadas", department: org?.department || "Capital", territory_scope: org?.territory_scope || "municipal" });
  }, [org]);

  const load = useCallback(async () => {
    const [nextSummary, nextUsers, nextZones, nextSettings, nextAudit, notificationCount] = await Promise.all([
      apiGet<AdminSummary>("/admin/summary", token),
      apiGet<AdminUser[]>("/admin/users", token),
      apiGet<RiskZone[]>("/zones", token),
      apiGet<EnvironmentalSourceSettings>("/admin/source-settings", token),
      apiGet<AuditEvent[]>("/admin/audit?limit=120", token),
      apiGet<{ unread: number }>("/admin/notifications/unread-count", token).catch(() => ({ unread: 0 })),
    ]);
    setSummary(nextSummary);
    setUsers(nextUsers);
    setZones(nextZones);
    setSettings(nextSettings);
    setAudit(nextAudit);
    setUnreadNotifications(notificationCount.unread);
    const nextBoundary = await apiGet<BoundaryStatus>("/territory/boundary-status", token).catch(() => null);
    setBoundaryStatus(nextBoundary);
  }, [token]);

  useEffect(() => { void load().catch((cause) => setError(cause instanceof Error ? cause.message : "No se pudo cargar el panel")); }, [load]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void apiGet<{ unread: number }>("/admin/notifications/unread-count", token)
        .then((value) => setUnreadNotifications(value.unread))
        .catch(() => undefined);
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [token]);

  const health = useMemo(() => {
    if (!summary) return 0;
    const devices = summary.devices_total ? summary.devices_online / summary.devices_total : 0;
    const users = summary.users_total ? summary.users_active / summary.users_total : 0;
    const rules = summary.rules_total ? summary.rules_enabled / summary.rules_total : 1;
    return Math.round((devices * .45 + users * .2 + rules * .2 + (summary.snapshots_24h ? .15 : 0)) * 100);
  }, [summary]);

  function message(text: string) {
    setNotice(text);
    setError("");
    window.setTimeout(() => setNotice(""), 4000);
  }

  async function syncOfficialBoundary() {
    setBusy(true); setError("");
    try {
      await apiPost("/territory/sync-georef", token, {});
      await load();
      message("Límite oficial de Misiones sincronizado desde GeoRef Argentina.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo sincronizar GeoRef");
    } finally { setBusy(false); }
  }

  async function createUser(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      await apiPost<AdminUser>("/admin/users", token, newUser);
      setNewUser({ name: "", email: "", role: "operador", password: "" });
      await load(); message("Usuario creado y registrado en la bitácora.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo crear el usuario"); }
    finally { setBusy(false); }
  }

  async function updateUser(user: AdminUser, changes: Partial<Pick<AdminUser, "name" | "role" | "is_active">>) {
    setBusy(true); setError("");
    try {
      await apiPatch(`/admin/users/${user.id}`, token, changes);
      await load(); message("Permisos actualizados.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo actualizar el usuario"); }
    finally { setBusy(false); }
  }

  async function deactivateUser(user: AdminUser) {
    if (!window.confirm(`Desactivar a ${user.name}? El historial se conserva.`)) return;
    setBusy(true); setError("");
    try { await apiDelete(`/admin/users/${user.id}`, token); await load(); message("Usuario desactivado."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo desactivar"); }
    finally { setBusy(false); }
  }

  function editZone(zone: RiskZone) {
    setEditingZoneId(zone.id);
    setZoneDraft({
      name: zone.name,
      kind: zone.kind,
      lat: String(zone.lat),
      lon: String(zone.lon),
      radius_m: String(zone.radius_m),
    });
  }

  function resetZone() {
    setEditingZoneId(null);
    setZoneDraft({
      ...EMPTY_ZONE,
      lat: String(settings?.default_latitude ?? EMPTY_ZONE.lat),
      lon: String(settings?.default_longitude ?? EMPTY_ZONE.lon),
    });
  }

  async function saveZone(event: React.FormEvent) {
    event.preventDefault();
    const payload = {
      name: zoneDraft.name.trim(),
      kind: zoneDraft.kind,
      lat: Number(zoneDraft.lat),
      lon: Number(zoneDraft.lon),
      radius_m: Number(zoneDraft.radius_m),
    };
    if (!payload.name || !Number.isFinite(payload.lat) || !Number.isFinite(payload.lon) || !Number.isFinite(payload.radius_m)) {
      setError("Completá nombre, coordenadas y radio con valores válidos.");
      return;
    }
    try { assertMisionesCoordinates(payload.lat, payload.lon); } catch (cause) { setError(cause instanceof Error ? cause.message : "La geocerca debe estar en Misiones."); return; }
    if (payload.radius_m < 50 || payload.radius_m > 100000) {
      setError("El radio operativo debe estar entre 50 m y 100 km.");
      return;
    }
    setBusy(true); setError("");
    try {
      if (editingZoneId) {
        await apiPatch<RiskZone>(`/zones/${editingZoneId}`, token, payload);
        message("Geocerca actualizada y vinculable desde el motor de reglas.");
      } else {
        await apiPost<RiskZone>("/zones", token, payload);
        message("Zona de riesgo creada.");
      }
      resetZone();
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo guardar la zona"); }
    finally { setBusy(false); }
  }

  async function deleteZone(zone: RiskZone) {
    if (!window.confirm(`Eliminar la zona “${zone.name}”? Las reglas vinculadas quedarán sin geocerca.`)) return;
    setBusy(true); setError("");
    try {
      await apiDelete(`/zones/${zone.id}`, token);
      if (editingZoneId === zone.id) resetZone();
      await load();
      message("Zona eliminada; la bitácora conserva el evento.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo eliminar la zona"); }
    finally { setBusy(false); }
  }

  async function saveOrganization(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      const value = await apiPatch<Org>("/admin/organization", token, {
        name: orgDraft.name,
        primary_color: orgDraft.primary_color,
        baseline_response_s: Number(orgDraft.baseline_response_s),
        municipality: orgDraft.municipality,
        department: orgDraft.department,
        territory_scope: orgDraft.territory_scope,
      });
      onOrgUpdate(value); await load(); message("Configuración institucional guardada.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo guardar la organización"); }
    finally { setBusy(false); }
  }

  async function testCopernicus() {
    if (!settings) return;
    const url = settings.copernicus_wms_url?.trim() || null;
    if (!settings.copernicus_use_system_default && !url) {
      setError("Para usar WMS propio cargá la URL de tu instancia Copernicus.");
      return;
    }
    setBusy(true); setError(""); setCopernicusTest(null);
    try {
      const result = await apiPost<CopernicusTestResult>("/copernicus/test", token, {
        provider: settings.copernicus_use_system_default ? "auto" : "wms",
        url,
      });
      setCopernicusTest(result);
      if (result.ok) message(`Copernicus ${result.provider === "process_api" ? "Process API" : "WMS"} respondió correctamente.`);
      else setError(result.detail);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo probar Copernicus");
    } finally { setBusy(false); }
  }

  async function saveSources(event: React.FormEvent) {
    event.preventDefault();
    if (!settings) return;
    try { assertMisionesCoordinates(settings.default_latitude, settings.default_longitude); } catch (cause) { setError(cause instanceof Error ? cause.message : "El centro de monitoreo debe estar en Misiones."); return; }
    setBusy(true); setError("");
    try {
      const {
        org_id: _orgId,
        firms_map_key_configured: _key,
        copernicus_configured: _copernicus,
        copernicus_provider: _provider,
        copernicus_process_configured: _processConfigured,
        copernicus_wms_configured: _wmsConfigured,
        copernicus_system_default: _systemDefault,
        copernicus_effective_wms_url: _effectiveWms,
        copernicus_last_test_at: _lastTestAt,
        copernicus_last_test_ok: _lastTestOk,
        copernicus_last_error: _lastError,
        copernicus_available_layers: _availableLayers,
        updated_at: _updated,
        ...rawPayload
      } = settings;
      const copernicusUrl = rawPayload.copernicus_wms_url?.trim() || null;
      const payload = {
        ...rawPayload,
        copernicus_wms_url: copernicusUrl,
        copernicus_true_color_layer: rawPayload.copernicus_true_color_layer.trim() || "TRUE_COLOR",
        copernicus_ndvi_layer: rawPayload.copernicus_ndvi_layer.trim() || "NDVI",
        copernicus_moisture_layer: rawPayload.copernicus_moisture_layer.trim() || "NDMI",
        copernicus_burn_layer: rawPayload.copernicus_burn_layer.trim() || "NBR",
      };
      const value = await apiPatch<EnvironmentalSourceSettings>("/admin/source-settings", token, payload);
      setSettings(value); onSourceSettingsUpdate?.(value); await load(); message("Política de fuentes y alertas actualizada.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo guardar la configuración"); }
    finally { setBusy(false); }
  }

  const tabs: Array<[Tab, string]> = [
    ["overview", "Control"], ["messages", `Mensajes${unreadNotifications ? ` (${unreadNotifications})` : ""}`],
    ["subscription", "Suscripción"], ["users", "Usuarios"], ["zones", "Geocercas"], ["telemetry", "Telemetría"], ["organization", "Organización"],
    ["sources", "Fuentes SpaceAI"], ["launch", "Lanzamiento"], ["audit", "Auditoría"],
  ];

  return (
    <div className="view admin-view">
      <div className="view-title-row admin-title">
        <div><span className="eyebrow">ADMIN CORE · ABM / CRUD</span><h2>Gobierno de la plataforma</h2><p className="sub">Usuarios, permisos, fuentes, parámetros operativos y trazabilidad.</p></div>
        <div className="admin-health"><span>HEALTH</span><strong>{health}%</strong><i><b style={{ width: `${health}%` }} /></i></div>
      </div>

      <nav className="admin-tabs" aria-label="Secciones administrativas">
        {tabs.map(([id, label]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>)}
      </nav>

      {error && <div className="workspace-message error" role="alert">{error}</div>}
      {notice && <div className="workspace-message success">{notice}</div>}

      {tab === "overview" && <section className="admin-overview">
        <div className="admin-summary-grid">
          <AdminMetric label="Usuarios activos" value={`${summary?.users_active ?? "—"}/${summary?.users_total ?? "—"}`} detail="identidades y roles" />
          <AdminMetric label="Nodos online" value={`${summary?.devices_online ?? "—"}/${summary?.devices_total ?? "—"}`} detail="red física" />
          <AdminMetric label="Geocercas" value={summary?.zones_total ?? "—"} detail="zonas operativas" />
          <AdminMetric label="Reglas activas" value={`${summary?.rules_enabled ?? "—"}/${summary?.rules_total ?? "—"}`} detail="motor operacional" />
          <AdminMetric label="Alertas activas" value={summary?.alerts_active ?? "—"} detail="requieren seguimiento" tone={(summary?.alerts_active || 0) > 3 ? "warn" : ""} />
          <AdminMetric label="Reportes pendientes" value={summary?.reports_pending ?? "—"} detail="moderación ciudadana" tone={(summary?.reports_pending || 0) ? "warn" : ""} />
          <AdminMetric label="Snapshots 24 h" value={summary?.snapshots_24h ?? "—"} detail="bitácora SpaceAI" />
        </div>
        <div className="admin-core-grid">
          <article className="admin-core-card neural"><span className="eyebrow">ÚLTIMO ESTADO</span><strong>{summary?.last_snapshot_level || "—"}</strong><b>{summary?.last_snapshot_score != null ? `HTI ${Math.round(summary.last_snapshot_score)}/100` : "sin snapshot"}</b><small>{ago(summary?.last_snapshot_at || null)}</small><div className="admin-orbit"><i /><i /><i /></div></article>
          <article className="admin-core-card"><span className="eyebrow">SEGURIDAD</span><h3>Control por organización</h3><p>Los recursos se filtran por <code>org_id</code>, los roles se validan en cada operación y toda modificación sensible genera un evento de auditoría.</p><div className="admin-checks"><span>● JWT + rol vivo</span><span>● usuarios desactivables</span><span>● enlace público revocable</span><span>● secretos fuera del frontend</span></div></article>
          <article className="admin-core-card"><span className="eyebrow">OPERACIÓN</span><h3>Automatización supervisada</h3><p>SpaceAI puede guardar snapshots automáticamente y elevar alertas desde un nivel mínimo configurable. La activación conserva fuente, metodología y evidencia.</p><button className="primary" onClick={() => setTab("sources")}>Configurar automatización</button></article>
        </div>
      </section>}

      {tab === "messages" && <AdminNotificationsPanel token={token} onRead={() => void load()} />}

      {tab === "subscription" && <SubscriptionPanel token={token} />}

      {tab === "users" && <section className="admin-section-grid">
        <form className="admin-form-card" onSubmit={createUser}>
          <div className="panel-heading"><span>01</span><div><h3>Alta de usuario</h3><p>Credencial inicial por contraseña; luego puede vincular Google.</p></div></div>
          <label>Nombre<input required minLength={2} value={newUser.name} onChange={(event) => setNewUser({ ...newUser, name: event.target.value })} /></label>
          <label>Correo<input required type="email" value={newUser.email} onChange={(event) => setNewUser({ ...newUser, email: event.target.value })} /></label>
          <div className="form-two"><label>Rol<select value={newUser.role} onChange={(event) => setNewUser({ ...newUser, role: event.target.value as UserRole })}><option value="admin">Administrador</option><option value="operador">Operador</option><option value="visualizador">Visualizador</option></select></label><label>Contraseña temporal<input required minLength={10} type="password" value={newUser.password} onChange={(event) => setNewUser({ ...newUser, password: event.target.value })} /></label></div>
          <button className="primary" disabled={busy}>Crear usuario</button>
        </form>
        <article className="admin-table-card">
          <div className="panel-heading"><span>02</span><div><h3>Identidades y permisos</h3><p>ABM con baja lógica para conservar trazabilidad.</p></div></div>
          <div className="admin-user-list">
            {users.map((user) => <div className={`admin-user-row ${user.is_active ? "" : "inactive"}`} key={user.id}>
              <div className="admin-avatar">{user.name.slice(0, 1).toUpperCase()}</div>
              <div><strong>{user.name}</strong><span>{user.email}</span><small>{user.auth_provider} · {user.email_verified ? "verificado" : "sin verificar"} · {ago(user.last_login_at)}</small></div>
              <select aria-label={`Rol de ${user.name}`} value={user.role} disabled={busy || !user.is_active} onChange={(event) => void updateUser(user, { role: event.target.value as UserRole })}><option value="admin">admin</option><option value="operador">operador</option><option value="visualizador">visualizador</option></select>
              <button className="sm" disabled={busy} onClick={() => void updateUser(user, { is_active: !user.is_active })}>{user.is_active ? "Pausar" : "Reactivar"}</button>
              {user.is_active && <button className="sm danger" disabled={busy} onClick={() => void deactivateUser(user)}>Baja</button>}
            </div>)}
          </div>
        </article>
      </section>}

      {tab === "telemetry" && <TelemetryAdminPanel token={token} zones={zones} onChanged={() => void load()} />}

      {tab === "zones" && <section className="admin-zone-layout">
        <form className="admin-form-card admin-zone-form" onSubmit={saveZone}>
          <div className="panel-heading"><span>01</span><div><h3>{editingZoneId ? "Editar geocerca" : "Nueva geocerca"}</h3><p>Círculo geoespacial persistido en PostGIS para filtrar reglas, incidentes y reportes.</p></div></div>
          <label>Nombre operativo<input required minLength={2} maxLength={120} value={zoneDraft.name} onChange={(event) => setZoneDraft({ ...zoneDraft, name: event.target.value })} placeholder="Microcuenca prioritaria" /></label>
          <div className="form-two">
            <label>Dominio<select value={zoneDraft.kind} onChange={(event) => setZoneDraft({ ...zoneDraft, kind: event.target.value as RiskZoneKind })}><option value="general">Multiamenaza</option><option value="incendio">Incendio</option><option value="hidrica">Hídrica</option></select></label>
            <label>Radio operativo (m)<input required type="number" min={50} max={100000} step={50} value={zoneDraft.radius_m} onChange={(event) => setZoneDraft({ ...zoneDraft, radius_m: event.target.value })} /></label>
          </div>
          <div className="form-two">
            <label>Latitud<input required type="number" min={-90} max={90} step="0.000001" value={zoneDraft.lat} onChange={(event) => setZoneDraft({ ...zoneDraft, lat: event.target.value })} /></label>
            <label>Longitud<input required type="number" min={-180} max={180} step="0.000001" value={zoneDraft.lon} onChange={(event) => setZoneDraft({ ...zoneDraft, lon: event.target.value })} /></label>
          </div>
          <div className={`zone-radar-preview ${zoneDraft.kind}`}>
            <span className="zone-radar-cross x" /><span className="zone-radar-cross y" />
            <i style={{ width: `${Math.min(92, Math.max(28, Number(zoneDraft.radius_m || 0) / 1000 * 12))}%`, aspectRatio: "1" }} />
            <b>{ZONE_LABEL[zoneDraft.kind]}</b>
            <small>{Number(zoneDraft.radius_m || 0).toLocaleString("es-AR")} m · {misionesLocationLabel(Number(zoneDraft.lat || 0), Number(zoneDraft.lon || 0))}</small>
          </div>
          <div className="modal-actions admin-zone-actions">
            {editingZoneId && <button type="button" onClick={resetZone}>Cancelar edición</button>}
            <button className="primary" disabled={busy}>{editingZoneId ? "Guardar geocerca" : "Crear geocerca"}</button>
          </div>
        </form>

        <article className="admin-table-card admin-zone-list-card">
          <div className="panel-heading"><span>02</span><div><h3>Territorio operacional</h3><p>{zones.length} zonas disponibles para el motor no-code y el mapa de comando.</p></div></div>
          <div className="admin-zone-list">
            {zones.map((zone) => <div className={`admin-zone-row ${zone.kind}`} key={zone.id}>
              <div className="zone-symbol"><i /><span /></div>
              <div><strong>{zone.name}</strong><span>{ZONE_LABEL[zone.kind]} · {(zone.radius_m / 1000).toLocaleString("es-AR", { maximumFractionDigits: 1 })} km</span><small>{misionesLocationLabel(zone.lat, zone.lon)}</small><small className="mono">{zone.lat.toFixed(5)}, {zone.lon.toFixed(5)}</small></div>
              <div className="zone-row-actions"><button className="sm" type="button" disabled={busy} onClick={() => editZone(zone)}>Editar</button><button className="sm danger" type="button" disabled={busy} onClick={() => void deleteZone(zone)}>Borrar</button></div>
            </div>)}
            {!zones.length && <div className="empty">No hay geocercas. Creá una para segmentar reglas y monitoreo territorial.</div>}
          </div>
          <div className="source-warning"><strong>PostGIS</strong><span>La API almacena centro, radio y polígono geográfico. Al eliminar una zona, las reglas conservan su definición pero quedan sin filtro espacial.</span></div>
        </article>
      </section>}

      {tab === "organization" && <form className="admin-form-card admin-org-form" onSubmit={saveOrganization}>
        <div className="panel-heading"><span>01</span><div><h3>Identidad institucional</h3><p>Datos usados en documentos, enlaces públicos y tableros.</p></div></div>
        <div className="form-two"><label>Nombre<input required value={orgDraft.name} onChange={(event) => setOrgDraft({ ...orgDraft, name: event.target.value })} /></label><label>Color institucional<div className="color-input"><input type="color" value={orgDraft.primary_color} onChange={(event) => setOrgDraft({ ...orgDraft, primary_color: event.target.value })} /><input pattern="^#[0-9A-Fa-f]{6}$" value={orgDraft.primary_color} onChange={(event) => setOrgDraft({ ...orgDraft, primary_color: event.target.value })} /></div></label></div>
        <div className="form-three"><label>Provincia<input value="Misiones" readOnly /></label><label>Municipio<select value={orgDraft.municipality} onChange={(event) => { const municipality = event.target.value; setOrgDraft({ ...orgDraft, municipality, department: municipalityDepartment(municipality) || "Capital" }); }}>{MISIONES_MUNICIPALITIES.map((item) => <option key={`${item.department}-${item.name}`} value={item.name}>{item.name}</option>)}</select></label><label>Departamento<input value={orgDraft.department} readOnly /></label></div>
        <div className="form-two"><label>Alcance<select value={orgDraft.territory_scope} onChange={(event) => setOrgDraft({ ...orgDraft, territory_scope: event.target.value as Org["territory_scope"] })}><option value="municipal">Municipal</option><option value="departamental">Departamental</option><option value="provincial">Provincial</option><option value="area_operativa">Área operativa</option></select></label><label>Baseline de respuesta (segundos)<input required min={60} max={604800} type="number" value={orgDraft.baseline_response_s} onChange={(event) => setOrgDraft({ ...orgDraft, baseline_response_s: event.target.value })} /></label></div>
        <div className="admin-org-preview" style={{ "--org-color": orgDraft.primary_color } as React.CSSProperties}><span>ECO/NEXO</span><strong>{orgDraft.name || "Organización"}</strong><small>{org?.vertical} · baseline {orgDraft.baseline_response_s || "—"} s</small></div>
        <button className="primary" disabled={busy}>Guardar organización</button>
      </form>}

      {tab === "sources" && settings && <form className="admin-form-card admin-sources" onSubmit={saveSources}>
        <div className="panel-heading"><span>01</span><div><h3>Fuentes ambientales y automatización</h3><p>La configuración no convierte datos de modelo en lecturas de sensor; controla su uso como contexto.</p></div></div>
        <div className="source-switch-grid">
          <SourceToggle label="Open-Meteo Forecast" detail="temperatura, humedad, lluvia, suelo y viento" checked={settings.open_meteo_enabled} onChange={(value) => setSettings({ ...settings, open_meteo_enabled: value })} />
          <SourceToggle label="Copernicus CAMS" detail="PM2.5, AQI, gases, aerosoles e índice UV" checked={settings.air_quality_enabled} onChange={(value) => setSettings({ ...settings, air_quality_enabled: value })} />
          <SourceToggle label="GloFAS / Flood" detail="caudal modelado y tendencia hidrológica" checked={settings.flood_enabled} onChange={(value) => setSettings({ ...settings, flood_enabled: value })} />
          <SourceToggle label="NASA FIRMS" detail={`focos térmicos · MAP_KEY ${settings.firms_map_key_configured ? "configurada" : "pendiente / sin datos reales"}`} checked={settings.firms_enabled} onChange={(value) => setSettings({ ...settings, firms_enabled: value })} />
          <SourceToggle label="Copernicus Sentinel-2" detail={settings.copernicus_configured ? `${settings.copernicus_provider === "process_api" ? "Process API" : "WMS"} configurado` : "predeterminado; faltan credenciales OAuth o INSTANCE_ID"} checked={settings.copernicus_enabled} onChange={(value) => setSettings({ ...settings, copernicus_enabled: value })} />
          <SourceToggle label="Sanidad forestal" detail="módulo preventivo para recorridas, trampas y reportes fitosanitarios" checked={settings.forestry_pest_enabled} onChange={(value) => setSettings({ ...settings, forestry_pest_enabled: value })} />
          <SourceToggle label="Radar SINARAME" detail="contexto meteorológico regional; no identifica especies de plagas" checked={settings.sinarame_radar_enabled} onChange={(value) => setSettings({ ...settings, sinarame_radar_enabled: value })} />
        </div>
        <section className="copernicus-config-card">
          <div><span className="eyebrow">COPERNICUS PREDETERMINADO · SENTINEL-2 L2A</span><h3>Imágenes e índices satelitales</h3><p>EcoNexo usa Process API por defecto cuando las credenciales OAuth están cargadas en Render. La alternativa WMS queda disponible para organizaciones con INSTANCE_ID propio.</p></div>
          <div className="source-warning"><strong>Proveedor efectivo: {settings.copernicus_provider === "process_api" ? "Process API" : settings.copernicus_provider === "wms" ? "WMS" : "pendiente"}</strong><span>{settings.copernicus_configured ? "Disponible para Color natural, NDVI, NDMI de humedad y NBR de quema." : "Cargá COPERNICUS_CLIENT_ID y COPERNICUS_CLIENT_SECRET en la API de Render, o desactivá el valor predeterminado y usá WMS propio."}</span></div>
          <SourceToggle label="Usar Copernicus predeterminado del sistema" detail="recomendado: OAuth y Process API administrados por el backend; los secretos nunca llegan al navegador" checked={settings.copernicus_use_system_default} onChange={(value) => { setCopernicusTest(null); setSettings({ ...settings, copernicus_use_system_default: value }); }} />
          <label>URL WMS propia (opcional)<input type="url" disabled={settings.copernicus_use_system_default} placeholder="https://sh.dataspace.copernicus.eu/ogc/wms/INSTANCE_ID" value={settings.copernicus_wms_url || ""} onChange={(event) => { setCopernicusTest(null); setSettings({ ...settings, copernicus_wms_url: event.target.value || null }); }} /></label>
          <div className="form-four copernicus-layers">
            <label>Color natural<input disabled={settings.copernicus_use_system_default} value={settings.copernicus_true_color_layer} onChange={(event) => setSettings({ ...settings, copernicus_true_color_layer: event.target.value })} /></label>
            <label>Vegetación NDVI<input disabled={settings.copernicus_use_system_default} value={settings.copernicus_ndvi_layer} onChange={(event) => setSettings({ ...settings, copernicus_ndvi_layer: event.target.value })} /></label>
            <label>Humedad NDMI<input disabled={settings.copernicus_use_system_default} value={settings.copernicus_moisture_layer} onChange={(event) => setSettings({ ...settings, copernicus_moisture_layer: event.target.value })} /></label>
            <label>Quema NBR<input disabled={settings.copernicus_use_system_default} value={settings.copernicus_burn_layer} onChange={(event) => setSettings({ ...settings, copernicus_burn_layer: event.target.value })} /></label>
          </div>
          <div className="copernicus-test-row"><button type="button" disabled={busy || (!settings.copernicus_use_system_default && !settings.copernicus_wms_url)} onClick={() => void testCopernicus()}>Probar Copernicus</button><span className={copernicusTest?.ok ? "ok" : copernicusTest ? "bad" : ""}>{copernicusTest?.detail || settings.copernicus_last_error || "La prueba usa una imagen pequeña de Misiones o GetCapabilities, según el proveedor efectivo."}</span></div>
          {copernicusTest?.ok && copernicusTest.layers.length > 0 && <div className="copernicus-layer-results"><strong>Capas disponibles</strong><div>{copernicusTest.layers.slice(0, 24).map((layer) => <code key={layer}>{layer}</code>)}</div></div>}
        </section>
        <div className="form-three"><label>Latitud base<input type="number" step="0.00001" min={-90} max={90} value={settings.default_latitude} onChange={(event) => setSettings({ ...settings, default_latitude: Number(event.target.value) })} /></label><label>Longitud base<input type="number" step="0.00001" min={-180} max={180} value={settings.default_longitude} onChange={(event) => setSettings({ ...settings, default_longitude: Number(event.target.value) })} /></label><label>Refresco (min)<input type="number" min={2} max={180} value={settings.refresh_minutes} onChange={(event) => setSettings({ ...settings, refresh_minutes: Number(event.target.value) })} /></label></div>
        <div className="form-three"><label>Radio FIRMS (km)<input type="number" min={1} max={500} value={settings.fire_radius_km} onChange={(event) => setSettings({ ...settings, fire_radius_km: Number(event.target.value) })} /></label><label>Nivel mínimo para alertar<select value={settings.operational_alert_min_level} onChange={(event) => setSettings({ ...settings, operational_alert_min_level: event.target.value as EnvironmentalSourceSettings["operational_alert_min_level"] })}>{LEVELS.map((level) => <option key={level}>{level}</option>)}</select></label><label className="toggle-field"><span>Autoactivar alertas</span><button type="button" className={`switch ${settings.auto_activate_alerts ? "on" : ""}`} onClick={() => setSettings({ ...settings, auto_activate_alerts: !settings.auto_activate_alerts })}><i /></button></label></div>
        <div className="source-warning"><strong>Control humano recomendado</strong><span>Para organismos públicos, comenzar con autoactivación deshabilitada, registrar el snapshot y validar antes de convertirlo en alerta operacional.</span></div>
        <button className="primary" disabled={busy}>Guardar política de fuentes</button>
      </form>}

      {tab === "launch" && <section className="admin-launch-grid">
        <article className="admin-form-card">
          <div className="panel-heading"><span>01</span><div><h3>Control de lanzamiento Misiones</h3><p>Puerta de salida técnica, territorial, legal y operativa.</p></div></div>
          <div className="launch-checklist">
            <LaunchCheck ok={org?.province === "Misiones" && Boolean(org?.municipality)} title="Territorio institucional" detail={`${org?.municipality || "municipio pendiente"} · ${org?.department || "departamento pendiente"}`} />
            <LaunchCheck ok={Boolean(boundaryStatus?.official)} title="Límite oficial GeoRef" detail={boundaryStatus?.official ? `Sincronizado · ${boundaryStatus.boundaries[0]?.source || "GeoRef Argentina"}` : "Pendiente: usar el botón de sincronización antes del lanzamiento"} />
            <LaunchCheck ok={Boolean(settings && settings.default_latitude && settings.default_longitude)} title="Centro de monitoreo" detail={settings ? misionesLocationLabel(settings.default_latitude, settings.default_longitude) : "sin configuración"} />
            <LaunchCheck ok={Boolean(settings?.firms_map_key_configured)} title="NASA FIRMS productivo" detail={settings?.firms_map_key_configured ? "MAP_KEY configurada" : "pendiente: no publicar focos demo como reales"} />
            <LaunchCheck ok={Boolean(settings?.copernicus_enabled && settings?.copernicus_configured)} title="Copernicus Sentinel-2" detail={settings?.copernicus_configured ? `${settings.copernicus_provider === "process_api" ? "Process API" : "WMS"} operativo` : "pendiente: credenciales OAuth en Render o INSTANCE_ID WMS"} />
            <LaunchCheck ok={Boolean(settings?.forestry_pest_enabled)} title="Sanidad forestal norte" detail={settings?.sinarame_radar_enabled ? "San Antonio + contexto de radar Bernardo de Irigoyen" : "módulo activo sin contexto SINARAME"} />
            <LaunchCheck ok={Boolean(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID)} title="Ingreso con Google" detail={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ? "OAuth visible" : "opcional, sin configurar"} />
            <LaunchCheck ok={Boolean(process.env.NEXT_PUBLIC_LEGAL_EMAIL)} title="Canal legal y privacidad" detail={process.env.NEXT_PUBLIC_LEGAL_EMAIL || "NEXT_PUBLIC_LEGAL_EMAIL pendiente"} />
            <LaunchCheck ok={Boolean(process.env.NEXT_PUBLIC_API_URL?.startsWith("https://"))} title="API pública con TLS" detail={process.env.NEXT_PUBLIC_API_URL || "URL pública pendiente"} />
            <LaunchCheck ok={(summary?.users_active || 0) >= 2} title="Continuidad operativa" detail="Se recomiendan al menos dos administradores/operadores activos" />
            <LaunchCheck ok={Boolean(summary?.snapshots_24h)} title="Prueba de extremo a extremo" detail="Snapshot, alerta, moderación e informe deben verificarse antes de abrir" />
          </div>
          <button type="button" className="secondary" disabled={IS_DEMO || busy || Boolean(boundaryStatus?.official)} onClick={() => void syncOfficialBoundary()}>{IS_DEMO ? "Disponible en entorno productivo" : boundaryStatus?.official ? "GeoRef sincronizado" : "Sincronizar límite oficial de Misiones"}</button>
        </article>
        <article className="admin-table-card">
          <div className="panel-heading"><span>02</span><div><h3>Protocolo provincial de publicación</h3><p>Condiciones mínimas para evitar falsas alertas.</p></div></div>
          <ol className="launch-protocol"><li>Las señales fuera de Misiones se descartan antes de alimentar KPIs y mapas.</li><li>Un punto caliente satelital no equivale a incendio confirmado.</li><li>Las alertas R3-R5 requieren revisión humana, fuente y hora de corte.</li><li>Ante fuego o humo visible, el canal inmediato comunicado es el 911.</li><li>Los informes deben identificar método, fórmulas, límites, coordenadas y responsable de aprobación.</li><li>El lanzamiento público queda bloqueado hasta completar identidad legal, backups, monitoreo y pruebas de restauración.</li></ol>
        </article>
      </section>}

      {tab === "audit" && <article className="admin-table-card audit-card">
        <div className="panel-heading"><span>01</span><div><h3>Bitácora inmutable de acciones</h3><p>Últimos eventos administrativos y operativos.</p></div></div>
        <div className="audit-list"><div className="audit-row head"><span>Fecha</span><span>Actor</span><span>Acción</span><span>Recurso</span><span>Detalle</span></div>{audit.map((event) => <div className="audit-row" key={event.id}><span className="mono">{new Date(event.created_at).toLocaleString("es-AR")}</span><strong>{event.actor_name || "sistema"}</strong><span>{event.action}</span><span>{event.resource}</span><small>{metadataText(event.metadata)}</small></div>)}</div>
      </article>}
    </div>
  );
}

function LaunchCheck({ ok, title, detail }: { ok: boolean; title: string; detail: string }) {
  return <div className={`launch-check ${ok ? "ok" : "pending"}`}><span>{ok ? "✓" : "!"}</span><div><strong>{title}</strong><small>{detail}</small></div></div>;
}

function AdminMetric({ label, value, detail, tone = "" }: { label: string; value: string | number; detail: string; tone?: string }) {
  return <article className={`admin-metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small><i /></article>;
}

function SourceToggle({ label, detail, checked, onChange }: { label: string; detail: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label className={`source-toggle ${checked ? "enabled" : ""}`}><div><strong>{label}</strong><small>{detail}</small></div><button type="button" className={`switch ${checked ? "on" : ""}`} aria-pressed={checked} onClick={() => onChange(!checked)}><i /></button></label>;
}
