"use client";
import { useBrazilLanguage, BrazilLanguageProvider } from "./BrazilLanguage";
import { useState } from "react";
import BrazilSoyPanel from "./BrazilSoyPanel";
import BrazilMonitoringPanel from "./BrazilMonitoringPanel";

function BrazilPanelContent({ token, role }: { token: string; role: string }) {
 const { t } = useBrazilLanguage();

  const [tab, setTab] = useState<"soy"|"territory">("soy");
  return <div>
    <nav className="workspace-steps" aria-label={t("Herramientas de Mato Grosso")}>
      <button className={tab === "soy" ? "active" : ""} aria-current={tab === "soy" ? "page" : undefined} onClick={() => setTab("soy")}>{t("Soja · pronóstico y evaluación")}</button>
      <button className={tab === "territory" ? "active" : ""} aria-current={tab === "territory" ? "page" : undefined} onClick={() => setTab("territory")}>{t("Mapa estatal y alertas")}</button>
    </nav>
    <div hidden={tab !== "soy"}><BrazilSoyPanel token={token} role={role}/></div>
    {tab === "territory" && <BrazilMonitoringPanel token={token}/>}
  </div>;
}

export default function BrazilPanel(props: { token: string; role: string }) {
 return <BrazilLanguageProvider><BrazilPanelContent {...props}/></BrazilLanguageProvider>;
}
