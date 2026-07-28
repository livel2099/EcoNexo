"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { changePassword, clearSession, getSession, saveSession } from "../lib/api";
import type { Session } from "../lib/types";
import CircuitBackdrop from "../../components/CircuitBackdrop";
import TechLogo from "../../components/TechLogo";

function destination(session: Session): string {
  return session.platform_admin ? "/plataforma" : "/dashboard";
}

export default function ChangePasswordPage() {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const current = getSession();
    if (!current) {
      router.replace("/login");
      return;
    }
    if (!current.must_change_password) {
      router.replace(destination(current));
      return;
    }
    setSession(current);
  }, [router]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!session) return;
    setError("");
    if (newPassword.length < 12 || !/[A-Za-zÁÉÍÓÚáéíóúÑñ]/.test(newPassword) || !/\d/.test(newPassword)) {
      setError("Usá al menos 12 caracteres, una letra y un número.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Las contraseñas nuevas no coinciden.");
      return;
    }
    if (currentPassword === newPassword) {
      setError("La contraseña nueva debe ser diferente de la temporal.");
      return;
    }
    setBusy(true);
    try {
      await changePassword(session.access_token, currentPassword, newPassword);
      const updated = { ...session, must_change_password: false };
      saveSession(updated);
      router.replace(destination(updated));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo cambiar la contraseña");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="platform-gate-page">
      <CircuitBackdrop dense />
      <section className="platform-gate-card">
        <TechLogo className="platform-gate-logo" showTagline />
        <span className="eyebrow">SEGURIDAD OBLIGATORIA</span>
        <h1>Cambiá la contraseña temporal</h1>
        <p>La cuenta administrativa fue creada con una credencial inicial. Definí una contraseña privada antes de abrir la consola general.</p>
        <form onSubmit={submit} className="platform-password-form">
          <label>Contraseña temporal
            <input required type="password" autoComplete="current-password" minLength={6} value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
          </label>
          <label>Nueva contraseña
            <input required type="password" autoComplete="new-password" minLength={12} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
          </label>
          <label>Repetir nueva contraseña
            <input required type="password" autoComplete="new-password" minLength={12} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
          </label>
          <small>Mínimo 12 caracteres, al menos una letra y un número.</small>
          {error && <div className="workspace-message error" role="alert">{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "Actualizando…" : "Guardar contraseña segura"}</button>
          <button type="button" className="platform-text-button" onClick={() => { clearSession(); router.replace("/login"); }}>Salir de esta cuenta</button>
        </form>
      </section>
    </main>
  );
}
