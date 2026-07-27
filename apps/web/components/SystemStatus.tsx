"use client";

import { useEffect, useMemo, useState } from "react";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

type Check = { label: string; state: "checking" | "ok" | "warning" | "error"; detail: string };

export default function SystemStatus() {
  const [checks, setChecks] = useState<Check[]>([
    { label: "Aplicación web", state: "ok", detail: "Interfaz cargada correctamente" },
    { label: "API", state: "checking", detail: "Verificando disponibilidad" },
    { label: "Base y PostGIS", state: "checking", detail: "Verificando readiness" },
    { label: "Límite oficial de Misiones", state: "checking", detail: "Verificando GeoRef" },
  ]);

  useEffect(() => {
    if (DEMO_MODE || !API_URL) {
      setChecks((current) => current.map((item) => item.label === "Aplicación web" ? item : {
        ...item,
        state: "warning",
        detail: "Demo autónoma: este control requiere la API productiva",
      }));
      return;
    }
    let active = true;
    Promise.allSettled([
      fetch(`${API_URL}/health`, { cache: "no-store" }).then((response) => response.ok ? response.json() : Promise.reject(response.status)),
      fetch(`${API_URL}/ready`, { cache: "no-store" }).then(async (response) => ({ ok: response.ok, body: await response.json() })),
      fetch(`${API_URL}/territory/boundary-status`, { cache: "no-store" }).then((response) => response.ok ? response.json() : Promise.reject(response.status)),
    ]).then(([health, ready, boundary]) => {
      if (!active) return;
      const healthOk = health.status === "fulfilled" && health.value?.status === "ok";
      const readyBody = ready.status === "fulfilled" ? ready.value.body : null;
      const readyOk = ready.status === "fulfilled" && ready.value.ok && readyBody?.status === "ready";
      const official = boundary.status === "fulfilled" && Boolean(boundary.value?.official);
      setChecks([
        { label: "Aplicación web", state: "ok", detail: "Interfaz cargada correctamente" },
        { label: "API", state: healthOk ? "ok" : "error", detail: healthOk ? `EcoNexo API · ${health.value.territory || "Misiones"}` : "No disponible" },
        { label: "Base y PostGIS", state: readyOk ? "ok" : "error", detail: readyOk ? "Base, PostGIS y guardas territoriales operativas" : "Readiness incompleto" },
        { label: "Límite oficial de Misiones", state: official ? "ok" : "warning", detail: official ? "Geometría oficial GeoRef sincronizada" : "Activo con fallback; sincronización GeoRef pendiente" },
      ]);
    });
    return () => { active = false; };
  }, []);

  const overall = useMemo(() => checks.some((item) => item.state === "error") ? "error" : checks.some((item) => item.state === "warning" || item.state === "checking") ? "warning" : "ok", [checks]);

  return (
    <section className="status-console" aria-live="polite">
      <header><span className={`status-orb ${overall}`} /><div><h2>{overall === "ok" ? "Servicios operativos" : overall === "error" ? "Revisión necesaria" : "Operación parcial"}</h2><p>Estado visible del entorno configurado para EcoNexo Misiones.</p></div></header>
      <div className="status-checks">{checks.map((check) => <article key={check.label} className={`status-check ${check.state}`}><span>{check.state === "ok" ? "✓" : check.state === "error" ? "×" : check.state === "warning" ? "!" : "…"}</span><div><strong>{check.label}</strong><small>{check.detail}</small></div></article>)}</div>
      <p className="status-note">Este panel no certifica la disponibilidad de fuentes de terceros ni sustituye la supervisión operativa, los runbooks y el monitoreo de infraestructura.</p>
    </section>
  );
}
