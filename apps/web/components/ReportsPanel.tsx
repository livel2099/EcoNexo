"use client";

import { useEffect, useRef, useState } from "react";
import { apiGet, apiPost, apiPostForm } from "../app/lib/api";
import type { Report } from "../app/lib/types";
import { MISIONES_CENTER, assertMisionesCoordinates, misionesLocationLabel } from "../app/lib/misiones";

function scoreColor(value: number | null): string {
  if (value == null) return "#5c6f65";
  return value >= 0.66 ? "#37D08A" : value >= 0.33 ? "#D97706" : "#DC2626";
}

export default function ReportsPanel({ token }: { token: string }) {
  const [reports, setReports] = useState<Report[]>([]);
  const [type, setType] = useState("humo");
  const [description, setDescription] = useState("");
  const [lat, setLat] = useState(String(MISIONES_CENTER[0]));
  const [lon, setLon] = useState(String(MISIONES_CENTER[1]));
  const [photo, setPhoto] = useState<File | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = () => apiGet<Report[]>("/reports", token).then(setReports).catch(() => undefined);
  useEffect(() => { void load(); }, [token]);

  async function moderate(id: string, status: "verificado" | "rechazado") {
    await apiPost(`/reports/${id}/moderate`, token, { status });
    await load();
  }

  function useLocation() {
    setNotice("");
    if (!navigator.geolocation) return setNotice("El navegador no ofrece geolocalización.");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        try {
          assertMisionesCoordinates(position.coords.latitude, position.coords.longitude);
          setLat(position.coords.latitude.toFixed(6));
          setLon(position.coords.longitude.toFixed(6));
          setNotice(`Ubicación cargada: ${misionesLocationLabel(position.coords.latitude, position.coords.longitude)}.`);
        } catch (cause) { setNotice(cause instanceof Error ? cause.message : "La ubicación no pertenece a Misiones."); }
      },
      () => setNotice("No se pudo obtener la ubicación. Podés escribir las coordenadas manualmente."),
      { enableHighAccuracy: true, timeout: 12_000, maximumAge: 60_000 },
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setNotice("");
    const latitude = Number(lat);
    const longitude = Number(lon);
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90 || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      return setNotice("Revisá las coordenadas.");
    }
    try { assertMisionesCoordinates(latitude, longitude); } catch (cause) { return setNotice(cause instanceof Error ? cause.message : "La ubicación debe estar en Misiones."); }
    if (description.trim().length < 5) return setNotice("Describí brevemente lo observado.");
    setBusy(true);
    try {
      const form = new FormData();
      form.set("type", type);
      form.set("description", description.trim());
      form.set("lat", String(latitude));
      form.set("lon", String(longitude));
      if (photo) form.set("photo", photo);
      await apiPostForm<Report>("/reports/internal", token, form);
      setDescription(""); setPhoto(null);
      if (fileRef.current) fileRef.current.value = "";
      setNotice("Reporte cargado. Quedó pendiente de verificación y trazado en auditoría.");
      await load();
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "No se pudo cargar el reporte.");
    } finally { setBusy(false); }
  }

  const pending = reports.filter((report) => report.status === "pendiente").length;

  return (
    <div className="view reports-workspace">
      <div className="workspace-heading"><div><span className="eyebrow">COMUNIDAD + EQUIPOS DE CAMPO</span><h2>Reportes comunitarios e institucionales</h2><p>Cargá humo, fuego, inundación, vertidos u otra evidencia. La observación entra a una cola de moderación y se contrasta con sensores, satélite y alertas.</p></div><div className="workspace-stats"><strong>{reports.length}</strong><span>totales</span><b>{pending} pendientes</b></div></div>

      <section className="community-report-form-card">
        <div className="panel-heading"><span>01</span><div><h3>Cargar un reporte</h3><p>El formulario no reemplaza una llamada al 911 ante fuego, humo o riesgo inmediato en Misiones.</p></div></div>
        <form onSubmit={submit} className="community-report-form">
          <label>Tipo de observación<select value={type} onChange={(event) => setType(event.target.value)}><option value="humo">Humo</option><option value="incendio">Fuego / incendio</option><option value="inundacion">Inundación</option><option value="vertido">Vertido o contaminación</option><option value="otro">Otro</option></select></label>
          <label className="report-description">Descripción<textarea maxLength={1000} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Qué se observa, desde dónde, hacia qué dirección y desde cuándo..." /></label>
          <label>Latitud<input inputMode="decimal" value={lat} onChange={(event) => setLat(event.target.value)} /></label>
          <label>Longitud<input inputMode="decimal" value={lon} onChange={(event) => setLon(event.target.value)} /></label>
          <label className="report-photo">Foto opcional<input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setPhoto(event.target.files?.[0] || null)} /><small>JPG, PNG o WEBP; máximo 8 MB. Evitá fotografiar rostros o patentes si no es necesario.</small></label>
          <div className="community-report-actions"><button type="button" onClick={useLocation}>Usar mi ubicación</button><button className="primary" disabled={busy} type="submit">{busy ? "Enviando…" : "Enviar reporte"}</button></div>
        </form>
        {notice && <div className="workspace-message">{notice}</div>}
      </section>

      <section className="report-moderation-card">
        <div className="panel-heading"><span>02</span><div><h3>Cola de verificación</h3><p>Correlación IA × reputación del emisor × evidencia disponible.</p></div></div>
        <div className="table-scroll"><table>
          <thead><tr><th>Tipo</th><th>Descripción</th><th>Correlación IA</th><th>Reputación</th><th>Estado</th><th>Ubicación</th><th>Foto</th><th>Acción</th></tr></thead>
          <tbody>{reports.map((report) => <tr key={report.id}>
            <td style={{ fontWeight: 600, textTransform: "capitalize" }}>{report.type}</td>
            <td className="muted report-description-cell">{report.description || "—"}</td>
            <td className="score" style={{ color: scoreColor(report.correlation_score) }}>{report.correlation_score != null ? `${Math.round(report.correlation_score * 100)}%` : "—"}</td>
            <td className="score" style={{ color: scoreColor(report.reputation_score) }}>{report.reputation_score != null ? `${Math.round(report.reputation_score * 100)}%` : "—"}</td>
            <td><span className={`stat ${report.status === "verificado" ? "online" : report.status === "rechazado" ? "alerta" : "offline"}`}>● {report.status}</span></td>
            <td><small>{misionesLocationLabel(report.lat, report.lon)}</small></td>
            <td>{report.photo_url ? <a href={report.photo_url} target="_blank" rel="noreferrer">ver</a> : "—"}</td>
            <td>{report.status === "pendiente" && <div className="inline-actions"><button className="sm primary" onClick={() => void moderate(report.id, "verificado")}>Verificar</button><button className="sm danger" onClick={() => void moderate(report.id, "rechazado")}>Rechazar</button></div>}</td>
          </tr>)}</tbody>
        </table></div>
        {reports.length === 0 && <div className="empty">Todavía no hay reportes.</div>}
      </section>
    </div>
  );
}
