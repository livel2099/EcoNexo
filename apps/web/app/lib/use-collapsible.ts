"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Estado abierto/cerrado de un panel del centro de comando, recordado entre
 * recargas.
 *
 * El valor inicial es siempre `defaultOpen`, no lo guardado: en el primer
 * render el servidor no tiene acceso a `localStorage` y devolver otra cosa
 * produce un desajuste de hidratacion. Lo guardado se aplica en el efecto,
 * ya en el cliente.
 */
const PREFIX = "econexo.panel.";

export function useCollapsible(id: string, defaultOpen = true) {
  const [open, setOpen] = useState(defaultOpen);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(PREFIX + id);
      if (stored === "0" || stored === "1") setOpen(stored === "1");
    } catch {
      /* almacenamiento bloqueado por el navegador: se usa el valor por defecto */
    }
  }, [id]);

  const toggle = useCallback(() => {
    setOpen((previous) => {
      const next = !previous;
      try {
        window.localStorage.setItem(PREFIX + id, next ? "1" : "0");
      } catch {
        /* sin persistencia, pero el panel igual responde */
      }
      return next;
    });
  }, [id]);

  return [open, toggle] as const;
}
