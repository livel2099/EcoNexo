"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import SiteFooter from "../../components/SiteFooter";
import TechLogo from "../../components/TechLogo";
import { publicGet, submitPublicReport } from "../lib/api";
import { assertMisionesCoordinates, misionesLocationLabel } from "../lib/misiones";

interface PubOrg { id: string; name: string; vertical: string; }
interface CitizenSession { token: string; expires_in_days: number; }
const CITIZEN_KEY = "econexo_citizen_session";

async function citizenToken(force = false): Promise<string> {
  if (!force) {
    const existing = localStorage.getItem(CITIZEN_KEY);
    if (existing) return existing;
  }
  const session = await publicGet<CitizenSession>("/reports/citizen-session");
  localStorage.setItem(CITIZEN_KEY, session.token);
  return session.token;
}

export default function Reportar() {
  const [orgs, setOrgs] = useState<PubOrg[]>([]);
  const [orgId, setOrgId] = useState("");
  const [type, setType] = useState("humo");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    publicGet<PubOrg[]>("/orgs/public").then((items) => {
      setOrgs(items); if (items[0]) setOrgId(items[0].id);
    }).catch(() => setError("No se pudieron cargar los territorios disponibles."));
    void citizenToken().catch(() => undefined);
  }, []);

  function locate() {
    setError(""); setLocating(true);
    if (!navigator.geolocation) { setError("Este dispositivo no admite geolocalización."); setLocating(false); return; }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        try {
          assertMisionesCoordinates(position.coords.latitude, position.coords.longitude);
          setLat(position.coords.latitude.toFixed(6));
          setLon(position.coords.longitude.toFixed(6));
        } catch (cause) { setError(cause instanceof Error ? cause.message : "La ubicación debe estar en Misiones."); }
        setLocating(false);
      },
      () => { setError("No se pudo obtener la ubicación. Ingresá las coordenadas manualmente."); setLocating(false); },
      { enableHighAccuracy: true, timeout: 12_000, maximumAge: 60_000 },
    );
  }

  function choosePhoto(file: File | null) {
    setError("");
    if (file && file.size > 8 * 1024 * 1024) {
      setPhoto(null); setError("La foto supera el máximo de 8 MB."); return;
    }
    setPhoto(file);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError("");
    const latitude = Number(lat); const longitude = Number(lon);
    if (!orgId || !Number.isFinite(latitude) || !Number.isFinite(longitude)) { setError("Seleccioná un territorio y una ubicación válida."); return; }
    try { assertMisionesCoordinates(latitude, longitude); } catch (cause) { setError(cause instanceof Error ? cause.message : "La ubicación debe estar en Misiones."); return; }
    if (!privacyAccepted) { setError("Debés aceptar el tratamiento de datos para enviar el reporte."); return; }
    setBusy(true);
    const form = new FormData();
    form.append("org_id", orgId); form.append("type", type);
    form.append("lat", String(latitude)); form.append("lon", String(longitude));
    form.append("citizen_token", await citizenToken());
    form.append("privacy_accepted", "true"); form.append("website", "");
    if (description.trim()) form.append("description", description.trim());
    if (photo) form.append("photo", photo);
    try {
      await submitPublicReport(form);
      setDone(true); setDescription(""); setPhoto(null);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "No se pudo enviar el reporte";
      if (/sesion ciudadana/i.test(message)) localStorage.removeItem(CITIZEN_KEY);
      setError(message);
    } finally { setBusy(false); }
  }

  return (
    <main className="citizen-page">
      <header className="citizen-header">
        <Link href="/" className="citizen-brand-link" aria-label="EcoNexo · inicio">
          <TechLogo compact showTagline={false} />
        </Link>
        <div className="citizen-header-actions">
          <span>REPORTES COMUNITARIOS</span>
          <Link href="/" className="citizen-home-link"><b aria-hidden="true">←</b> Volver al inicio</Link>
        </div>
      </header>
      <section className="citizen-layout">
        <aside className="citizen-context">
          <span className="eyebrow">EVIDENCIA DE CAMPO</span>
          <h1>Ayudá a detectar un incidente ambiental en Misiones.</h1>
          <p>Tu reporte se cruza con sensores, observación satelital y eventos activos. La organización destinataria decide su validación y respuesta.</p>
          <div className="citizen-steps"><div><b>01</b><span>Describí qué observás</span></div><div><b>02</b><span>Compartí ubicación y foto</span></div><div><b>03</b><span>EcoNexo correlaciona la evidencia</span></div></div>
          <div className="emergency-warning"><strong>No es un canal de emergencias.</strong><span>Ante fuego, humo o riesgo inmediato para personas o bienes en Misiones, alejate del peligro y llamá al 911.</span></div>
        </aside>

        <section className="citizen-form-card">
          {done ? <div className="report-success"><span>✓</span><h2>Reporte recibido</h2><p>La evidencia quedó en revisión y será correlacionada con las fuentes disponibles.</p><button className="primary" onClick={() => setDone(false)}>Enviar otro reporte</button></div> :
          <form onSubmit={submit}>
            <div className="panel-heading"><span>●</span><div><h2>Nuevo reporte</h2><p>Completá solamente datos que puedas observar de buena fe.</p></div></div>
            <label>Territorio u organización
              <select value={orgId} required onChange={(event) => setOrgId(event.target.value)}>
                <option value="" disabled>Seleccionar</option>{orgs.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}
              </select>
            </label>
            <label>Tipo de incidente
              <select value={type} onChange={(event) => setType(event.target.value)}><option value="humo">Humo</option><option value="incendio">Incendio</option><option value="inundacion">Inundación</option><option value="vertido">Vertido o contaminación</option><option value="otro">Otro</option></select>
            </label>
            <label>Descripción<textarea rows={4} maxLength={1000} value={description} placeholder="Qué observás, desde cuándo y qué referencias cercanas existen…" onChange={(event) => setDescription(event.target.value)} /><small>{description.length}/1000</small></label>
            <label>Foto opcional · JPG, PNG o WebP · máximo 8 MB<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(event) => choosePhoto(event.target.files?.[0] || null)} /></label>
            <div className="location-box"><div><strong>Ubicación del incidente</strong><small>Se usa únicamente para ubicar y correlacionar este reporte.</small></div><button type="button" onClick={locate} disabled={locating}>{locating ? "Ubicando…" : "Usar mi ubicación"}</button></div>
            {/* `Number("")` es 0, y 0 pasa `isFinite`: con los campos vacios la nota
                anunciaba "fuera del territorio" antes de que hubiera una ubicacion. */}
            {lat.trim() && lon.trim() && Number.isFinite(Number(lat)) && Number.isFinite(Number(lon))
              ? <div className="territory-inline-note">{misionesLocationLabel(Number(lat), Number(lon))}</div>
              : <div className="territory-inline-note">Compartí tu ubicación para validar el territorio.</div>}
            <div className="form-two"><label>Latitud<input inputMode="decimal" required value={lat} placeholder="-26.820000" onChange={(event) => setLat(event.target.value)} /></label><label>Longitud<input inputMode="decimal" required value={lon} placeholder="-54.450000" onChange={(event) => setLon(event.target.value)} /></label></div>
            <label className="legal-check"><input type="checkbox" checked={privacyAccepted} onChange={(event) => setPrivacyAccepted(event.target.checked)} /><span>Autorizo el tratamiento de ubicación, descripción e imagen conforme a la <Link href="/privacidad" target="_blank">Política de Privacidad</Link>. Declaro que el reporte es de buena fe y que tengo derecho a compartir la imagen.</span></label>
            {error && <div className="auth-error" role="alert">{error}</div>}
            <button className="primary citizen-submit" disabled={busy}>{busy ? "Enviando…" : "Enviar reporte para validación"}</button>
          </form>}
        </section>
      </section>
      <SiteFooter compact />
    </main>
  );
}
