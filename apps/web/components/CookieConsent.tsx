"use client";

import { useEffect, useState } from "react";

/**
 * Banner de consentimiento de cookies (Ley 25.326 / buenas practicas GDPR).
 *
 * EcoNexo solo usa almacenamiento estrictamente necesario (sesion, mapas,
 * Google Identity). Este panel informa, registra la eleccion del usuario en
 * ``localStorage`` y no carga tecnologias opcionales hasta que se acepten.
 */
const STORAGE_KEY = "econexo-cookie-consent";

type Consent = "accepted" | "essential";

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (!window.localStorage.getItem(STORAGE_KEY)) setVisible(true);
    } catch {
      // Si el navegador bloquea storage, mostramos el aviso igualmente.
      setVisible(true);
    }
  }, []);

  function decide(choice: Consent) {
    try {
      window.localStorage.setItem(STORAGE_KEY, choice);
      window.localStorage.setItem(`${STORAGE_KEY}-at`, new Date().toISOString());
    } catch {
      /* almacenamiento no disponible: la eleccion vale solo para esta sesion */
    }
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="cookie-consent" role="dialog" aria-live="polite" aria-label="Aviso de cookies">
      <div className="cookie-consent__text">
        <strong>Cookies y almacenamiento</strong>
        <p>
          Usamos almacenamiento estrictamente necesario para el inicio de sesión, los mapas y el
          reporte ciudadano. Las tecnologías opcionales solo se activan si las aceptás. Más
          detalle en la <a href="/cookies">política de cookies</a>.
        </p>
      </div>
      <div className="cookie-consent__actions">
        <button type="button" className="cookie-consent__btn cookie-consent__btn--ghost" onClick={() => decide("essential")}>
          Solo esenciales
        </button>
        <button type="button" className="cookie-consent__btn cookie-consent__btn--primary" onClick={() => decide("accepted")}>
          Aceptar todo
        </button>
      </div>
    </div>
  );
}
