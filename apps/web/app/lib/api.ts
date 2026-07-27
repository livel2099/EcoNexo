import type { Session } from "./types";
import {
  demoDelete,
  demoGet,
  demoGoogleLogin,
  demoLogin,
  demoPatch,
  demoPost,
  demoRegisterEmail,
  demoSubmitReport,
} from "./demo";

export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
export const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
export const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

const KEY = "econexo_session";
const DEFAULT_TIMEOUT_MS = 12_000;

export function saveSession(session: Session) {
  sessionStorage.setItem(KEY, JSON.stringify(session));
  localStorage.removeItem(KEY);
}
export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const current = sessionStorage.getItem(KEY);
  const legacy = localStorage.getItem(KEY);
  const raw = current || legacy;
  if (!raw) return null;
  try {
    const session = JSON.parse(raw) as Session;
    if (!current) {
      sessionStorage.setItem(KEY, raw);
      localStorage.removeItem(KEY);
    }
    return session;
  } catch {
    clearSession();
    return null;
  }
}
export function clearSession() {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(KEY);
  localStorage.removeItem(KEY);
}

async function request(url: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") {
      throw new Error(`La API de EcoNexo no respondió a tiempo (${API}).`);
    }
    throw new Error(
      `No se pudo conectar con la API de EcoNexo en ${API}. Verificá que Docker esté iniciado y que ${API}/health responda.`,
      { cause },
    );
  } finally {
    window.clearTimeout(timer);
  }
}

async function responseError(response: Response, fallback: string): Promise<Error> {
  try {
    const body = await response.json() as { detail?: string | { msg?: string }[] };
    if (typeof body.detail === "string") return new Error(body.detail);
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return new Error(body.detail[0].msg);
  } catch { /* response without JSON */ }
  return new Error(`${fallback} (${response.status})`);
}

async function checked<T>(response: Response, fallback: string, redirectUnauthorized = true): Promise<T> {
  if (response.status === 401 && redirectUnauthorized) {
    clearSession();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/informe")) {
      window.location.assign("/");
    }
  }
  if (!response.ok) throw await responseError(response, fallback);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function getApiStatus(): Promise<boolean> {
  if (IS_DEMO) return true;
  try {
    const response = await request(`${API}/health`, { cache: "no-store" }, 4_000);
    return response.ok;
  } catch {
    return false;
  }
}

export async function login(email: string, password: string): Promise<Session> {
  if (IS_DEMO) return demoLogin(email, password);
  return checked<Session>(await request(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  }), "No se pudo iniciar sesión", false);
}

export interface EmailRegisterInput {
  organization_name: string;
  vertical: "municipio" | "forestal" | "energetica";
  municipality?: string;
  department?: string;
  name: string;
  email: string;
  password: string;
  terms_accepted: boolean;
  legal_version?: string;
}

export async function registerWithEmail(input: EmailRegisterInput): Promise<Session> {
  if (IS_DEMO) return demoRegisterEmail(input);
  return checked<Session>(await request(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }), "No se pudo crear la organización", false);
}

export interface GoogleAuthInput {
  credential: string;
  mode: "login" | "register";
  organization_name?: string;
  vertical?: "municipio" | "forestal" | "energetica";
  municipality?: string;
  department?: string;
  terms_accepted?: boolean;
  legal_version?: string;
}

export async function loginWithGoogle(input: GoogleAuthInput): Promise<Session> {
  if (IS_DEMO) return demoGoogleLogin(input);
  return checked<Session>(await request(`${API}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }), "No se pudo validar la cuenta de Google", false);
}

export async function apiGet<T>(path: string, token: string): Promise<T> {
  if (IS_DEMO) return demoGet<T>(path);
  return checked<T>(await request(`${API}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  }), `GET ${path}`);
}

export async function apiPost<T>(path: string, token: string, body: unknown): Promise<T> {
  if (IS_DEMO) return demoPost<T>(path, body);
  return checked<T>(await request(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  }), `POST ${path}`);
}

export async function apiPostForm<T>(path: string, token: string, form: FormData): Promise<T> {
  if (IS_DEMO) {
    if (path === "/reports/internal") {
      await demoSubmitReport(form);
      return undefined as T;
    }
    throw new Error(`Ruta demo no implementada: POST FORM ${path}`);
  }
  return checked<T>(await request(`${API}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  }, 30_000), `POST ${path}`);
}

export async function apiPatch<T>(path: string, token: string, body?: unknown): Promise<T> {
  if (IS_DEMO) return demoPatch<T>(path, body);
  return checked<T>(await request(`${API}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: body === undefined ? undefined : JSON.stringify(body),
  }), `PATCH ${path}`);
}

export async function apiDelete(path: string, token: string): Promise<void> {
  if (IS_DEMO) return demoDelete(path);
  await checked<void>(await request(`${API}${path}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  }), `DELETE ${path}`);
}

export async function publicGet<T>(path: string): Promise<T> {
  if (IS_DEMO) return demoGet<T>(path);
  return checked<T>(await request(`${API}${path}`, { cache: "no-store" }), `GET ${path}`);
}

export async function submitPublicReport(form: FormData): Promise<void> {
  if (IS_DEMO) return demoSubmitReport(form);
  await checked<void>(await request(`${API}/reports`, { method: "POST", body: form }), "No se pudo enviar el reporte");
}
