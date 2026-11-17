"use client";
import { useState } from "react";
import BrazilSoyPanel from "./BrazilSoyPanel";
import BrazilMonitoringPanel from "./BrazilMonitoringPanel";

export default function BrazilPanel({ token, role }: { token: string; role: string }) {
  const [tab, setTab] = useState<"soy"|"territory">("soy");
  return <div>
    <nav className="workspace-steps" aria-label="Herramientas de Mato Grosso">
      <button className={tab === "soy" ? "active" : ""} aria-current={tab === "soy" ? "page" : undefined} onClick={() => setTab("soy")}>Soja · pronóstico y evaluación</button>
      <button className={tab === "territory" ? "active" : ""} aria-current={tab === "territory" ? "page" : undefined} onClick={() => setTab("territory")}>Mapa estatal y alertas</button>
    </nav>
    <div hidden={tab !== "soy"}><BrazilSoyPanel token={token} role={role}/></div>
    {tab === "territory" && <BrazilMonitoringPanel token={token}/>}
  </div>;
}
