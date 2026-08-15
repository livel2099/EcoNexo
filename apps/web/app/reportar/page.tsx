"use client";
import { useEffect, useState } from "react";
import { API } from "../lib/api";

// PWA publica mobile-first: reporte ciudadano (tipo, foto, geolocalizacion).
interface PubOrg { id: string; name: string; vertical: string; }

function citizenToken(): string {
  let t = localStorage.getItem("econexo_citizen");
  if (!t) { t = crypto.randomUUID(); localStorage.setItem("econexo_citizen", t); }
  return t;
}

export default function Reportar() {
  const [orgs, setOrgs] = useState<PubOrg[]>([]);
  const [orgId, setOrgId] = useState("");
  const [type, setType] = useState("humo");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [pos, setPos] = useState<{ lat: number; lon: number } | null>(null);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    fetch(`${API}/orgs/public`).then((r) => r.json()).then((o: PubOrg[]) => {
      setOrgs(o); if (o[0]) setOrgId(o[0].id);
    }).catch(() => {});
    navigator.geolocation?.getCurrentPosition(
      (p) => setPos({ lat: p.coords.latitude, lon: p.coords.longitude }),
      () => setPos({ lat: -26.82, lon: -54.45 })
    );
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    if (!pos || !orgId) { setErr("Falta ubicacion u organizacion"); return; }
    const fd = new FormData();
    fd.append("org_id", orgId); fd.append("type", type);
    fd.append("lat", String(pos.lat)); fd.append("lon", String(pos.lon));
    fd.append("citizen_token", citizenToken());
    if (description) fd.append("description", description);
    if (photo) fd.append("photo", photo);
    const r = await fetch(`${API}/reports`, { method: "POST", body: fd });
    if (r.ok) setDone(true); else setErr("No se pudo enviar el reporte");
  }

  if (done) return (
    <div className="center"><div className="card" style={{ textAlign: "center" }}>
      <div style={{ fontSize: 40 }}>✅</div>
      <h3>Reporte enviado</h3>
      <p className="muted">Se correlacionara con sensores y satelite. Gracias.</p>
      <button className="primary" onClick={() => setDone(false)}>Enviar otro</button>
    </div></div>
  );

  return (
    <div className="center">
      <form className="card" onSubmit={submit}>
        <div className="brand" style={{ fontSize: 20 }}>ECO<span>NEXO</span></div>
        <div className="muted" style={{ marginBottom: 16 }}>Reportar incidente ambiental</div>
        <label>Territorio</label>
        <select value={orgId} onChange={(e) => setOrgId(e.target.value)}>
          {orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
        <label>Tipo de incidente</label>
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="humo">Humo</option>
          <option value="incendio">Incendio</option>
          <option value="inundacion">Inundacion</option>
          <option value="vertido">Vertido / contaminacion</option>
          <option value="otro">Otro</option>
        </select>
        <label>Descripcion</label>
        <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        <label>Foto</label>
        <input type="file" accept="image/*" capture="environment" onChange={(e) => setPhoto(e.target.files?.[0] || null)} />
        <div className="muted mono" style={{ fontSize: 11, marginBottom: 10 }}>
          📍 {pos ? `${pos.lat.toFixed(4)}, ${pos.lon.toFixed(4)}` : "obteniendo ubicacion…"}
        </div>
        {err && <div className="err">{err}</div>}
        <button className="primary" style={{ width: "100%" }}>Enviar reporte</button>
      </form>
    </div>
  );
}
