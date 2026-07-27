"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { publicGet } from "../lib/api";
import type { PublicImpactReport } from "../lib/types";
import ImpactReportDocument from "../../components/ImpactReportDocument";
import SiteFooter from "../../components/SiteFooter";

function PublicReportView() {
  const search = useSearchParams();
  const token = search.get("token") || "";
  const [report, setReport] = useState<PublicImpactReport | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!token) { setError("El enlace no contiene un token de informe."); return; }
    publicGet<PublicImpactReport>(`/impact-reports/public/view/${encodeURIComponent(token)}`)
      .then(setReport).catch((cause) => setError(cause instanceof Error ? cause.message : "Informe no disponible"));
  }, [token]);
  if (error) return <div className="public-report-state"><div className="impact-logo">ECO<span>NEXO</span></div><h1>Informe no disponible</h1><p>{error}</p><a href="/">Volver a EcoNexo</a></div>;
  if (!report) return <div className="public-report-state"><div className="impact-logo">ECO<span>NEXO</span></div><p>Cargando informe verificado…</p></div>;
  return <>
    <div className="public-report-toolbar no-print"><div><span>● INFORME PUBLICADO</span><small>El propietario puede revocar este enlace.</small></div><button onClick={() => window.print()}>Imprimir / guardar PDF</button></div>
    <main className="public-report-page"><ImpactReportDocument report={report} publicView /></main>
    <SiteFooter compact />
  </>;
}

export default function PublicReportPage() {
  return <Suspense fallback={<div className="public-report-state">Cargando…</div>}><PublicReportView /></Suspense>;
}
