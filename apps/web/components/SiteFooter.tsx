import Link from "next/link";
import type { ReactNode } from "react";

export default function SiteFooter({ compact = false, brand }: { compact?: boolean; brand?: ReactNode }) {
  return (
    <footer className={`site-footer ${compact ? "compact" : ""}`}>
      <div>
        {brand || <strong>ECO<span>NEXO</span></strong>}
        <small>Inteligencia bioclimática activa</small>
      </div>
      <nav aria-label="Información legal">
        <Link href="/">Inicio</Link>
        <Link href="/documentacion">Documentación</Link>
        <Link href="/terminos">Términos</Link>
        <Link href="/privacidad">Privacidad</Link>
        <Link href="/cookies">Cookies</Link>
        <Link href="/seguridad">Seguridad</Link>
        <Link href="/accesibilidad">Accesibilidad</Link>
        <Link href="/metodologia">Metodología</Link>
        <Link href="/estado">Estado</Link>
      </nav>
      <small>© 2026 EcoNexo · Plantillas legales sujetas a revisión profesional antes del lanzamiento comercial.</small>
    </footer>
  );
}
