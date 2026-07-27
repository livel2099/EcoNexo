# Sistema de marca EcoNexo

Versión: **2026-07-25**

## Identidad principal

La identidad oficial suministrada combina:

- globo territorial con tramas digitales;
- líneas de tendencia y nodos de información;
- ondas ambientales y lectura hídrica;
- órbitas de observación;
- palabra **ECONEXO** con acento violeta en la “X”;
- descriptor “Análisis predictivo · Decisiones en tiempo real”.

El archivo maestro entregado se conserva sin modificaciones en:

```text
docs/brand/EcoNexo_logo_oficial.png
```

## Implementación digital

| Recurso | Ubicación | Uso |
|---|---|---|
| Original oficial | `docs/brand/EcoNexo_logo_oficial.png` | archivo maestro y referencia |
| Lockup horizontal optimizado | `apps/web/public/brand/econexo-lockup.jpg` | acceso, centro de comando, módulos e informes |
| Símbolo optimizado | `apps/web/public/brand/econexo-symbol.png` | iconografía y superficies compactas |
| Componente tecnológico animado | `apps/web/components/TechLogo.tsx` | recurso secundario de movimiento y construcción digital |
| Fondo de circuitos | `apps/web/components/CircuitBackdrop.tsx` | ambientación del centro de comando |
| Icono web | `apps/web/public/icon.svg` | metadatos del sitio |
| Activos móviles | `apps/mobile/assets/` | icono, splash, adaptive icon y lockup |

## Sistema tecnológico secundario

`TechLogo.tsx` no reemplaza la identidad oficial. Se utiliza como lenguaje de movimiento complementario:

- trazas de circuito que se dibujan por etapas;
- nodos periféricos que pulsan;
- paquetes de datos en movimiento;
- núcleo geométrico como motor analítico;
- órbitas de observación territorial y satelital.

Las animaciones respetan `prefers-reduced-motion` mediante las reglas globales del proyecto.

## Paleta

| Token | Valor | Función |
|---|---|---|
| Verde bio-digital | `#8FF06A` | señal activa y éxito |
| Cian telemetría | `#33DAFF` | datos, red y atmósfera |
| Violeta IA | `#A78BFF` | inferencia y acento de marca |
| Naranja alerta | `#FF9F45` | fuego y amenaza alta |
| Rojo crítico | `#FF5D52` | incidente crítico |
| Fondo profundo | `#031413` aproximado | centro de comando |

## Reglas de uso

- Utilizar el lockup oficial en autenticación, navegación principal, portadas e informes.
- Mantener proporción y área libre; no deformar ni recolorear el original.
- No usar `image-rendering: pixelated` en ningún activo de marca.
- Usar el símbolo cuando el ancho disponible no admita la palabra completa.
- Mantener el componente animado como recurso secundario, no como sustituto del logo oficial.
- Para documentos impresos, preferir el lockup horizontal de alta legibilidad.
