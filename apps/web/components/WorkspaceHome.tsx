"use client";

type Destination = 'comando'|'agro'|'ecocampo'|'paraguay'|'informes'|'prediccion';
export default function WorkspaceHome({name,alerts,devices,connected,onOpen}:{name:string;alerts:number;devices:number;connected:boolean;onOpen:(view:Destination)=>void}){
  return <section className="workspace-home" aria-label="Inicio de Econexo">
    <div className="workspace-welcome"><span className="workspace-eyebrow">TU ESPACIO DE TRABAJO</span><h2>¿Qué necesitás revisar hoy?</h2><p>Elegí una tarea. La información y las herramientas aparecen cuando las necesitás.</p></div>
    <div className="workspace-summary"><div><span>Organización</span><strong>{name}</strong></div><div><span>Alertas abiertas en Misiones</span><strong>{connected?alerts:'—'}</strong></div><div><span>Dispositivos en Misiones</span><strong>{connected?devices:'—'}</strong></div><div><span>Estado de la consulta</span><strong>{connected?'Datos recibidos':'Sin confirmar'}</strong></div></div>
    <div className="workspace-task-grid">
      <button className="workspace-task featured" onClick={()=>onOpen('agro')}><span className="workspace-task-label">AGRICULTURA</span><h3>Revisar mis cultivos</h3><p>Lotes, agua y condiciones para planificar las labores.</p><span>Ver cultivos <b aria-hidden="true">↗</b></span></button>
      <button className="workspace-task" onClick={()=>onOpen('paraguay')}><span className="workspace-task-label">PARAGUAY</span><h3>Evaluar un lote de soja</h3><p>Ubicación, pronóstico y recomendaciones para tu campo.</p><span>Abrir Paraguay <b aria-hidden="true">↗</b></span></button>
      <button className="workspace-task" onClick={()=>onOpen('ecocampo')}><span className="workspace-task-label">GANADERÍA Y TERRENO</span><h3>Planificar el uso del campo</h3><p>Evaluación del terreno y presupuesto de forraje.</p><span>Abrir EcoCampo <b aria-hidden="true">↗</b></span></button>
      <button className="workspace-task" onClick={()=>onOpen('comando')}><span className="workspace-task-label">MONITOREO TERRITORIAL</span><h3>Ver el mapa y las alertas</h3><p>Señales que requieren seguimiento en Misiones.</p><span>Abrir mapa <b aria-hidden="true">↗</b></span></button>
    </div>
    <div className="workspace-next"><div><h3>Los informes, a mano</h3><p>Consultá el historial y compartí la información con tu equipo. Los informes de soja están dentro de Paraguay.</p></div><button onClick={()=>onOpen('informes')}>Ver informes</button></div>
    <p className="workspace-help">Primera visita: empezá por Cultivos o Paraguay, ubicá tu lote y revisá los datos disponibles. Las herramientas de configuración están en el menú lateral.</p>
  </section>;
}
