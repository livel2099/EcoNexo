/**
 * Punto único de reporte de errores de EcoNexo.
 *
 * Hoy deja siempre una traza estructurada en consola (con contexto y
 * timestamp) para poder diagnosticar. Está preparado para Sentry: si el SDK
 * está inicializado (expone `window.Sentry`), el error se reenvía.
 *
 * Para activar Sentry en el futuro:
 *   1) npx @sentry/wizard@latest -i nextjs
 *   2) definir NEXT_PUBLIC_SENTRY_DSN
 * El SDK de Sentry captura automáticamente; este helper solo agrega contexto.
 */

export interface ErrorContext {
  source?: string;
  digest?: string;
  [key: string]: unknown;
}

interface SentryLike {
  captureException?: (error: unknown, hint?: { extra?: Record<string, unknown> }) => void;
}

export function reportError(error: unknown, context: ErrorContext = {}): void {
  const payload = {
    message: error instanceof Error ? error.message : String(error),
    stack: error instanceof Error ? error.stack : undefined,
    at: new Date().toISOString(),
    ...context,
  };

  // Traza local: siempre disponible, incluso sin servicio externo.
  console.error("[EcoNexo] error capturado", payload);

  // Reenvío opcional a Sentry si el SDK ya está inicializado.
  try {
    const sentry = (globalThis as unknown as { Sentry?: SentryLike }).Sentry;
    sentry?.captureException?.(error, { extra: { ...context } });
  } catch {
    /* nunca dejar que el reporte de errores lance otro error */
  }
}
