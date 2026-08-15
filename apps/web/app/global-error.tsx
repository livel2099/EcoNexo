"use client";

import { useEffect } from "react";
import { reportError } from "./lib/observability";

/**
 * Límite de error de último recurso: se activa si falla el propio layout raíz.
 * Debe renderizar su propio <html>/<body> y usar estilos en línea, porque
 * reemplaza por completo al layout (y por lo tanto a globals.css).
 */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    reportError(error, { source: "global-error", digest: error.digest });
  }, [error]);

  return (
    <html lang="es-AR">
      <body style={{ margin: 0, minHeight: "100vh", display: "grid", placeItems: "center", background: "#020608", color: "#eafff5", fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif" }}>
        <div style={{ maxWidth: 420, padding: "32px 28px", textAlign: "center", border: "1px solid rgba(143,240,106,.22)", borderRadius: 20, background: "linear-gradient(180deg, rgba(6,20,17,.98), rgba(3,12,12,.98))" }}>
          <div style={{ fontSize: 34, marginBottom: 8 }} aria-hidden="true">⚠️</div>
          <h1 style={{ fontSize: 20, margin: "0 0 8px" }}>No pudimos cargar EcoNexo</h1>
          <p style={{ margin: "0 0 16px", color: "#a9c4bc", fontSize: 14, lineHeight: 1.5 }}>
            Ocurrió un error inesperado. Volvé a intentar; si persiste, compartí la referencia con el equipo.
          </p>
          {error.digest && (
            <code style={{ display: "inline-block", marginBottom: 16, padding: "4px 10px", borderRadius: 8, background: "rgba(0,0,0,.3)", color: "#8ff06a", fontSize: 12 }}>
              Ref: {error.digest}
            </code>
          )}
          <div>
            <button
              type="button"
              onClick={() => reset()}
              style={{ cursor: "pointer", padding: "11px 20px", borderRadius: 12, border: "none", fontWeight: 700, color: "#06140d", background: "linear-gradient(135deg,#8ff06a,#50c978)" }}
            >
              Reintentar
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
