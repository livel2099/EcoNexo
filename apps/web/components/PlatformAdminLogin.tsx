"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { IS_DEMO, login, saveSession } from "../app/lib/api";

export default function PlatformAdminLogin() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      if (IS_DEMO) throw new Error("El acceso administrativo requiere la API de producción.");
      const session = await login(email.trim(), password);
      if (!session.platform_admin || session.role !== "admin") {
        throw new Error("Acceso reservado a administradores de la plataforma.");
      }
      saveSession(session);
      setPassword("");
      router.replace(session.must_change_password ? "/cambiar-contrasena" : "/plataforma");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo validar el acceso.");
    } finally { setBusy(false); }
  }

  return <main className="platform-console">
    <form className="platform-user-create" style={{ maxWidth: 480, margin: "8vh auto" }} onSubmit={submit}>
      <div><span className="eyebrow">ECO/NEXO · ACCESO PRIVADO</span><h1>Administración de plataforma</h1><p>Ingresá con tu cuenta autorizada.</p></div>
      <label>Correo<input required type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <label>Contraseña<input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      {error && <p role="alert" className="workspace-message error">{error}</p>}
      <button className="primary" disabled={busy || IS_DEMO}>{busy ? "Validando…" : "Ingresar"}</button>
      {IS_DEMO && <p>La consola privada no está disponible en modo demo.</p>}
    </form>
  </main>;
}
