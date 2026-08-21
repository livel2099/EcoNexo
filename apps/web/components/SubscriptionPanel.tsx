"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../app/lib/api";
import type {
  LicenseRequest,
  PlatformSubscriptionRow,
  SubscriptionMe,
  SubscriptionPlan,
  SubscriptionPlanKey,
} from "../app/lib/types";

const USAGE: Array<[keyof SubscriptionMe["usage"], string, string]> = [
  ["users", "Usuarios", "max_users"],
  ["devices", "Dispositivos", "max_devices"],
  ["zones", "Geocercas", "max_zones"],
  ["rules", "Reglas", "max_rules"],
  ["reports_this_month", "Informes del mes", "max_reports_per_month"],
];

function price(plan: SubscriptionPlan): string {
  const period = plan.billing_period === "monthly" ? "/mes" : plan.billing_period === "cohort" ? "/cohorte" : "";
  if ((plan.price_min_usd || 0) === 0 && (plan.price_max_usd || 0) === 0) return "Evaluación limitada";
  if (plan.price_max_usd == null) return `USD ${Number(plan.price_min_usd).toLocaleString("es-AR")}+${period}`;
  return `USD ${Number(plan.price_min_usd).toLocaleString("es-AR")}–${Number(plan.price_max_usd).toLocaleString("es-AR")}${period}`;
}

function booleanFeature(value: unknown): string {
  return value ? "Incluido" : "No incluido";
}

function statusLabel(value: string): string {
  return ({ pending: "Pendiente", trial: "Evaluación", active: "Activa", past_due: "Pago pendiente", suspended: "Suspendida", expired: "Vencida", cancelled: "Cancelada", approved: "Aprobada", rejected: "Rechazada" } as Record<string, string>)[value] || value;
}

export default function SubscriptionPanel({ token }: { token: string }) {
  const [subscription, setSubscription] = useState<SubscriptionMe | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [requests, setRequests] = useState<LicenseRequest[]>([]);
  const [platformRequests, setPlatformRequests] = useState<LicenseRequest[]>([]);
  const [organizations, setOrganizations] = useState<PlatformSubscriptionRow[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlanKey>("pilot_8_weeks");
  const [requestMessage, setRequestMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    const [me, catalog, mine] = await Promise.all([
      apiGet<SubscriptionMe>("/subscriptions/me", token),
      apiGet<SubscriptionPlan[]>("/subscriptions/plans", token),
      apiGet<LicenseRequest[]>("/subscriptions/requests", token),
    ]);
    setSubscription(me); setPlans(catalog); setRequests(mine);
    if (me.platform_admin) {
      const [pending, orgs] = await Promise.all([
        apiGet<LicenseRequest[]>("/subscriptions/platform/requests?status=pending", token),
        apiGet<PlatformSubscriptionRow[]>("/subscriptions/platform/organizations", token),
      ]);
      setPlatformRequests(pending); setOrganizations(orgs);
    }
  }, [token]);

  useEffect(() => { void load().catch((cause) => setError(cause instanceof Error ? cause.message : "No se pudo cargar la licencia")); }, [load]);

  const selected = useMemo(() => plans.find((plan) => plan.plan_key === selectedPlan), [plans, selectedPlan]);

  async function requestPlan(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      await apiPost<LicenseRequest>("/subscriptions/request-change", token, { requested_plan: selectedPlan, message: requestMessage });
      setRequestMessage(""); await load(); setNotice("Solicitud registrada en la bandeja comercial de EcoNexo.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo enviar la solicitud"); }
    finally { setBusy(false); }
  }

  async function approve(item: LicenseRequest) {
    const plan = plans.find((entry) => entry.plan_key === item.requested_plan);
    if (!plan || !window.confirm(`Activar ${plan.display_name} para ${item.org_name}?`)) return;
    const modules = Array.isArray(plan.entitlements.included_modules) ? plan.entitlements.included_modules : ["core"];
    setBusy(true); setError("");
    try {
      await apiPatch(`/subscriptions/platform/${item.org_id}`, token, {
        plan_key: item.requested_plan,
        status: "active",
        active_modules: modules,
        request_id: item.id,
        notes: "Activación aprobada desde Admin Core",
      });
      await load(); setNotice(`Licencia activada para ${item.org_name}.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo activar la licencia"); }
    finally { setBusy(false); }
  }

  if (!subscription) return <div className="admin-form-card"><p>Cargando suscripción…</p></div>;

  return <section className="subscription-panel">
    {error && <div className="workspace-message error">{error}</div>}
    {notice && <div className="workspace-message success">{notice}</div>}

    <div className="subscription-hero">
      <div><span className="eyebrow">LICENCIA ACTUAL</span><h3>{subscription.plan.display_name}</h3><p>{subscription.plan.description}</p></div>
      <div className={`subscription-status ${subscription.available ? "active" : "inactive"}`}><strong>{statusLabel(subscription.status)}</strong><span>{subscription.expiry_label}</span></div>
      <div className="subscription-price"><strong>{price(subscription.plan)}</strong><span>{subscription.entitlements.report_frequency as string || "frecuencia según contrato"}</span></div>
    </div>

    <div className="subscription-usage-grid">
      {USAGE.map(([usageKey, label, limitKey]) => {
        const current = subscription.usage[usageKey];
        const rawLimit = subscription.entitlements[limitKey];
        const limit = typeof rawLimit === "number" ? rawLimit : null;
        // Sin tope la barra queda vacía: llenarla al 100% haría leer como
        // agotado un recurso que no tiene límite.
        const percent = limit && limit > 0 ? Math.min(100, Math.round(current / limit * 100)) : 0;
        return <article key={usageKey}><span>{label}</span><strong>{current}<small>{limit == null ? " · sin límite" : ` / ${limit}`}</small></strong><i><b style={{ width: `${percent}%` }} /></i></article>;
      })}
    </div>

    <div className="subscription-feature-grid">
      <article><span>Capas críticas</span><strong>{String(subscription.entitlements.max_critical_layers ?? "según contrato")}</strong></article>
      <article><span>Municipios</span><strong>{String(subscription.entitlements.municipality_limit ?? "según contrato")}</strong></article>
      <article><span>API</span><strong>{booleanFeature(subscription.entitlements.api_access)}</strong></article>
      <article><span>Exportación de auditoría</span><strong>{booleanFeature(subscription.entitlements.audit_export)}</strong></article>
      <article><span>Modelos personalizados</span><strong>{booleanFeature(subscription.entitlements.custom_models)}</strong></article>
      <article><span>SLA</span><strong>{booleanFeature(subscription.entitlements.sla)}</strong></article>
    </div>

    <div className="subscription-layout">
      <article className="admin-table-card">
        <div className="panel-heading"><span>01</span><div><h3>Planes comerciales</h3><p>Precios del plan de negocios; los límites técnicos pueden ajustarse por contrato.</p></div></div>
        <div className="plan-catalog">
          {plans.map((plan) => <button type="button" key={plan.plan_key} className={`${selectedPlan === plan.plan_key ? "selected" : ""} ${subscription.plan.plan_key === plan.plan_key ? "current" : ""}`} onClick={() => setSelectedPlan(plan.plan_key)}>
            <span>{plan.display_name}</span><strong>{price(plan)}</strong><small>{plan.description}</small>{subscription.plan.plan_key === plan.plan_key && <b>ACTUAL</b>}
          </button>)}
        </div>
      </article>

      <form className="admin-form-card subscription-request" onSubmit={requestPlan}>
        <div className="panel-heading"><span>02</span><div><h3>Solicitar cambio</h3><p>La solicitud llega al panel del administrador comercial.</p></div></div>
        <label>Plan solicitado<select value={selectedPlan} onChange={(event) => setSelectedPlan(event.target.value as SubscriptionPlanKey)}>{plans.filter((plan) => plan.plan_key !== "sandbox").map((plan) => <option key={plan.plan_key} value={plan.plan_key}>{plan.display_name}</option>)}</select></label>
        <label>Necesidad o alcance<textarea rows={5} maxLength={2000} value={requestMessage} onChange={(event) => setRequestMessage(event.target.value)} placeholder="Municipios, cantidad de nodos, módulos adicionales, integraciones o fecha estimada." /></label>
        {selected && <div className="source-warning"><strong>{price(selected)}</strong><span>{selected.description}</span></div>}
        <button className="primary" disabled={busy || selectedPlan === "sandbox"}>Enviar solicitud</button>
        {subscription.sales_email && <a className="subscription-mail" href={`mailto:${subscription.sales_email}?subject=Licencia EcoNexo ${encodeURIComponent(selected?.display_name || "")}`}>Contacto comercial: {subscription.sales_email}</a>}
        <div className="license-request-history">{requests.slice(0, 5).map((item) => <span key={item.id}><b>{plans.find((plan) => plan.plan_key === item.requested_plan)?.display_name || item.requested_plan}</b> · {statusLabel(item.status)} · {new Date(item.created_at).toLocaleDateString("es-AR")}</span>)}</div>
      </form>
    </div>

    {subscription.platform_admin && <section className="platform-license-console">
      <div className="panel-heading"><span>03</span><div><h3>Consola comercial de plataforma</h3><p>Visible solamente para los emails configurados en PLATFORM_ADMIN_EMAILS.</p></div></div>
      <div className="platform-request-list">
        {platformRequests.map((item) => <article key={item.id}><div><strong>{item.org_name}</strong><span>{item.requester_email}</span><small>{item.message || "Sin comentario"}</small></div><b>{plans.find((plan) => plan.plan_key === item.requested_plan)?.display_name || item.requested_plan}</b><button type="button" disabled={busy} onClick={() => void approve(item)}>Aprobar y activar</button></article>)}
        {!platformRequests.length && <div className="empty">No hay solicitudes pendientes.</div>}
      </div>
      <div className="platform-org-table"><div className="head"><span>Organización</span><span>Plan</span><span>Estado</span><span>Vencimiento</span></div>{organizations.slice(0, 30).map((item) => <div key={item.org_id}><span><strong>{item.org_name}</strong><small>{item.municipality || "Misiones"}</small></span><span>{item.display_name}</span><span>{statusLabel(item.status)}</span><span>{item.expires_at ? new Date(item.expires_at).toLocaleDateString("es-AR") : "continuo"}</span></div>)}</div>
    </section>}
  </section>;
}
