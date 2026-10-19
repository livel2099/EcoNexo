from pathlib import Path
p=Path('apps/web/app/dashboard/page.tsx');s=p.read_text(encoding='utf-8-sig')
s=s.replace('import CircuitBackdrop from "../../components/CircuitBackdrop";','import WorkspaceHome from "../../components/WorkspaceHome";')
s=s.replace('type View = "paraguay"','type View = "inicio" | "paraguay"')
s=s.replace('useState<View>("comando")','useState<View>("inicio")')
s=s.replace('  const [kpi, setKpi]', '  const [menuOpen, setMenuOpen] = useState(false);\n  const navigate = (target: View) => { setView(target); setMenuOpen(false); };\n  const [kpi, setKpi]')
s=s.replace('onClick={() => setView(target)}','aria-current={view === target ? "page" : undefined} onClick={() => navigate(target)}')
a=s.index('  return (\n    <main className={`shell tech-shell');b=s.index('      {accessNotice &&',a)
s=s[:a]+'''  const viewNames: Record<View, [string,string]> = {
    inicio:["Inicio","Un lugar para organizar tu día y decidir el próximo paso."],
    comando:["Mapa y alertas","Monitoreo territorial de Misiones."],
    agro:["Mis cultivos","Seguimiento de lotes agrícolas con EcoNexo AG."],
    ecocampo:["Mi campo y forraje","Evaluación de terreno y planificación con EcoCampo."],
    paraguay:["Paraguay · Soja","El clima, tu lote y sus recomendaciones, paso a paso."],
    informes:["Informes","Información para revisar y compartir con tu equipo."],
    prediccion:["Pronósticos de riesgo","Señales anticipadas para planificar el seguimiento."],
    fuego:["Fuego y humo","Vigilancia y verificación de señales territoriales."],
    plagas:["Sanidad forestal","Seguimiento y revisión de riesgos forestales."],
    observatorio:["Análisis ambiental","Detalle de fuentes e indicadores ambientales."],
    dispositivos:["Dispositivos","Administrá las fuentes de medición de tu organización."],
    reglas:["Reglas de alertas","Definí qué señales requieren atención."],
    reportes:["Reportes ciudadanos","Revisá los avisos recibidos desde el territorio."],
    admin:["Configuración","Usuarios, acceso y fuentes de la organización."],
  };
  return (
    <main className={`shell workspace-shell${menuOpen ? " nav-open" : ""}`}>
      <aside className="workspace-sidebar" aria-label="Menú de Econexo">
        <a className="workspace-brand" href="/dashboard"><img src="/brand/econexo-lockup.jpg" alt="Econexo" /></a>
        <div className="workspace-org"><small>ESPACIO DE TRABAJO</small><strong>{org?.name || "Tu organización"}</strong></div>
        <nav className="workspace-nav" aria-label="Navegación principal">
          {navItem("inicio", "Inicio")}
          <span className="workspace-nav-label">EL CAMPO</span>
          {navItem("agro", "Mis cultivos")}
          {navItem("ecocampo", "Campo y forraje")}
          {navItem("paraguay", "Paraguay · Soja")}
          <span className="workspace-nav-label">SEGUIMIENTO</span>
          {navItem("comando", "Mapa y alertas")}
          {navItem("prediccion", "Pronósticos de riesgo")}
          {navItem("informes", "Informes")}
          <details className="workspace-more" open={["fuego","plagas","observatorio","reportes","dispositivos","reglas","admin"].includes(view) || undefined}>
            <summary>Más herramientas</summary>
            {navItem("fuego", "Fuego y humo")}
            {navItem("plagas", "Sanidad forestal")}
            {navItem("observatorio", "Análisis ambiental")}
            {navItem("reportes", "Reportes ciudadanos")}
            {navItem("dispositivos", "Dispositivos")}
            {navItem("reglas", "Reglas de alertas")}
            <button onClick={() => router.push("/red-investigacion")}>Comunidad EcoNexoFoI</button>
            {session?.role === "admin" && navItem("admin", "Configuración")}
            {session?.platform_admin && <button onClick={() => router.push("/plataforma")}>Administración general</button>}
          </details>
        </nav>
        <div className="workspace-account"><strong>{session?.name || "Usuario"}</strong><small>{session?.role || ""}</small><button onClick={() => { clearSession(); router.replace("/"); }}>Cerrar sesión</button></div>
      </aside>
      <div className={`workspace-content${view === "comando" ? " command-view" : ""}`}>
        <header className="workspace-heading"><div><button className="workspace-menu" aria-expanded={menuOpen} onClick={()=>setMenuOpen(!menuOpen)}>Menú</button><span className="workspace-eyebrow">ECONEXO / {view === "paraguay" ? "PARAGUAY" : "TU ORGANIZACIÓN"}</span><h1>{viewNames[view][0]}</h1><p>{viewNames[view][1]}</p></div>{view !== "inicio" && <button className="workspace-back" onClick={()=>navigate("inicio")}>Volver al inicio</button>}</header>
''' +s[b:]
s=s.replace('{view !== "paraguay" && <>','{view === "comando" && <>')
s=s.replace('      <section className="kpis kpirow"','      <details className="workspace-technical"><summary>Ver indicadores de operación</summary>\n      <section className="kpis kpirow"')
s=s.replace('      <EarthIntelBar lat=', '      </details>\n      <EarthIntelBar lat=')
s=s.replace('      {token && view === "paraguay" ?', '      {view === "inicio" ? <WorkspaceHome name={org?.name || "Tu organización"} connected={kpi !== null && !accessNotice} alerts={localAlerts.filter(a=>!["descartada","resuelta"].includes(a.status)).length} devices={localDevices.length} onOpen={navigate} /> : token && view === "paraguay" ?')
s=s.replace('    </main>','      </div>\n    </main>',1)
p.write_text(s,encoding='utf-8')

p=Path('apps/web/components/ParaguaySoyPanel.tsx');s=p.read_text(encoding='utf-8-sig')
s=s.replace(" const [e,setE]", " const [tab,setTab]=useState('location');\n const [e,setE]")
s=s.replace('setReport(row.report);setNotice', "setReport(row.report);setTab('reports');setNotice")
s=s.replace("else setReport(await apiPost<Report>('/paraguay/soja/evaluate',token,submitted));", "else {setReport(await apiPost<Report>('/paraguay/soja/evaluate',token,submitted));setTab('reports');}")
needle=' <Map lat={e.lat}'
s=s.replace(needle,''' <nav className="workspace-steps" aria-label="Pasos para evaluar soja">{[['location','1','Ubicación'],['weather','2','Clima'],['assessment','3','Evaluación'],['satellite','4','Satélite'],['reports','5','Informes']].map(([id,n,label])=><button key={id} aria-current={tab===id?'step':undefined} className={tab===id?'active':''} onClick={()=>setTab(id)}><span>{n}</span>{label}</button>)}</nav>
 <div hidden={tab!=='location'} className="workspace-step-content"><div className="workspace-section-intro"><h3>Primero, ubicá tu lote</h3><p>Tocá el mapa para elegir la ubicación. Después revisá el clima y completá lo que conozcas de tu campo.</p></div><div className="workspace-coordinate-fields"><label>Latitud<input type="number" step="any" value={e.lat} onChange={ev=>update({lat:Number(ev.target.value)})}/></label><label>Longitud<input type="number" step="any" value={e.lon} onChange={ev=>update({lon:Number(ev.target.value)})}/></label></div>
 <Map lat={e.lat}''')
s=s.replace(' <article className="agro-card"><h3>Datos automáticos por ubicación', ''' <div className="workspace-step-actions"><button className="primary" onClick={()=>setTab('weather')}>Continuar al clima</button></div></div>
 <div hidden={tab!=='weather'} className="workspace-step-content"><article className="agro-card"><h3>El clima de tu lote''')
s=s.replace(' <form onSubmit=', ''' <div className="workspace-step-actions"><button onClick={()=>setTab('location')}>Volver a ubicación</button><button className="primary" onClick={()=>setTab('assessment')}>Continuar a evaluación</button></div></div>
 <div hidden={tab!=='assessment'} className="workspace-step-content"><div className="workspace-section-intro"><h3>Completá lo que sabés de tu campo</h3><p>Podés empezar con los datos básicos. Dejá en blanco lo que no mediste: aparecerá como pendiente en el informe.</p></div><form onSubmit=''',1)
s=s.replace('<h3>Lote y evidencia de campo</h3>','<h3>Datos del lote y observaciones</h3>')
s=s.replace(" {report&&<article", " </div>\n <div hidden={tab!=='reports'} className=\"workspace-step-content\">\n {report&&<article",1)
s=s.replace(' <article className="agro-card"><h3>Imágenes satelitales del lote', ''' </div><div hidden={tab!=='satellite'} className="workspace-step-content"><article className="agro-card"><h3>Observá tu lote desde el satélite''')
s=s.replace(' <article className="agro-card"><h3>Informes de Paraguay guardados', ''' </div><div hidden={tab!=='reports'} className="workspace-step-content"><article className="agro-card"><h3>Informes guardados''')
s=s.replace("onClick={()=>setReport(row.report)}", "onClick={()=>{setReport(row.report);setTab('reports');}}")
s=s.replace('</article></section>;', '</article></div></section>;')
p.write_text(s,encoding='utf-8')
