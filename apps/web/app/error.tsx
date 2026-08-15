"use client";

import { useEffect } from "react";
import { reportError } from "./lib/observability";

/**
 * Límite de error a nivel de ruta. Reemplaza la pantalla en blanco por una
 * vista con marca y una referencia (digest) trazable, y permite reintentar.
 */
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    reportError(error, { source: "route-error", digest: error.digest });
  }, [error]);

  return (
    <main className="error-boundary" role="alert">
      <div className="error-card">
        <span className="error-glyph" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
          </svg>
        </span>
        <h1>Algo no salió como esperábamos</h1>
        <p>Se produjo un error al mostrar esta sección. El equipo puede diagnosticarlo con la referencia de abajo.</p>
        {error.digest && <code className="error-digest">Ref: {error.digest}</code>}
        <div className="error-actions">
          <button type="button" className="primary" onClick={() => reset()}>Reintentar</button>
          <a className="error-link" href="/">Volver al inicio</a>
        </div>
      </div>
    </main>
  );
}
