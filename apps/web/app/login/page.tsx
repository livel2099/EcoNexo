"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, saveSession } from "../lib/api";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      const s = await login(email, password);
      saveSession(s);
      router.replace("/dashboard");
    } catch {
      setErr("Credenciales invalidas");
    }
  }

  return (
    <div className="center">
      <form className="card" onSubmit={submit}>
        <div className="brand" style={{ fontSize: 22, marginBottom: 4 }}>ECO<span>NEXO</span></div>
        <div className="muted" style={{ marginBottom: 18 }}>Centro de Comando</div>
        <label>Email</label>
        <input type="email" autoComplete="off" placeholder="tu@organizacion.econexo.ar" value={email} onChange={(e) => setEmail(e.target.value)} />
        <label>Contraseña</label>
        <input type="password" autoComplete="off" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} />
        {err && <div className="err">{err}</div>}
        <button className="primary" style={{ width: "100%", marginTop: 8 }}>Ingresar</button>
        <div className="muted" style={{ fontSize: 11, marginTop: 14 }}>
          Demo: admin@forestandes.econexo.ar / econexo123
        </div>
      </form>
    </div>
  );
}
