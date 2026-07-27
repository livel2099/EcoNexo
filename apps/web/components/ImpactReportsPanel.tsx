"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPost } from "../app/lib/api";
import type { EnvironmentalSnapshotRecord, ImpactReport, ImpactReportPublishResult, RecipientType, ReportKind } from "../app/lib/types";
import ImpactReportDocument from "./ImpactReportDocument";

function isoDate(daysAgo: number): string {
  return new Date(Date.now() - daysAgo * 86_400_000).toISOString().slice(0, 10);
}
function csvEscape(value: unknown): string {
  const text = value == null ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

export default function ImpactReportsPanel({ token }: { token: string }) {
  const [reports, setReports] = useState<ImpactReport[]>([]);
  const [snapshots, setSnapshots] = useState<EnvironmentalSnapshotRecord[]>([]);
  const [reportKind, setReportKind] = useState<ReportKind>("desempeno_operativo");
  const [snapshotId, setSnapshotId] = useState("");
  const [selected, setSelected] = useState<ImpactReport | null>(null);
  const [title, setTitle] = useState("Informe de desempeño ambiental y respuesta temprana");
  const [recipientType, setRecipientType] = useState<RecipientType>("programa_organismo");
  const [recipientName, setRecipientName] = useState("Programa u organismo destinatario");
  const [periodStart, setPeriodStart] = useState(isoDate(30));
  const [periodEnd, setPeriodEnd] = useState(isoDate(0));
  const [summary, setSummary] = useState("");
  const [issuingArea, setIssuingArea] = useState("Centro de comando EcoNexo Misiones");
  const [reviewedBy, setReviewedBy] = useState("");
  const [laboratoryName, setLaboratoryName] = useState("");
  const [protocolReference, setProtocolReference] = useState("");
  const [sampleReference, setSampleReference] = useState("");
  const [technicalNotes, setTechnicalNotes] = useState("");
  const [recommendations, setRecommendations] = useState("Revisar alertas críticas y documentar acciones.\nMantener calibrados los nodos de menor disponibilidad.\nValidar los eventos R3-R5 con observación local, autoridad competente o laboratorio según el caso.");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [shareUrl, setShareUrl] = useState("");

  const load = useCallback(async () => {
    try {
      const [result, environmental] = await Promise.all([
        apiGet<ImpactReport[]>("/impact-reports", token),
        apiGet<EnvironmentalSnapshotRecord[]>("/environment/snapshots?limit=40", token).catch(() => []),
      ]);
      setReports(result);
      setSnapshots(environmental);
      setSnapshotId((current) => current || environmental[0]?.id || "");
      setSelected((current) => current ? result.find((item) => item.id === current.id) || result[0] || null : result[0] || null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudieron cargar los informes");
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const counts = useMemo(() => ({
    total: reports.length,
    published: reports.filter((report) => report.status === "publicado").length,
  }), [reports]);

  async function createReport(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice(""); setShareUrl("");
    try {
      const report = await apiPost<ImpactReport>("/impact-reports", token, {
        report_kind: reportKind,
        environmental_snapshot_id: reportKind === "desempeno_operativo" ? null : snapshotId || null,
        title, recipient_type: recipientType, recipient_name: recipientName,
        period_start: periodStart, period_end: periodEnd,
        executive_summary: summary,
        issuing_area: issuingArea,
        reviewed_by: reviewedBy,
        laboratory_name: laboratoryName,
        protocol_reference: protocolReference,
        sample_reference: sampleReference,
        technical_notes: technicalNotes,
        recommendations: recommendations.split("\n").map((item) => item.trim()).filter(Boolean),
      });
      setReports((current) => [report, ...current]);
      setSelected(report);
      setNotice("Informe generado con métricas consolidadas del período.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo generar el informe");
    } finally { setBusy(false); }
  }

  async function publish(report: ImpactReport) {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await apiPost<ImpactReportPublishResult>(`/impact-reports/${report.id}/publish`, token, {});
      setSelected(result.report);
      setReports((current) => current.map((item) => item.id === result.report.id ? result.report : item));
      setShareUrl(result.share_url);
      await navigator.clipboard?.writeText(result.share_url).catch(() => undefined);
      setNotice("Enlace público creado y copiado. Publicarlo nuevamente revoca el enlace anterior.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo publicar el informe");
    } finally { setBusy(false); }
  }

  async function revoke(report: ImpactReport) {
    setBusy(true); setError(""); setShareUrl("");
    try {
      const result = await apiPost<ImpactReport>(`/impact-reports/${report.id}/revoke`, token, {});
      setSelected(result);
      setReports((current) => current.map((item) => item.id === result.id ? result : item));
      setNotice("Acceso público revocado.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo revocar el enlace");
    } finally { setBusy(false); }
  }

  async function remove(report: ImpactReport) {
    if (!window.confirm(`Eliminar el informe “${report.title}”?`)) return;
    setBusy(true);
    try {
      await apiDelete(`/impact-reports/${report.id}`, token);
      const next = reports.filter((item) => item.id !== report.id);
      setReports(next); setSelected(next[0] || null); setShareUrl("");
      setNotice("Informe eliminado.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo eliminar el informe");
    } finally { setBusy(false); }
  }

  function exportCsv(report: ImpactReport) {
    const rows: [string, unknown][] = [
      ["Código documental", String(report.official_metadata.document_code || "")],
      ["Organización", report.org_name], ["Título", report.title], ["Destinatario", report.recipient_name],
      ["Provincia", String(report.official_metadata.province || "Misiones")],
      ["Departamento", String(report.official_metadata.department || "")],
      ["Municipio", String(report.official_metadata.municipality || "")],
      ["Período desde", report.period_start], ["Período hasta", report.period_end],
      ["Nodos totales", report.metrics.devices_total], ["Nodos online", report.metrics.devices_online],
      ["Alertas", report.metrics.alerts_total], ["Alertas críticas", report.metrics.critical_alerts],
      ["Tiempo medio de detección (s)", report.metrics.average_detection_seconds],
      ["Precisión", report.metrics.model_precision], ["Reducción de respuesta", report.metrics.response_time_reduction],
      ["Reportes ciudadanos", report.metrics.citizen_reports_total], ["Reportes verificados", report.metrics.citizen_reports_verified],
    ];
    const content = ["campo,valor", ...rows.map(([key, value]) => `${csvEscape(key)},${csvEscape(value)}`)].join("\n");
    const url = URL.createObjectURL(new Blob(["\ufeff", content], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `econexo-informe-${report.period_end}.csv`; anchor.click(); URL.revokeObjectURL(url);
  }

  async function copyEmailBrief(report: ImpactReport) {
    const message = `${report.title}\n\nDestinatario: ${report.recipient_name}\nPeríodo: ${report.period_start} a ${report.period_end}\n\n${report.executive_summary}\n\nIndicadores: ${report.metrics.alerts_total} alertas, ${report.metrics.devices_online}/${report.metrics.devices_total} nodos operativos, ${report.metrics.average_detection_seconds ?? "s/d"} s de detección media.`;
    await navigator.clipboard.writeText(message);
    setNotice("Resumen listo para pegar en un correo o nota al organismo.");
  }

  return (
    <div className="view reports-workspace">
      <div className="view-title-row">
        <div><h2>Informes técnicos · Misiones</h2><div className="sub">Documentos extensos, trazables y territorialmente validados · {counts.total} informes · {counts.published} publicados</div></div>
        <span className="secure-badge">● ENLACES REVOCABLES</span>
      </div>

      <div className="report-builder-grid">
        <form className="report-builder" onSubmit={createReport}>
          <div className="panel-heading"><span>01</span><div><h3>Configurar informe</h3><p>El documento consolida exclusivamente datos ubicados dentro de Misiones.</p></div></div>
          <div className="form-two">
            <label>Tipo documental
              <select value={reportKind} onChange={(event) => setReportKind(event.target.value as ReportKind)}>
                <option value="desempeno_operativo">Informe de desempeño operativo</option>
                <option value="boletin_amenaza">Boletín técnico de amenaza</option>
                <option value="parte_tecnico">Parte técnico institucional</option>
                <option value="episodio_ambiental">Informe de episodio ambiental</option>
              </select>
            </label>
            <label>Snapshot SpaceAI
              <select value={snapshotId} disabled={reportKind === "desempeno_operativo" || !snapshots.length} onChange={(event) => setSnapshotId(event.target.value)}>
                <option value="">{snapshots.length ? "Último snapshot disponible" : "Sin snapshots registrados"}</option>
                {snapshots.map((item) => <option key={item.id} value={item.id}>{item.snapshot.overall_level} · {Math.round(item.snapshot.overall_score)}/100 · {new Date(item.created_at).toLocaleString("es-AR")}</option>)}
              </select>
            </label>
          </div>
          <label>Título<input value={title} maxLength={160} required onChange={(event) => setTitle(event.target.value)} /></label>
          <div className="form-two">
            <label>Destinatario
              <select value={recipientType} onChange={(event) => setRecipientType(event.target.value as RecipientType)}>
                <option value="programa_organismo">Programa / organismo (PO)</option><option value="organizacion">Organización</option><option value="municipio">Municipio</option><option value="inversor">Inversor</option><option value="aseguradora">Aseguradora</option><option value="auditoria">Auditoría</option>
              </select>
            </label>
            <label>Nombre<input value={recipientName} maxLength={160} required onChange={(event) => setRecipientName(event.target.value)} /></label>
          </div>
          <div className="form-two">
            <label>Desde<input type="date" value={periodStart} required onChange={(event) => setPeriodStart(event.target.value)} /></label>
            <label>Hasta<input type="date" value={periodEnd} required onChange={(event) => setPeriodEnd(event.target.value)} /></label>
          </div>
          <div className="report-lab-fields">
            <div className="panel-heading compact"><span>02</span><div><h3>Trazabilidad y revisión</h3><p>Datos que quedarán impresos en el documento técnico.</p></div></div>
            <div className="form-two">
              <label>Área emisora<input value={issuingArea} maxLength={160} onChange={(event) => setIssuingArea(event.target.value)} /></label>
              <label>Responsable revisor<input value={reviewedBy} maxLength={160} placeholder="Nombre, cargo o matrícula" onChange={(event) => setReviewedBy(event.target.value)} /></label>
            </div>
            <div className="form-two">
              <label>Laboratorio / institución<input value={laboratoryName} maxLength={160} placeholder="Opcional" onChange={(event) => setLaboratoryName(event.target.value)} /></label>
              <label>Protocolo / expediente<input value={protocolReference} maxLength={160} placeholder="Opcional" onChange={(event) => setProtocolReference(event.target.value)} /></label>
            </div>
            <label>Muestra / campaña / lote<input value={sampleReference} maxLength={160} placeholder="Identificador de trazabilidad, si corresponde" onChange={(event) => setSampleReference(event.target.value)} /></label>
          </div>
          <label>Resumen ejecutivo opcional<textarea rows={4} maxLength={4000} value={summary} placeholder="Si queda vacío, EcoNexo redacta un resumen metodológico con alcance Misiones." onChange={(event) => setSummary(event.target.value)} /></label>
          <label>Notas técnicas y observaciones de campo<textarea rows={5} maxLength={6000} value={technicalNotes} placeholder="Calibración, condiciones de muestreo, incidentes, datos faltantes o criterios de exclusión." onChange={(event) => setTechnicalNotes(event.target.value)} /></label>
          <label>Recomendaciones · una por línea<textarea rows={5} value={recommendations} onChange={(event) => setRecommendations(event.target.value)} /></label>
          <button className="primary report-generate" disabled={busy}>Generar informe con métricas</button>
          <p className="form-footnote">Los documentos congelan un snapshot versionado, incorporan fórmulas, fuentes, control de calidad y trazabilidad territorial. “Oficial” significa emitido por EcoNexo; toda comunicación pública R3-R5 requiere revisión humana y validación de la autoridad o laboratorio competente.</p>
        </form>

        <section className="report-library">
          <div className="panel-heading"><span>02</span><div><h3>Biblioteca</h3><p>Borradores y publicaciones recientes.</p></div></div>
          <div className="report-list">
            {reports.map((report) => <button type="button" key={report.id} className={`report-list-item ${selected?.id === report.id ? "active" : ""}`} onClick={() => { setSelected(report); setShareUrl(""); }}>
              <span className={`report-status ${report.status}`}>{report.status}</span><strong>{report.title}</strong><small>{report.recipient_name} · {report.period_end}</small>
            </button>)}
            {!reports.length && <div className="empty">Todavía no hay informes.</div>}
          </div>
        </section>
      </div>

      {error && <div className="workspace-message error" role="alert">{error}</div>}
      {notice && <div className="workspace-message success">{notice}</div>}
      {shareUrl && <div className="share-link-box"><label>Enlace público</label><input readOnly value={shareUrl} onFocus={(event) => event.currentTarget.select()} /><button onClick={() => void navigator.clipboard.writeText(shareUrl)}>Copiar</button><a href={shareUrl} target="_blank" rel="noreferrer">Abrir</a></div>}

      {selected && <section className="report-preview-area">
        <div className="report-actions no-print">
          <div><span className={`report-status ${selected.status}`}>{selected.status}</span><strong>Vista previa</strong></div>
          <div>
            <button onClick={() => window.print()}>Imprimir / guardar PDF</button>
            <button onClick={() => exportCsv(selected)}>Exportar CSV</button>
            <button onClick={() => void copyEmailBrief(selected)}>Copiar resumen</button>
            {selected.status === "publicado" ? <button onClick={() => void revoke(selected)} disabled={busy}>Revocar enlace</button> : <button className="primary" onClick={() => void publish(selected)} disabled={busy}>Publicar y copiar enlace</button>}
            <button className="danger" onClick={() => void remove(selected)} disabled={busy}>Eliminar</button>
          </div>
        </div>
        <ImpactReportDocument report={selected} />
      </section>}
    </div>
  );
}
