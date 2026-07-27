"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../app/lib/api";
import type { AdminNotification } from "../app/lib/types";

function metadataSummary(metadata: Record<string, unknown>): string {
  const values = [
    metadata.provider ? `acceso: ${metadata.provider}` : "",
    metadata.ip_masked ? `IP: ${metadata.ip_masked}` : "",
    metadata.requested_plan ? `plan: ${metadata.requested_plan}` : "",
  ].filter(Boolean);
  return values.join(" · ");
}

export default function AdminNotificationsPanel({ token, onRead }: { token: string; onRead?: () => void }) {
  const [items, setItems] = useState<AdminNotification[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const query = unreadOnly ? "?unread_only=true&limit=200" : "?limit=200";
    setItems(await apiGet<AdminNotification[]>(`/admin/notifications${query}`, token));
  }, [token, unreadOnly]);

  useEffect(() => { void load().catch((cause) => setError(cause instanceof Error ? cause.message : "No se pudieron cargar los mensajes")); }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => { void load().catch(() => undefined); }, 30_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const unread = useMemo(() => items.filter((item) => !item.read).length, [items]);

  async function markRead(item: AdminNotification) {
    if (item.read) return;
    setBusy(true); setError("");
    try {
      await apiPost(`/admin/notifications/${item.id}/read`, token, {});
      setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, read: true } : entry));
      onRead?.();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo marcar el mensaje"); }
    finally { setBusy(false); }
  }

  async function markAll() {
    setBusy(true); setError("");
    try {
      await apiPost("/admin/notifications/read-all", token, {});
      setItems((current) => current.map((entry) => ({ ...entry, read: true })));
      onRead?.();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudieron marcar los mensajes"); }
    finally { setBusy(false); }
  }

  return <section className="admin-messages-panel">
    <div className="admin-table-card">
      <div className="panel-heading"><span>01</span><div><h3>Mensajes de acceso y licencias</h3><p>Cada ingreso correcto deja una notificación con usuario, método, horario y contexto de seguridad reducido.</p></div></div>
      <div className="admin-message-toolbar">
        <label><input type="checkbox" checked={unreadOnly} onChange={(event) => setUnreadOnly(event.target.checked)} /> Solo no leídos</label>
        <span>{unread} pendientes</span>
        <button type="button" disabled={busy || unread === 0} onClick={() => void markAll()}>Marcar todo leído</button>
      </div>
      {error && <div className="workspace-message error">{error}</div>}
      <div className="admin-message-list">
        {items.map((item) => <article key={item.id} className={`admin-message ${item.severity} ${item.read ? "read" : "unread"}`}>
          <button type="button" disabled={busy || item.read} onClick={() => void markRead(item)} aria-label={`Marcar como leído: ${item.title}`}><i /></button>
          <div>
            <div className="admin-message-head"><strong>{item.title}</strong><span>{new Date(item.created_at).toLocaleString("es-AR")}</span></div>
            <p>{item.message}</p>
            <small>{item.org_name || "Organización"}{item.actor_email ? ` · ${item.actor_email}` : ""}{metadataSummary(item.metadata) ? ` · ${metadataSummary(item.metadata)}` : ""}</small>
          </div>
        </article>)}
        {!items.length && <div className="empty">No hay mensajes para este filtro.</div>}
      </div>
    </div>
  </section>;
}
