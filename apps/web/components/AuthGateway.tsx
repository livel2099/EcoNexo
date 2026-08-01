"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  GOOGLE_CLIENT_ID,
  IS_DEMO,
  getApiStatus,
  getSession,
  login,
  loginWithGoogle,
  registerWithEmail,
  saveSession,
} from "../app/lib/api";
import SiteFooter from "./SiteFooter";
import TechLogo from "./TechLogo";
import { MISIONES_MUNICIPALITIES, municipalityDepartment } from "../app/lib/misiones";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize(config: { client_id: string; callback: (response: { credential: string }) => void; ux_mode?: string; auto_select?: boolean }): void;
          renderButton(element: HTMLElement, options: Record<string, string | number | boolean>): void;
          cancel(): void;
        };
      };
    };
  }
}

type Mode = "login" | "register";
type Vertical = "municipio" | "forestal" | "energetica";
type ApiStatus = "checking" | "online" | "offline" | "demo";

const LEGAL_VERSION = "2026-07-27";

export default function AuthGateway() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState(IS_DEMO ? "admin@misiones.econexo.ar" : "");
  const [password, setPassword] = useState(IS_DEMO ? "econexo123" : "");
  const [confirmPassword, setConfirmPassword] = useState(IS_DEMO ? "econexo123" : "");
  const [fullName, setFullName] = useState(IS_DEMO ? "Administración EcoNexo" : "");
  const [organizationName, setOrganizationName] = useState(IS_DEMO ? "EcoNexo Misiones · Red Provincial" : "");
  const [vertical, setVertical] = useState<Vertical>("forestal");
  const [municipality, setMunicipality] = useState("Posadas");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [googleReady, setGoogleReady] = useState(false);
  const [apiStatus, setApiStatus] = useState<ApiStatus>(IS_DEMO ? "demo" : "checking");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const googleButton = useRef<HTMLDivElement>(null);
  const formRef = useRef({ mode, organizationName, vertical, municipality, termsAccepted });
  const selectedDepartment = municipalityDepartment(municipality) || "Capital";
  const googleRegistrationReady = mode === "login" || Boolean(organizationName.trim() && termsAccepted);

  useEffect(() => {
    formRef.current = { mode, organizationName, vertical, municipality, termsAccepted };
  }, [mode, organizationName, vertical, municipality, termsAccepted]);

  useEffect(() => {
    if (getSession()) router.replace("/dashboard");
  }, [router]);

  const checkConnection = useCallback(async () => {
    if (IS_DEMO) {
      setApiStatus("demo");
      return;
    }
    setApiStatus("checking");
    setApiStatus(await getApiStatus() ? "online" : "offline");
  }, []);

  useEffect(() => {
    void checkConnection();
  }, [checkConnection]);

  async function finishGoogle(credential: string) {
    const current = formRef.current;
    setError("");
    setBusy(true);
    try {
      const session = await loginWithGoogle({
        credential,
        mode: current.mode,
        organization_name: current.mode === "register" ? current.organizationName : undefined,
        vertical: current.mode === "register" ? current.vertical : undefined,
        municipality: current.mode === "register" ? current.municipality : undefined,
        department: current.mode === "register" ? municipalityDepartment(current.municipality) || "Capital" : undefined,
        terms_accepted: current.mode === "register" ? current.termsAccepted : undefined,
        legal_version: LEGAL_VERSION,
      });
      saveSession(session);
      router.replace("/dashboard");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo iniciar sesión con Google");
      void checkConnection();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    const existing = document.getElementById("google-identity-services") as HTMLScriptElement | null;
    const setup = () => setGoogleReady(true);
    if (window.google) {
      setup();
      return;
    }
    if (existing) {
      existing.addEventListener("load", setup, { once: true });
      return () => existing.removeEventListener("load", setup);
    }
    const script = document.createElement("script");
    script.id = "google-identity-services";
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = setup;
    script.onerror = () => setError("No se pudo cargar Google Identity Services");
    document.head.appendChild(script);
  }, []);

  useEffect(() => {
    if (!googleReady || !GOOGLE_CLIENT_ID || !googleRegistrationReady || !window.google || !googleButton.current) return;
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: ({ credential }) => void finishGoogle(credential),
      ux_mode: "popup",
      auto_select: false,
    });
    googleButton.current.replaceChildren();
    window.google.accounts.id.renderButton(googleButton.current, {
      type: "standard",
      theme: "filled_black",
      size: "large",
      shape: "pill",
      text: mode === "register" ? "signup_with" : "signin_with",
      logo_alignment: "center",
      width: 400,
      locale: "es",
    });
  }, [googleReady, mode, googleRegistrationReady]);

  async function emailSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");

    if (mode === "register") {
      if (!organizationName.trim() || !fullName.trim()) {
        setError("Completá el nombre de la organización y tu nombre.");
        return;
      }
      if (password.length < 8 || !/[A-Za-zÁÉÍÓÚáéíóúÑñ]/.test(password) || !/\d/.test(password)) {
        setError("La contraseña debe tener al menos 8 caracteres, una letra y un número.");
        return;
      }
      if (password !== confirmPassword) {
        setError("Las contraseñas no coinciden.");
        return;
      }
      if (!termsAccepted) {
        setError("Debés aceptar los Términos y la Política de Privacidad.");
        return;
      }
    }

    setBusy(true);
    try {
      const session = mode === "register"
        ? await registerWithEmail({
            organization_name: organizationName.trim(),
            vertical,
            municipality,
            department: selectedDepartment,
            name: fullName.trim(),
            email,
            password,
            terms_accepted: termsAccepted,
            legal_version: LEGAL_VERSION,
          })
        : await login(email, password);
      saveSession(session);
      router.replace("/dashboard");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : mode === "register" ? "No se pudo crear la organización" : "Credenciales inválidas");
      void checkConnection();
    } finally {
      setBusy(false);
    }
  }

  function changeMode(nextMode: Mode) {
    setMode(nextMode);
    setError("");
  }

  return (
    <main className="auth-page">
      <section className="auth-hero" aria-labelledby="auth-title">
        <TechLogo className="auth-brand-logo" showTagline />
        <div className="auth-kicker"><i /> Plataforma de decisión ambiental en tiempo real</div>
        <h1 id="auth-title">Detectar antes.<br /><span>Decidir mejor.</span></h1>
        <p>
          EcoNexo integra sensores IoT, observación satelital y reportes ciudadanos para convertir señales de los 17 departamentos y 79 municipios de Misiones en alertas verificables, acciones trazables e informes institucionales.
        </p>
        <div className="auth-proof-grid" aria-label="Capacidades principales">
          <article><strong>&lt; 5 min</strong><span>objetivo de detección</span></article>
          <article><strong>Multifuente</strong><span>IoT · satélite · ciudadanía</span></article>
          <article><strong>PostGIS + IA</strong><span>correlación espacial</span></article>
        </div>
        <div className="auth-flow" aria-label="Flujo operativo">
          <span>OBSERVAR</span><b>→</b><span>CORRELACIONAR</span><b>→</b><span>PRIORIZAR</span><b>→</b><span>ACTUAR</span>
        </div>
      </section>

      <section className="auth-panel-wrap">
        <div className="auth-panel">
          <div className="auth-panel-brand"><img src="/brand/econexo-lockup.jpg" alt="EcoNexo · análisis predictivo y decisiones en tiempo real" className="official-auth-logo" /></div>

          <div className={`auth-api-status ${apiStatus}`}>
            <i />
            <span>{apiStatus === "demo" ? "Demo autónoma activa" : apiStatus === "online" ? "API y base conectadas" : apiStatus === "checking" ? "Verificando conexión…" : "API sin conexión"}</span>
            {apiStatus === "offline" && <button type="button" onClick={() => void checkConnection()}>Reintentar</button>}
          </div>

          <div className="auth-tabs" role="tablist" aria-label="Acceso a EcoNexo">
            <button type="button" role="tab" aria-selected={mode === "login"} className={mode === "login" ? "active" : ""} onClick={() => changeMode("login")}>Ingresar</button>
            <button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "active" : ""} onClick={() => changeMode("register")}>Crear organización</button>
          </div>

          <div className="auth-panel-heading">
            <span className="eyebrow">ACCESO SEGURO</span>
            <h2>{mode === "login" ? "Bienvenido de nuevo" : "Activá tu espacio institucional"}</h2>
            <p>{mode === "login" ? "Ingresá al centro de comando y a tus informes." : "Registrate con email. El primer usuario quedará como administrador; Google es opcional."}</p>
          </div>

          <form onSubmit={emailSubmit} className={`email-login ${mode === "register" ? "email-registration" : ""}`}>
            {mode === "register" && (
              <>
                <div className="registration-fields">
                  <label>Nombre de la organización
                    <input required value={organizationName} maxLength={120} onChange={(event) => setOrganizationName(event.target.value)} placeholder="Municipalidad, empresa o programa" />
                  </label>
                  <label>Localidad base en Misiones
                    <select value={municipality} onChange={(event) => setMunicipality(event.target.value)}>
                      {MISIONES_MUNICIPALITIES.map((item) => <option key={`${item.department}-${item.name}`} value={item.name}>{item.name} · Dpto. {item.department}</option>)}
                    </select>
                  </label>
                  <label>Tipo de operación
                    <select value={vertical} onChange={(event) => setVertical(event.target.value as Vertical)}>
                      <option value="forestal">Forestal y biodiversidad</option>
                      <option value="municipio">Municipio y gestión territorial</option>
                      <option value="energetica">Energía e infraestructura crítica</option>
                    </select>
                  </label>
                </div>
                <label>Nombre y apellido del administrador
                  <input required value={fullName} maxLength={100} autoComplete="name" onChange={(event) => setFullName(event.target.value)} placeholder="Miguel Elías Ibachuta" />
                </label>
              </>
            )}

            <label>Email
              <input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="tu@organizacion.org" />
            </label>

            <div className={mode === "register" ? "password-grid" : ""}>
              <label>Contraseña
                <input type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} required minLength={mode === "register" ? 8 : 6} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" />
              </label>
              {mode === "register" && (
                <label>Repetir contraseña
                  <input type="password" autoComplete="new-password" required minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="••••••••" />
                </label>
              )}
            </div>

            {mode === "register" && (
              <>
                <small className="password-help">Mínimo 8 caracteres, al menos una letra y un número.</small>
                <label className="legal-check">
                  <input type="checkbox" checked={termsAccepted} onChange={(event) => setTermsAccepted(event.target.checked)} />
                  <span>Acepto los <Link href="/terminos" target="_blank">Términos y Condiciones</Link> y la <Link href="/privacidad" target="_blank">Política de Privacidad</Link>.</span>
                </label>
              </>
            )}

            <button className="primary auth-submit" disabled={busy || apiStatus === "checking"}>
              {busy ? "Procesando…" : mode === "register" ? "Crear organización y entrar" : "Ingresar al centro de comando"}
            </button>
          </form>

          {(GOOGLE_CLIENT_ID || IS_DEMO) && (
            <>
              <div className="auth-separator"><span>o continuar con Google</span></div>
              <div className="google-auth-area">
                {!googleRegistrationReady
                  ? <button className="google-demo-button" type="button" disabled aria-disabled="true"><GoogleMark /> Completá la organización para continuar</button>
                  : IS_DEMO && !GOOGLE_CLIENT_ID
                    ? <button className="google-demo-button" type="button" disabled={busy} onClick={() => void finishGoogle("demo-google-credential-for-cloudflare-preview")}><GoogleMark /> Continuar con Google · demo</button>
                    : <div ref={googleButton} className="google-native-button" aria-live="polite" />}
              </div>
            </>
          )}

          {!GOOGLE_CLIENT_ID && !IS_DEMO && <div className="auth-config-ok">Registro por email habilitado · agregá NEXT_PUBLIC_GOOGLE_CLIENT_ID para activar Google</div>}
          {error && <div className="auth-error" role="alert">{error}</div>}
          {IS_DEMO && <div className="demo-note">Demo autónoma · los datos se guardan solamente en este navegador</div>}
          <p className="auth-security-copy">Las contraseñas del modo completo se procesan en la API y se almacenan con hash Argon2. EcoNexo nunca guarda contraseñas en texto plano.</p>
        </div>
      </section>
      <SiteFooter compact />
    </main>
  );
}

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.205c0-.638-.057-1.252-.164-1.841H9v3.482h4.844a4.14 4.14 0 0 1-1.797 2.716v2.258h2.91c1.703-1.568 2.683-3.878 2.683-6.615Z"/>
      <path fill="#34A853" d="M9 18c2.43 0 4.468-.806 5.957-2.18l-2.91-2.258c-.806.54-1.835.859-3.047.859-2.344 0-4.328-1.584-5.037-3.711H.956v2.333A9 9 0 0 0 9 18Z"/>
      <path fill="#FBBC05" d="M3.963 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.281-1.71V4.957H.956A9 9 0 0 0 0 9c0 1.452.347 2.827.956 4.043l3.007-2.333Z"/>
      <path fill="#EA4335" d="M9 3.579c1.321 0 2.507.454 3.441 1.346l2.581-2.581C13.464.892 11.426 0 9 0A9 9 0 0 0 .956 4.957L3.963 7.29C4.672 5.163 6.656 3.579 9 3.579Z"/>
    </svg>
  );
}
