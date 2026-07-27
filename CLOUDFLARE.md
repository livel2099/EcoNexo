# Demo de EcoNexo en Cloudflare

Esta variante publica la experiencia web autónoma y no necesita PostgreSQL, MQTT, Redis, MinIO ni los microservicios. Next.js genera HTML estático, los datos operativos de demo se guardan en `localStorage` y las fuentes ambientales se consultan desde el navegador.

## Qué incluye

- Login demo precargado.
- Dashboard con KPIs, alertas y feed simulado.
- Meteorología actual y pronóstico de 12 horas mediante Open‑Meteo.
- Calidad del aire y aerosoles del modelo Copernicus CAMS mediante Open‑Meteo.
- Mapa Leaflet orientado a Misiones con bases CARTO/OpenStreetMap. Las capas Sentinel‑2 —color natural, NDVI, humedad y NBR— solo se habilitan cuando se configura un WMS propio de Copernicus.
- Dispositivos con series temporales.
- Alta, pausa y eliminación de reglas.
- Moderación y carga de reportes ciudadanos.
- Persistencia por navegador y caché ambiental de 10 minutos.
- Cabeceras de seguridad y caché largo para los assets versionados.

Credenciales:

```text
admin@misiones.econexo.ar
econexo123
```

## Probar localmente

Desde la raíz del repositorio:

```bash
cd apps/web
npm ci
npm run dev:demo
```

Abrir `http://localhost:3000`.

Para probar el artefacto exactamente como lo servirá Cloudflare:

```bash
npm run preview:cloudflare
```

Abrir `http://localhost:8787`.

## Validar antes de publicar

```bash
npm audit
npm run check:cloudflare
```

La salida estática queda en `apps/web/out`. No se versiona porque se regenera en cada build.

## Desplegar con Wrangler

La primera vez:

```bash
cd apps/web
npx wrangler login
npm run deploy:cloudflare
```

Wrangler usa `wrangler.jsonc` y publica el Worker `econexo-demo` con Static Assets. El comando muestra la URL `*.workers.dev` al terminar. Para cambiar el nombre, editar el campo `name` de `wrangler.jsonc`.

El despliegue no necesita secretos: `NEXT_PUBLIC_DEMO_MODE=true` se activa en el script de build y las URL públicas ya tienen valores seguros por defecto. Si se usa una configuración propia de Sentinel Hub, se puede definir durante el build:

```text
NEXT_PUBLIC_COPERNICUS_WMS_URL=https://sh.dataspace.copernicus.eu/ogc/wms/ID_DE_INSTANCIA
NEXT_PUBLIC_OPEN_METEO_FORECAST_URL=https://api.open-meteo.com/v1/forecast
NEXT_PUBLIC_OPEN_METEO_AIR_URL=https://air-quality-api.open-meteo.com/v1/air-quality
```

No agregar un client secret de Copernicus al frontend. La demo no incorpora credenciales ni UUIDs WMS de terceros. Sin `NEXT_PUBLIC_COPERNICUS_WMS_URL`, el mapa base continúa funcionando y la capa satelital queda identificada como no disponible.

## Despliegue conectado a Git

En Cloudflare, crear un Worker conectado al repositorio y usar:

| Opción | Valor |
|---|---|
| Root directory | `apps/web` |
| Build command | `npm ci && npm run build:cloudflare` |
| Deploy command | `npx wrangler deploy` |

No agregar `NEXT_PUBLIC_API_URL` ni `NEXT_PUBLIC_WS_URL` para esta demo.

## Fuentes y atribución

- Open‑Meteo Forecast API: contexto meteorológico y suelo.
- Open‑Meteo Air Quality API: datos del modelo Copernicus Atmosphere Monitoring Service (CAMS).
- Copernicus Data Space Ecosystem / Sentinel Hub / ESA: mosaicos Sentinel‑2 por WMS.
- OpenStreetMap y CARTO: cartografía base.

La atribución queda visible tanto en la franja de datos como en el control del mapa. Las capas de Sentinel‑2 se solicitan desde zoom 9 para respetar la resolución operativa del servicio. La metodología completa está en `docs/DATA_SOURCES.md`.

## Frontend oficial conectado a la API

Para publicar el frontend real, completar `apps/web/.env.production.local` y usar la configuración separada `wrangler.production.jsonc`:

```bash
npm run deploy:cloudflare:production:dry-run
npm run deploy:cloudflare:production
```

El Worker productivo se denomina `econexo-misiones`. Requiere una API HTTPS pública, PostgreSQL/PostGIS, credenciales reales y la puerta de lanzamiento detallada en `docs/DEPLOY_CLOUDFLARE_PRODUCTION.md` y `docs/OFFICIAL_LAUNCH_MISIONES.md`.

## Dominio propio

Después del primer deploy, abrir **Workers & Pages > econexo-demo > Settings > Domains & Routes** y agregar un Custom Domain. Cloudflare gestiona el DNS y el certificado TLS.

## Reiniciar los datos de demo

En la consola del navegador:

```js
localStorage.removeItem("econexo_cloudflare_demo_v2");
localStorage.removeItem("econexo_session");
Object.keys(localStorage).filter((key) => key.startsWith("econexo_earth_intel_v1")).forEach((key) => localStorage.removeItem(key));
location.reload();
```

## Alcance

Esta demo es intencionalmente client-only: cada visitante ve y modifica su propio conjunto de datos. Open‑Meteo y CAMS aportan contexto ambiental; no sustituyen una detección satelital de incendios ni validan por sí solos una alerta. La arquitectura completa y multiusuario continúa disponible mediante Docker Compose según el README principal.

Referencias: [Workers Static Assets](https://developers.cloudflare.com/workers/static-assets/), [Wrangler](https://developers.cloudflare.com/workers/wrangler/), [Open‑Meteo](https://open-meteo.com/en/docs), [Open‑Meteo Air Quality](https://open-meteo.com/en/docs/air-quality-api) y [Copernicus Data Space OGC](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/OGC.html).

## Solución de errores frecuentes

### `Failed to collect page data for /robots.txt`

Las rutas `app/robots.ts` y `app/sitemap.ts` deben exportar:

```ts
export const dynamic = "force-static";
```

Esto permite que Next.js 15 las genere durante `output: "export"`. La corrección ya está incluida en esta entrega.

### Advertencia por múltiples `package-lock.json`

La configuración fija `outputFileTracingRoot` en `apps/web`. Aun así, conviene conservar un único lockfile por proyecto: si se trabaja exclusivamente dentro de `apps/web`, eliminar el `package-lock.json` superior que no se utilice y ejecutar `npm ci` nuevamente.
