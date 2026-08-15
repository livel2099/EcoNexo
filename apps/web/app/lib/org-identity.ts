/**
 * Identidad visual de la organización.
 *
 * `organizations.primary_color` lo elige un admin de la organización y termina
 * inyectado como custom property de CSS. La API ya valida el formato
 * (`OrgUpdateIn.primary_color`, patrón `^#[0-9A-Fa-f]{6}$`), pero el valor
 * también puede venir de filas viejas, del seed o de una edición directa en la
 * base, así que acá se vuelve a validar antes de escribirlo en el DOM: una
 * custom property no sanitizada es un vector de inyección de CSS.
 *
 * Del color elegido se derivan dos valores más, porque un color de marca suelto
 * no alcanza sobre una interfaz oscura:
 *
 * - `--org-ink`  → el texto que va *encima* del color (relleno de botones y
 *   chips). Se elige por luminancia, no a ojo: un municipio con azul marino
 *   necesita texto claro, uno con verde lima necesita texto oscuro.
 * - `--org-tint` → el color usado *como* texto sobre los paneles oscuros. Si la
 *   marca es muy oscura se aclara hasta que se lea; el color crudo quedaría
 *   invisible sobre `--bg`.
 */
import type { CSSProperties } from "react";

/** Verde institucional de EcoNexo: se usa cuando la organización no definió color. */
export const DEFAULT_ORG_COLOR = "#8ff06a";

const HEX6 = /^#[0-9A-Fa-f]{6}$/;

/** Devuelve el color sólo si es un hexadecimal de 6 dígitos; si no, el default. */
export function orgColor(value: string | null | undefined): string {
  return typeof value === "string" && HEX6.test(value) ? value : DEFAULT_ORG_COLOR;
}

function channels(hex: string): [number, number, number] {
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ];
}

function toHex(rgb: [number, number, number]): string {
  return `#${rgb.map((channel) => Math.round(Math.min(255, Math.max(0, channel))).toString(16).padStart(2, "0")).join("")}`;
}

/** Luminancia relativa WCAG 2.x (0 = negro, 1 = blanco). */
function luminance(hex: string): number {
  const [r, g, b] = channels(hex).map((channel) => {
    const srgb = channel / 255;
    return srgb <= 0.03928 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Texto legible sobre un relleno del color de la organización. */
function ink(hex: string): string {
  // 0.42 está calibrado contra la paleta real: por encima de ese punto el texto
  // oscuro gana contraste, por debajo lo gana el claro.
  return luminance(hex) > 0.42 ? "#03120a" : "#f2fbf6";
}

/** Variante legible del color de la organización usada como texto sobre `--bg`. */
function tint(hex: string): string {
  let current = channels(hex);
  let hexValue = hex;
  // Aclarar hacia el blanco hasta despegarse del fondo. El tope de iteraciones
  // evita cualquier posibilidad de bucle largo con colores casi negros.
  for (let step = 0; step < 12 && luminance(hexValue) < 0.22; step += 1) {
    current = [
      current[0] + (255 - current[0]) * 0.18,
      current[1] + (255 - current[1]) * 0.18,
      current[2] + (255 - current[2]) * 0.18,
    ];
    hexValue = toHex(current);
  }
  return hexValue;
}

/**
 * Custom properties para aplicar la identidad a un subárbol del DOM.
 * Se pasa como `style` al contenedor: todo lo que esté adentro y use
 * `var(--org-color)` queda teñido sin más trabajo.
 */
export function orgIdentityStyle(value: string | null | undefined): CSSProperties {
  const color = orgColor(value);
  return {
    "--org-color": color,
    "--org-ink": ink(color),
    "--org-tint": tint(color),
  } as CSSProperties;
}
