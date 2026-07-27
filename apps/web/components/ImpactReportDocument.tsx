import type { EnvironmentalSnapshot, ImpactReport, PublicImpactReport } from "../app/lib/types";

type ReportLike = ImpactReport | PublicImpactReport;

type OfficialMetadata = {
  document_code?: string;
  document_version?: string;
  territorial_version?: string;
  province?: string;
  department?: string | null;
  municipality?: string | null;
  territory_scope?: string;
  coordinate_reference_system?: string;
  issuing_area?: string;
  reviewed_by?: string | null;
  laboratory_name?: string | null;
  protocol_reference?: string | null;
  sample_reference?: string | null;
  technical_notes?: string | null;
  verification_status?: string;
  data_cutoff_at?: string;
  emergency_channel?: string;
  disclaimer?: string;
  spaceai?: EnvironmentalSnapshot;
};

const RECIPIENT_LABELS: Record<ReportLike["recipient_type"], string> = {
  organizacion: "Organización",
  municipio: "Municipio",
  programa_organismo: "Programa / organismo (PO)",
  inversor: "Inversor",
  aseguradora: "Aseguradora",
  auditoria: "Auditoría",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-AR", { day: "2-digit", month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}T12:00:00Z`));
}
function pct(value: number | null): string {
  return value == null ? "Sin base suficiente" : `${Math.round(value * 100)}%`;
}
function seconds(value: number | null): string {
  if (value == null) return "Sin base suficiente";
  if (value < 60) return `${Math.round(value)} s`;
  return `${Math.round(value / 60)} min`;
}
function observationLabel(key: string): string {
  const labels: Record<string, string> = {
    temperature_c: "Temperatura del aire", relative_humidity_pct: "Humedad relativa", soil_moisture_pct: "Humedad superficial del suelo",
    heat_index_c: "Índice de calor", wet_bulb_c: "Temperatura de bulbo húmedo", pm25_24h_ug_m3: "PM2.5 (24 h)",
    us_aqi: "Índice de calidad del aire", uv_index: "Índice UV", river_discharge_m3_s: "Descarga fluvial",
    river_discharge_ratio: "Relación contra línea base hídrica", precipitation_24h_mm: "Precipitación 24 h",
    precipitation_7d_mm: "Precipitación 7 días", precipitation_forecast_7d_mm: "Precipitación prevista 7 días",
    humidity_balance_index: "Balance de humedad", wind_gust_kmh: "Ráfaga máxima", vapour_pressure_deficit_kpa: "Déficit de presión de vapor",
  };
  return labels[key] || key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const LEVEL_ROWS = [
  ["R0", "< 80%", "Basal", "Monitoreo rutinario"],
  ["R1", "80-99%", "Vigilancia", "Aumentar frecuencia y control de calidad"],
  ["R2", "100-149%", "Alerta", "Contrastar con fuentes secundarias"],
  ["R3", "150-199%", "Amenaza alta", "Priorizar población vulnerable"],
  ["R4", "≥ 200%", "Crítico", "Validación rápida y acciones intersectoriales"],
  ["R5", "Regla específica", "Emergencia", "Escalamiento inmediato a la autoridad competente"],
] as const;

function domainFormula(id: string): string {
  const formulas: Record<string, string> = {
    air: "Excedencia PM2.5 = (PM2.5 24 h / 15 µg/m³) × 100; AQI se interpreta por categoría oficial.",
    heat: "Índice térmico = f(temperatura, humedad relativa); categorías de índice de calor y Tw no se linealizan.",
    moisture: "Balance de humedad = f(humedad relativa, suelo, lluvia acumulada y déficit de presión de vapor).",
    fire: "Amenaza fuego/humo = f(sequedad, viento, lluvia, PM2.5/AQI, aerosoles y focos térmicos verificados).",
    hydric: "Amenaza hídrica = f(lluvia, saturación del suelo, descarga actual y relación contra baseline/percentiles).",
    uv: "Radiación UV se interpreta con la escala categórica: 0-2 bajo, 3-7 protección, ≥8 muy alto, ≥11 extremo.",
    vector: "Aptitud vectorial = f(temperatura, humedad y lluvia con rezago); requiere calibración entomológica local.",
  };
  return formulas[id] || "Regla específica definida por el dominio y la fuente de datos.";
}

export default function ImpactReportDocument({ report, publicView = false }: { report: ReportLike; publicView?: boolean }) {
  const metrics = report.metrics;
  const meta = (report.official_metadata || {}) as OfficialMetadata;
  const spaceai = meta.spaceai;
  const territory = [meta.municipality, meta.department ? `Dpto. ${meta.department}` : null, meta.province || "Misiones"].filter(Boolean).join(" · ");
  return (
    <article className="impact-document" aria-label={`Informe ${report.title}`}>
      <header className="impact-cover">
        <img className="impact-official-logo" src="/brand/econexo-lockup.jpg" alt="EcoNexo · análisis predictivo y decisiones en tiempo real" />
        <div className="impact-cover-meta">
          <span>{publicView ? "INFORME PUBLICADO" : "INFORME INSTITUCIONAL"}</span>
          <strong>{report.org_name}</strong>
          <small>{meta.document_code || "Código asignado al emitir"}</small>
        </div>
        <h1>{report.title}</h1>
        <div className="impact-recipient">
          <div><small>DESTINATARIO</small><strong>{report.recipient_name}</strong></div>
          <div><small>TIPO</small><strong>{RECIPIENT_LABELS[report.recipient_type]}</strong></div>
          <div><small>PERÍODO</small><strong>{formatDate(report.period_start)} — {formatDate(report.period_end)}</strong></div>
        </div>
      </header>

      <section className="impact-section impact-issuance-section">
        <span className="impact-section-number">01</span>
        <div className="impact-section-body">
          <h2>Ficha de emisión y alcance territorial</h2>
          <div className="impact-issuance-grid">
            <Meta label="Código documental" value={meta.document_code || "Pendiente"} />
            <Meta label="Versión" value={meta.document_version || "1.0"} />
            <Meta label="Territorio evaluado" value={territory || "Provincia de Misiones"} />
            <Meta label="Alcance" value={meta.territory_scope || "provincial"} />
            <Meta label="Área emisora" value={meta.issuing_area || "Centro de comando EcoNexo"} />
            <Meta label="Corte de datos" value={meta.data_cutoff_at ? new Date(meta.data_cutoff_at).toLocaleString("es-AR") : report.period_end} />
            <Meta label="Sistema de coordenadas" value={meta.coordinate_reference_system || "WGS 84 / EPSG:4326"} />
            <Meta label="Estado de revisión" value={meta.verification_status === "revisado" ? "Revisado por responsable declarado" : "Pendiente de revisión humana"} />
          </div>
          <p className="impact-territory-note">Este informe excluye automáticamente registros fuera del límite operacional de Misiones. Las detecciones satelitales son señales de observación remota: un foco térmico no confirma por sí solo un incendio y debe contrastarse con observación local.</p>
        </div>
      </section>

      <section className="impact-section impact-summary">
        <span className="impact-section-number">02</span>
        <div>
          <h2>Resumen ejecutivo</h2>
          <p>{report.executive_summary}</p>
        </div>
      </section>

      <section className="impact-section">
        <span className="impact-section-number">03</span>
        <div className="impact-section-body">
          <h2>Indicadores del período</h2>
          <div className="impact-metric-grid">
            <Metric label="Nodos operativos" value={`${metrics.devices_online}/${metrics.devices_total}`} detail="red de monitoreo" />
            <Metric label="Alertas detectadas" value={String(metrics.alerts_total)} detail={`${metrics.critical_alerts} críticas`} />
            <Metric label="Tiempo de detección" value={seconds(metrics.average_detection_seconds)} detail="promedio multifuente" />
            <Metric label="Precisión operativa" value={pct(metrics.model_precision)} detail="confirmadas / moderadas" />
            <Metric label="Reducción de respuesta" value={pct(metrics.response_time_reduction)} detail="contra baseline institucional" />
            <Metric label="Reportes válidos" value={pct(metrics.valid_reports_rate)} detail={`${metrics.citizen_reports_verified} verificados`} />
          </div>
        </div>
      </section>

      {spaceai && <section className="impact-section impact-spaceai-section">
        <span className="impact-section-number">04</span>
        <div className="impact-section-body">
          <div className="impact-spaceai-heading"><div><h2>Situación ambiental SpaceAI</h2><p>Snapshot congelado y versionado al momento de emisión.</p></div><div className={`impact-hti ${spaceai.overall_level.toLowerCase()}`}><span>HTI</span><strong>{Math.round(spaceai.overall_score)}</strong><b>{spaceai.overall_level} · {spaceai.overall_label}</b></div></div>
          <div className="impact-index-table">
            <div className="impact-index-row head"><span>Dominio</span><span>Nivel</span><span>Índice</span><span>Fuente</span></div>
            {spaceai.indices.map((index) => <div className="impact-index-row" key={index.id}><strong>{index.label}</strong><b className={index.level.toLowerCase()}>{index.level}</b><span>{index.value == null ? "s/d" : `${index.value} ${index.unit}`}</span><small>{index.source}</small></div>)}
          </div>
          <div className="impact-spaceai-meta"><span>Método: {spaceai.methodology_version}</span><span>Coordenadas: {spaceai.latitude.toFixed(5)}, {spaceai.longitude.toFixed(5)}</span><span>Generado: {new Date(spaceai.generated_at).toLocaleString("es-AR")}</span></div>
        </div>
      </section>}

      <section className="impact-section impact-two-column">
        <span className="impact-section-number">05</span>
        <div>
          <h2>Hallazgos destacados</h2>
          <ul className="impact-list">
            {report.highlights.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}
          </ul>
        </div>
        <div>
          <h2>Próximas acciones</h2>
          <ol className="impact-actions">
            {report.recommendations.map((item, index) => <li key={`${index}-${item}`}><span>{String(index + 1).padStart(2, "0")}</span>{item}</li>)}
          </ol>
        </div>
      </section>

      {spaceai && <section className="impact-section impact-technical-annex">
        <span className="impact-section-number">06</span>
        <div className="impact-section-body">
          <h2>Anexo técnico: cálculo y trazabilidad</h2>
          <p className="impact-lead">El anexo documenta cómo se transformaron observaciones heterogéneas en una lectura operativa. Los porcentajes indican excedencia contra una referencia; no equivalen a un incremento porcentual de daño clínico.</p>
          <div className="formula-grid">
            <div><small>FÓRMULA A · EXCEDENCIA RELATIVA</small><code>Excedencia (%) = (valor observado / valor de referencia sanitaria) × 100</code><p>Aplicable a indicadores continuos. No usar mecánicamente en AQI, UV, ruido, SPI, IDLH o índice de calor.</p></div>
            <div><small>FÓRMULA B · SCORE POR INDICADOR</small><code>Scoreᵢ = severidadᵢ × persistenciaᵢ × confiabilidadᵢ</code><p>Persistencia sugerida: 1 evento aislado; 1,25 para 2-3 días; 1,5 para 4-7 días; 2 para más de 7 días o exposición crónica.</p></div>
            <div><small>FÓRMULA C · HEALTH THREAT INDEX</small><code>HTI = Σ(wᵢ × Scoreᵢ × vulnerabilidad poblacional) / Σ(wᵢ)</code><p>Los pesos dependen del dominio, evidencia sanitaria, calidad de fuente y capacidad predictiva territorial.</p></div>
          </div>

          <h3>Matriz de severidad utilizada</h3>
          <div className="impact-method-table">
            <div className="head"><span>Nivel</span><span>Referencia</span><span>Interpretación</span><span>Respuesta sugerida</span></div>
            {LEVEL_ROWS.map(([level, reference, meaning, response]) => <div key={level}><b className={level.toLowerCase()}>{level}</b><span>{reference}</span><strong>{meaning}</strong><span>{response}</span></div>)}
          </div>

          <h3>Detalle por dominio</h3>
          <div className="impact-domain-detail">
            {spaceai.indices.map((index) => <article key={index.id}>
              <header><div><small>DOMINIO</small><h4>{index.label}</h4></div><b className={index.level.toLowerCase()}>{index.level} · {Math.round(index.score)}/100</b></header>
              <dl><div><dt>Valor</dt><dd>{index.value == null ? "Sin dato" : `${index.value} ${index.unit}`}</dd></div><div><dt>Confianza</dt><dd>{Math.round(index.confidence * 100)}%</dd></div><div><dt>Fuente</dt><dd>{index.source}</dd></div></dl>
              <p><strong>Interpretación:</strong> {index.status}</p>
              <p><strong>Regla de cálculo:</strong> {domainFormula(index.id)}</p>
              <p><strong>Acción sugerida:</strong> {index.action || "Mantener monitoreo y validar con fuentes locales."}</p>
              {!!index.evidence?.length && <div><strong>Evidencia utilizada</strong><ul>{index.evidence.map((item, evidenceIndex) => <li key={`${index.id}-${evidenceIndex}`}>{item}</li>)}</ul></div>}
              {!!index.health_impacts?.length && <div><strong>Impactos plausibles</strong><ul>{index.health_impacts.map((item, impactIndex) => <li key={`${index.id}-impact-${impactIndex}`}>{item}</li>)}</ul></div>}
            </article>)}
          </div>
        </div>
      </section>}

      {spaceai && <section className="impact-section impact-observation-annex">
        <span className="impact-section-number">07</span>
        <div className="impact-section-body">
          <h2>Anexo de observaciones, fuentes y control de calidad</h2>
          <div className="impact-observation-table">
            <div className="head"><span>Variable</span><span>Valor utilizado</span><span>Condición de uso</span></div>
            {Object.entries(spaceai.observations).map(([key, value]) => <div key={key}><strong>{observationLabel(key)}</strong><span>{value == null ? "Sin dato" : Number(value).toLocaleString("es-AR", { maximumFractionDigits: 3 })}</span><small>{value == null ? "No contribuyó al cálculo" : "Incluida según la regla del dominio"}</small></div>)}
          </div>
          <div className="impact-provenance-grid">
            <article><h3>Fuentes declaradas</h3><ul>{Object.entries(spaceai.sources).map(([key, value]) => <li key={key}><b>{key}</b>: {value}</li>)}</ul></article>
            <article><h3>Focos térmicos</h3><ul><li>Total 48 h: {spaceai.hotspots.count_48h}</li><li>Alta confianza: {spaceai.hotspots.high_confidence_count_48h}</li><li>FRP máxima: {spaceai.hotspots.maximum_frp_mw ?? "s/d"} MW</li><li>Distancia mínima: {spaceai.hotspots.nearest_distance_km ?? "s/d"} km</li></ul></article>
            <article><h3>Limitaciones registradas</h3><ul>{spaceai.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></article>
          </div>
          <div className="impact-validation-box"><h3>Control previo a uso institucional o de laboratorio</h3><ol><li>Confirmar fecha, coordenadas, zona horaria y período de agregación.</li><li>Verificar unidad, calibración y mantenimiento de cada sensor físico.</li><li>Distinguir medición in situ de estimación meteorológica, atmosférica o satelital.</li><li>Revisar datos faltantes, latencia, cobertura espacial y confiabilidad asignada.</li><li>Contrastar episodios R3-R5 con fuentes independientes y autoridad competente.</li><li>Documentar responsable de revisión, decisión adoptada y versión del método.</li></ol></div>
        </div>
      </section>}

      <section className="impact-section impact-laboratory-section">
        <span className="impact-section-number">08</span>
        <div className="impact-section-body">
          <h2>Plan de confirmación, muestreo y cadena de custodia</h2>
          <div className="impact-lab-grid">
            <Meta label="Laboratorio / institución" value={meta.laboratory_name || "A designar por la organización"} />
            <Meta label="Protocolo / expediente" value={meta.protocol_reference || "No informado"} />
            <Meta label="Muestra / campaña / lote" value={meta.sample_reference || "No informado"} />
            <Meta label="Responsable revisor" value={meta.reviewed_by || "Pendiente de designación"} />
          </div>
          <h3>Secuencia mínima recomendada</h3>
          <ol className="impact-chain-list">
            <li><b>Detección:</b> registrar fuente, fecha, hora, coordenadas, resolución espacial y latencia.</li>
            <li><b>Validación territorial:</b> confirmar municipio, departamento y pertenencia efectiva a Misiones.</li>
            <li><b>Confirmación de campo:</b> documentar fotografía, operador, equipo, calibración y condiciones ambientales.</li>
            <li><b>Muestreo:</b> asignar identificador único, matriz, preservación, transporte y horario de recepción.</li>
            <li><b>Análisis:</b> declarar método, límite de detección/cuantificación, incertidumbre y controles positivos/negativos.</li>
            <li><b>Revisión:</b> contrastar el resultado con el índice EcoNexo sin sustituir la interpretación profesional.</li>
            <li><b>Comunicación:</b> separar aviso preventivo, resultado analítico y alerta emitida por autoridad competente.</li>
          </ol>
          <div className="impact-qa-table">
            <div className="head"><span>Control</span><span>Estado documental</span><span>Evidencia requerida</span></div>
            <div><strong>Integridad temporal</strong><span>Verificar</span><small>Zona horaria, corte de datos y secuencia de eventos</small></div>
            <div><strong>Trazabilidad espacial</strong><span>Verificar</span><small>Coordenadas WGS84, municipio y departamento</small></div>
            <div><strong>Calidad de sensor</strong><span>Verificar</span><small>Calibración, deriva, batería, señal y mantenimiento</small></div>
            <div><strong>Calidad de modelo</strong><span>Verificar</span><small>Fuente, versión, cobertura, resolución y datos faltantes</small></div>
            <div><strong>Confirmación independiente</strong><span>Obligatoria R3-R5</span><small>Campo, laboratorio, autoridad o segunda fuente confiable</small></div>
          </div>
        </div>
      </section>

      <section className="impact-section impact-approval-section">
        <span className="impact-section-number">09</span>
        <div className="impact-section-body">
          <h2>Observaciones técnicas, revisión y autorización</h2>
          <div className="impact-technical-notes">
            <h3>Observaciones declaradas</h3>
            <p>{meta.technical_notes || "No se declararon observaciones adicionales. Antes de emitir el documento hacia terceros deben completarse los datos de calibración, revisión y confirmación que correspondan al uso previsto."}</p>
          </div>
          <div className="impact-signatures">
            <div><span>ELABORÓ</span><strong>{meta.issuing_area || "Centro de comando EcoNexo"}</strong><i>Fecha y firma</i></div>
            <div><span>REVISÓ</span><strong>{meta.reviewed_by || "Pendiente"}</strong><i>Fecha, cargo/matrícula y firma</i></div>
            <div><span>RECIBIÓ</span><strong>{report.recipient_name}</strong><i>Fecha, cargo y constancia</i></div>
          </div>
          <p className="impact-emergency-note"><strong>Canal de emergencia:</strong> ante fuego o humo visible, la plataforma recomienda comunicar el evento al {meta.emergency_channel || "911"}. EcoNexo no reemplaza el despacho de emergencias.</p>
        </div>
      </section>

      <section className="impact-methodology">
        <strong>Metodología y alcance</strong>
        <p>
          Los indicadores consolidan exclusivamente registros ubicados dentro de Misiones para el período seleccionado: telemetría IoT, eventos operativos, detecciones satelitales, contexto de Open-Meteo/CAMS/GloFAS y reportes ciudadanos moderados. Los datos externos son modelos o reanálisis geoespaciales, no lecturas del sensor físico. Los valores dependen de disponibilidad, calibración y cobertura. “Oficial” significa emitido y versionado por EcoNexo; no constituye certificación de autoridad pública, diagnóstico clínico, peritaje, alerta de emergencia ni dictamen regulatorio independiente.
        </p>
      </section>

      <footer className="impact-footer">
        <span>EcoNexo · Inteligencia bioclimática activa</span>
        <span>Documento generado {"published_at" in report && report.published_at ? new Intl.DateTimeFormat("es-AR", { dateStyle: "long", timeStyle: "short" }).format(new Date(report.published_at)) : "desde el centro de comando"} · {meta.document_code || "sin código"}</span>
      </footer>
    </article>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="impact-metric"><small>{label}</small><strong>{value}</strong><span>{detail}</span></div>;
}

function Meta({ label, value }: { label: string; value: string }) {
  return <div className="impact-meta-item"><small>{label}</small><strong>{value}</strong></div>;
}
