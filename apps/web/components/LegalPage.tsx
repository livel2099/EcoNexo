import Link from "next/link";
import type { ReactNode } from "react";
import SiteFooter from "./SiteFooter";

export const legalContact = process.env.NEXT_PUBLIC_LEGAL_EMAIL || "legal@econexo.com.ar";
export const legalEntity = {
  name: process.env.NEXT_PUBLIC_LEGAL_ENTITY_NAME || "EcoNexo",
  cuit: process.env.NEXT_PUBLIC_LEGAL_CUIT || "CUIT pendiente de publicación",
  address: process.env.NEXT_PUBLIC_LEGAL_ADDRESS || "Misiones, Argentina",
  jurisdiction: process.env.NEXT_PUBLIC_LEGAL_JURISDICTION || "Provincia de Misiones",
};
const legalComplete = Boolean(
  process.env.NEXT_PUBLIC_LEGAL_ENTITY_NAME
  && process.env.NEXT_PUBLIC_LEGAL_CUIT
  && process.env.NEXT_PUBLIC_LEGAL_ADDRESS
  && process.env.NEXT_PUBLIC_LEGAL_EMAIL,
);

export function LegalPage({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <main className="legal-page">
      <header className="legal-topbar"><Link href="/" className="brand">ECO<span>NEXO</span></Link><Link href="/">Volver</Link></header>
      <article className="legal-document">
        <div className="legal-cover"><span>MARCO DE CONFIANZA · MISIONES</span><h1>{title}</h1><p>{subtitle}</p><div><strong>Versión 1.1</strong><span>Vigencia: 27 de julio de 2026</span></div></div>
        {!legalComplete && <aside className="legal-review-note"><strong>Datos societarios pendientes antes del lanzamiento comercial.</strong><span>Configurá NEXT_PUBLIC_LEGAL_ENTITY_NAME, NEXT_PUBLIC_LEGAL_CUIT, NEXT_PUBLIC_LEGAL_ADDRESS y NEXT_PUBLIC_LEGAL_EMAIL. La publicación definitiva debe contar con revisión jurídica local.</span></aside>}
        <div className="legal-identity"><strong>{legalEntity.name}</strong><span>{legalEntity.cuit} · {legalEntity.address} · Jurisdicción: {legalEntity.jurisdiction}</span></div>
        <div className="legal-content">{children}</div>
      </article>
      <SiteFooter />
    </main>
  );
}

export function LegalSection({ number, title, children }: { number: string; title: string; children: ReactNode }) {
  return <section className="legal-section"><span>{number}</span><div><h2>{title}</h2>{children}</div></section>;
}
