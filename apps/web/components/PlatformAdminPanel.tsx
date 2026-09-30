"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPatch, apiPost, clearSession, getSession } from "../app/lib/api";
import type {
  PlatformAudit,
  PlatformOrganization,
  PlatformSummary,
  PlatformUser,
  Session,
  UserRole,
} from "../app/lib/types";
import CircuitBackdrop from "./CircuitBackdrop";
import SubscriptionPanel from "./SubscriptionPanel";

type Tab = "overview" | "users" | "organizations" | "subscriptions" | "audit";

function dateLabel(value: string | null): string {
  if (!value) return "sin ingreso";
  return new Date(value).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });
}

function metadataLabel(value: Record<string, unknown>): string {
  const entries = Object.entries(value || {}).slice(0, 4);
  return entries.length ? entries.map(([key, item]) => `${key}: ${String(item)}`).join(" · ") : "—";
}

/**
 * wa.me solo acepta dígitos: sin +, espacios ni separadores.
 * En Argentina los móviles se marcan con un 9 entre el código de país y el de
 * área (+54 9 376 ...). Si el número llegó sin ese 9, el enlace no resuelve.
 */
function whatsappLink(phone: string): string {
  const digits = phone.replace(/[^0-9]/g, "");
  const normalized = digits.startsWith("54") && !digits.startsWith("549")
    ? `549${digits.slice(2)}`
    : digits;
  return `https://wa.me/${normalized}`;
}

export default function PlatformAdminPanel() {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [summary, setSummary] = useState<PlatformSummary | null>(null);
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [organizations, setOrganizations] = useState<PlatformOrganization[]>([]);
  const [organizationCatalog, setOrganizationCatalog] = useState<PlatformOrganization[]>([]);
  const [audit, setAudit] = useState<PlatformAudit[]>([]);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editingUser, setEditingUser] = useState<PlatformUser | null>(null);
  const [editDraft, setEditDraft] = useState({ name: "", email: "", phone: "", role: "admin" as UserRole });
  const [userDraft, setUserDraft] = useState({ org_id: "", name: "", email: "", role: "operador" as UserRole, temporary_password: "" });

  const token = session?.access_token || "";

  const load = useCallback(async (accessToken: string, term = "") => {
    const query = encodeURIComponent(term.trim());
    const [nextSummary, nextUsers, nextOrganizations, nextOrganizationCatalog, nextAudit] = await Promise.all([
      apiGet<PlatformSummary>("/platform/summary", accessToken),
      apiGet<PlatformUser[]>(`/platform/users?limit=250&search=${query}`, accessToken),
      apiGet<PlatformOrganization[]>(`/platform/organizations?limit=250&search=${query}`, accessToken),
      apiGet<PlatformOrganization[]>("/platform/organizations?limit=500", accessToken),
      apiGet<PlatformAudit[]>("/platform/audit?limit=180", accessToken),
    ]);
    setSummary(nextSummary);
    setUsers(nextUsers);
    setOrganizations(nextOrganizations);
    setOrganizationCatalog(nextOrganizationCatalog);
    setAudit(nextAudit);
    setUserDraft((current) => current.org_id || !nextOrganizationCatalog.length ? current : { ...current, org_id: nextOrganizationCatalog[0].id });
  }, []);

  useEffect(() => {
    const current = getSession();
    if (!current) {
      router.replace("/login");
      return;
    }
    if (current.must_change_password) {
      router.replace("/cambiar-contrasena");
      return;
    }
    if (!current.platform_admin || current.role !== "admin") {
      router.replace("/dashboard");
      return;
    }
    setSession(current);
    void load(current.access_token).catch((cause) => setError(cause instanceof Error ? cause.message : "No se pudo abrir la consola"));
  }, [load, router]);

  const activeRate = useMemo(() => {
    if (!summary?.users_total) return 0;
    return Math.round(summary.users_active / summary.users_total * 100);
  }, [summary]);

  function flash(message: string) {
    setNotice(message);
    setError("");
    globalThis.setTimeout(() => setNotice(""), 4500);
  }

  async function reload(term = search) {
    if (!token) return;
    setBusy(true); setError("");
    try { await load(token, term); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo actualizar la consola"); }
    finally { setBusy(false); }
  }

  function generateTemporaryPassword(): string {
    const bytes = new Uint32Array(4);
    globalThis.crypto.getRandomValues(bytes);
    return `EcoNexo-${Array.from(bytes).map((value) => value.toString(36)).join("-")}-9`;
  }

  async function createUser(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !userDraft.org_id) return;
    if (userDraft.temporary_password.length < 12 || !/[A-Za-zÁÉÍÓÚáéíóúÑñ]/.test(userDraft.temporary_password) || !/\d/.test(userDraft.temporary_password)) {
      setError("La contraseña temporal debe tener al menos 12 caracteres, una letra y un número.");
      return;
    }
    setBusy(true); setError("");
    try {
      await apiPost("/platform/users", token, userDraft);
      setUserDraft((current) => ({ ...current, name: "", email: "", role: "operador", temporary_password: "" }));
      await load(token, search);
      flash("Usuario creado con cambio obligatorio de contraseña.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo crear el usuario"); }
    finally { setBusy(false); }
  }

  async function updateUser(item: PlatformUser, changes: { name?: string; email?: string; phone?: string; role?: UserRole; is_active?: boolean }) {
    if (!token) return false;
    setBusy(true); setError("");
    try {
      await apiPatch(`/platform/users/${item.id}`, token, changes);
      await load(token, search);
      flash("Usuario actualizado en la auditoría global.");
      return true;
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo actualizar el usuario"); return false; }
    finally { setBusy(false); }
  }

  function editUser(item: PlatformUser) {
    setEditingUser(item);
    setEditDraft({ name: item.name, email: item.email, phone: item.phone || "", role: item.role });
  }

  async function saveUser(event: React.FormEvent) {
    event.preventDefault();
    if (!editingUser) return;
    if (await updateUser(editingUser, { ...editDraft, name: editDraft.name.trim(), email: editDraft.email.trim() })) setEditingUser(null);
  }

  async function editContact(item: PlatformOrganization) {
    if (!item.contact_email) return;
    setBusy(true); setError("");
    try {
      const matches = await apiGet<PlatformUser[]>(`/platform/users?search=${encodeURIComponent(item.contact_email)}`, token);
      const contact = matches.find((entry) => entry.org_id === item.id && entry.email === item.contact_email);
      if (!contact) throw new Error("No se encontró el contacto. Buscalo desde Usuarios.");
      editUser(contact);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo cargar el contacto"); }
    finally { setBusy(false); }
  }

  async function resetPassword(item: PlatformUser) {
    if (!token) return;
    const temporary = window.prompt(`Contraseña temporal para ${item.email}\nMínimo 12 caracteres, una letra y un número.`);
    if (!temporary) return;
    if (temporary.length < 12 || !/[A-Za-zÁÉÍÓÚáéíóúÑñ]/.test(temporary) || !/\d/.test(temporary)) {
      setError("La contraseña temporal no cumple los requisitos mínimos.");
      return;
    }
    if (!window.confirm(`Restablecer el acceso de ${item.email}? Deberá cambiar la contraseña al ingresar.`)) return;
    setBusy(true); setError("");
    try {
      await apiPost(`/platform/users/${item.id}/reset-password`, token, { temporary_password: temporary });
      await load(token, search);
      flash("Contraseña temporal asignada; el cambio será obligatorio.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo restablecer la contraseña"); }
    finally { setBusy(false); }
  }

  async function renameOrganization(item: PlatformOrganization) {
    if (!token) return;
    const name = window.prompt("Nombre de la organización", item.name)?.trim();
    if (!name || name === item.name) return;
    setBusy(true); setError("");
    try {
      await apiPatch(`/platform/organizations/${item.id}`, token, { name });
      await load(token, search);
      flash("Nombre de organización actualizado.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo renombrar la organización"); }
    finally { setBusy(false); }
  }

  async function toggleOrganization(item: PlatformOrganization) {
    const verb = item.is_active ? "Suspender" : item.access_status === "pending" ? "Aprobar el acceso de" : "Reactivar";
    if (!token || !window.confirm(`${verb} la organización ${item.name}?`)) return;
    setBusy(true); setError("");
    try {
      await apiPatch(`/platform/organizations/${item.id}`, token, { is_active: !item.is_active });
      await load(token, search);
      flash(item.is_active ? "Organización suspendida." : item.access_status === "pending" ? "Acceso aprobado. La organización ya puede ingresar." : "Organización reactivada.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo actualizar la organización"); }
    finally { setBusy(false); }
  }

  if (!session) return <main className="platform-console-loading">Validando acceso privado…</main>;

  return (
    <main className="platform-console">
      <CircuitBackdrop dense />
      <header className="platform-console-header">
        <div>
          <span className="eyebrow">ECO/NEXO · CONSOLA PRIVADA</span>
          <h1>Administración general de plataforma</h1>
          <p>Organizaciones, identidades, licencias y trazabilidad global.</p>
        </div>
        <div className="platform-admin-account">
          <strong>{session.name}</strong><span>{session.email}</span>
          <div><button onClick={() => router.push("/dashboard")}>Centro operativo</button><button onClick={() => { clearSession(); router.replace("/login"); }}>Salir</button></div>
        </div>
      </header>

      <nav className="platform-console-tabs" aria-label="Consola general">
        {([
          ["overview", "Resumen"], ["users", "Usuarios"], ["organizations", "Organizaciones"],
          ["subscriptions", "Licencias"], ["audit", "Auditoría"],
        ] as Array<[Tab, string]>).map(([id, label]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>)}
      </nav>

      {error && <div className="workspace-message error" role="alert">{error}</div>}
      {notice && <div className="workspace-message success">{notice}</div>}

      {editingUser && <form className="platform-user-create platform-edit-user" onSubmit={saveUser} aria-label="Editar usuario">
        <div><span className="eyebrow">{editingUser.org_name}</span><h2>Editar usuario y contacto</h2><p>El rol Administrador habilita Admin Core. Cambiar el correo cierra las sesiones anteriores y desvincula el acceso anterior con Google.</p></div>
        <label>Nombre del usuario<input required minLength={2} maxLength={120} value={editDraft.name} onChange={(event) => setEditDraft({ ...editDraft, name: event.target.value })} /></label>
        <label>Correo de acceso<input required type="email" value={editDraft.email} onChange={(event) => setEditDraft({ ...editDraft, email: event.target.value })} /></label>
        <label>Teléfono de contacto<input type="tel" maxLength={32} value={editDraft.phone} onChange={(event) => setEditDraft({ ...editDraft, phone: event.target.value })} /></label>
        <label>Permisos<select value={editDraft.role} onChange={(event) => setEditDraft({ ...editDraft, role: event.target.value as UserRole })}><option value="admin">Administrador · Admin Core</option><option value="operador">Operador</option><option value="visualizador">Visualizador</option></select></label>
        <div className="platform-edit-actions"><button className="primary" disabled={busy}>Guardar cambios</button><button type="button" disabled={busy} onClick={() => setEditingUser(null)}>Cancelar</button><button type="button" disabled={busy} onClick={() => void resetPassword(editingUser)}>Restablecer clave</button></div>
      </form>}

      {tab === "overview" && <>
        <section className="platform-metrics">
          <article><span>Organizaciones</span><strong>{summary?.organizations_active ?? "—"}<small> / {summary?.organizations_total ?? "—"}</small></strong><i><b style={{ width: `${summary?.organizations_total ? summary.organizations_active / summary.organizations_total * 100 : 0}%` }} /></i></article>
          <article><span>Usuarios activos</span><strong>{summary?.users_active ?? "—"}<small> / {summary?.users_total ?? "—"}</small></strong><i><b style={{ width: `${activeRate}%` }} /></i></article>
          <article><span>Admins generales</span><strong>{summary?.platform_admins ?? "—"}</strong><small>correos autorizados</small></article>
          <article><span>Solicitudes pendientes</span><strong>{summary?.pending_license_requests ?? "—"}</strong><small>licencias comerciales</small></article>
          <article><span>Ingresos 24 h</span><strong>{summary?.logins_24h ?? "—"}</strong><small>actividad reciente</small></article>
        </section>
        <section className="platform-overview-grid">
          <article><span className="eyebrow">CONTROL GLOBAL</span><h2>Separación por organización</h2><p>El panel normal conserva el filtro por <code>org_id</code>. Esta consola utiliza endpoints exclusivos protegidos por el correo configurado en <code>PLATFORM_ADMIN_EMAILS</code>.</p></article>
          <article><span className="eyebrow">CREDENCIALES</span><h2>Cambio obligatorio</h2><p>Las cuentas creadas o restablecidas con contraseña temporal quedan bloqueadas hasta establecer una clave privada.</p></article>
          <article><span className="eyebrow">TRAZABILIDAD</span><h2>Acciones auditadas</h2><p>Altas, suspensiones, cambios de rol, restablecimientos y licencias dejan un evento con actor, organización y fecha.</p></article>
        </section>
      </>}

      {(tab === "users" || tab === "organizations") && <form className="platform-search" onSubmit={(event) => { event.preventDefault(); void reload(); }}>
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar nombre, correo, organización o municipio" />
        <button className="primary" disabled={busy}>Buscar</button>
        <button type="button" disabled={busy} onClick={() => { setSearch(""); void reload(""); }}>Limpiar</button>
      </form>}

      {tab === "users" && <section className="platform-users-layout">
        <form className="platform-user-create" onSubmit={createUser}>
          <div><span className="eyebrow">ALTA GLOBAL</span><h2>Crear usuario</h2><p>La credencial es temporal y deberá cambiarse en el primer ingreso.</p></div>
          <label>Organización<select required value={userDraft.org_id} onChange={(event) => setUserDraft({ ...userDraft, org_id: event.target.value })}>{organizationCatalog.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Nombre<input required minLength={2} value={userDraft.name} onChange={(event) => setUserDraft({ ...userDraft, name: event.target.value })} /></label>
          <label>Correo<input required type="email" value={userDraft.email} onChange={(event) => setUserDraft({ ...userDraft, email: event.target.value })} /></label>
          <label>Rol<select value={userDraft.role} onChange={(event) => setUserDraft({ ...userDraft, role: event.target.value as UserRole })}><option value="admin">Administrador</option><option value="operador">Operador</option><option value="visualizador">Visualizador</option></select></label>
          <label>Contraseña temporal<div className="platform-password-draft"><input required minLength={12} type="text" value={userDraft.temporary_password} onChange={(event) => setUserDraft({ ...userDraft, temporary_password: event.target.value })} /><button type="button" onClick={() => setUserDraft({ ...userDraft, temporary_password: generateTemporaryPassword() })}>Generar</button></div></label>
          <button className="primary" disabled={busy || !userDraft.org_id}>Crear usuario</button>
        </form>
        <div className="platform-table-card">
        <div className="platform-table-title"><h2>Usuarios globales</h2><span>{users.length} resultados</span></div>
        <div className="platform-user-table">
          <div className="head"><span>Identidad</span><span>Organización</span><span>Rol</span><span>Estado</span><span>Acciones</span></div>
          {users.map((item) => <div key={item.id} className={!item.is_active || !item.organization_active ? "inactive" : ""}>
            <span><strong>{item.name}</strong><small>{item.email}</small><small>{item.phone || "Sin teléfono"}</small><small>{item.auth_provider} · {dateLabel(item.last_login_at)}</small></span>
            <span><strong>{item.org_name}</strong><small>{item.organization_active ? "organización activa" : "organización suspendida"}</small></span>
            <span><select value={item.role} disabled={busy} onChange={(event) => void updateUser(item, { role: event.target.value as UserRole })}><option value="admin">admin</option><option value="operador">operador</option><option value="visualizador">visualizador</option></select></span>
            <span><b className={item.is_active ? "status-on" : "status-off"}>{item.is_active ? "Activo" : "Pausado"}</b>{item.must_change_password && <small className="status-warn">cambio de clave pendiente</small>}</span>
            <span className="actions"><button disabled={busy} onClick={() => editUser(item)}>Editar datos</button><button disabled={busy} onClick={() => void updateUser(item, { is_active: !item.is_active })}>{item.is_active ? "Pausar" : "Reactivar"}</button><button disabled={busy} onClick={() => void resetPassword(item)}>Restablecer clave</button></span>
          </div>)}
        </div>
        </div>
      </section>}

      {tab === "organizations" && <section className="platform-table-card">
        <div className="platform-table-title"><h2>Organizaciones</h2><span>{organizations.length} resultados</span></div>
        <div className="platform-org-console">
          {organizations.map((item) => <article key={item.id} className={item.access_status === "pending" ? "pending" : item.is_active ? "" : "inactive"}>
            <div>
              <strong>{item.name}</strong>
              <span>{item.municipality || item.province} · {item.vertical}</span>
              <small>{item.slug}</small>
              {item.access_status === "pending" && <b className="status-warn">Alta pendiente de aprobación</b>}
            </div>
            <div>
              <strong>{item.contact_name || "Sin contacto"}</strong>
              <span>{item.contact_email || "—"}</span>
              {item.contact_phone
                ? <a className="platform-org-whatsapp" href={whatsappLink(item.contact_phone)} target="_blank" rel="noreferrer">WhatsApp {item.contact_phone}</a>
                : <small>sin teléfono registrado</small>}
            </div>
            <div><strong>{item.users_active}/{item.users_total}</strong><span>usuarios activos</span></div>
            <div><strong>{item.plan_name || "Sin licencia"}</strong><span>{item.subscription_status || "sin estado"}</span></div>
            <div className="platform-org-actions"><button disabled={busy} onClick={() => void renameOrganization(item)}>Renombrar</button><button disabled={busy || !item.contact_email} onClick={() => void editContact(item)}>Editar contacto</button><button disabled={busy} className={item.is_active ? "danger" : ""} onClick={() => void toggleOrganization(item)}>{item.is_active ? "Suspender" : item.access_status === "pending" ? "Aprobar acceso" : "Reactivar"}</button></div>
          </article>)}
        </div>
      </section>}

      {tab === "subscriptions" && <SubscriptionPanel token={token} />}

      {tab === "audit" && <section className="platform-table-card">
        <div className="platform-table-title"><h2>Auditoría global</h2><span>últimos {audit.length} eventos</span></div>
        <div className="platform-audit-list">
          {audit.map((item) => <article key={item.id}><time>{dateLabel(item.created_at)}</time><div><strong>{item.action} · {item.resource}</strong><span>{item.org_name || "plataforma"} · {item.actor_name || "sistema"}</span><small>{metadataLabel(item.metadata)}</small></div></article>)}
        </div>
      </section>}
    </main>
  );
}
