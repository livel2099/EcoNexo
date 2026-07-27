import Link from "next/link";
import SystemStatus from "../../components/SystemStatus";
import SiteFooter from "../../components/SiteFooter";

export const metadata = { title: "Estado del sistema" };

export default function StatusPage() {
  return (
    <main className="status-page">
      <header className="legal-topbar"><Link href="/" className="brand">ECO<span>NEXO</span></Link><Link href="/">Volver</Link></header>
      <section className="status-hero"><span>TRANSPARENCIA OPERATIVA · MISIONES</span><h1>Estado del sistema</h1><p>Controles públicos básicos de conectividad, base geoespacial y alcance territorial.</p></section>
      <SystemStatus />
      <SiteFooter />
    </main>
  );
}
