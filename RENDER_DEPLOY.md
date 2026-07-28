# EcoNexo en Render — guía validada para la API

Este repositorio incluye dos opciones:

- `render.yaml`: beta con Web Service, Render Postgres y worker NASA FIRMS.
- `render.production.yaml`: servicio Starter y Postgres `basic-256mb`.

El frontend continúa en Cloudflare. Render aloja la API FastAPI y PostgreSQL/PostGIS.

> **Importante:** `render.yaml` es solo para beta o validación. El Web Service gratuito entra en reposo por inactividad y la base gratuita expira a los 30 días sin backups. Para lanzamiento oficial usar `render.production.yaml` o planes pagos equivalentes.

## Opción A — Blueprint

1. Subir el repositorio a GitHub.
2. En Render elegir **New > Blueprint**.
3. Seleccionar el repositorio.
4. Usar `render.yaml` para beta o indicar `render.production.yaml` para producción.
5. Confirmar la creación de `econexo-db` y `econexo-api`.

El Blueprint configura:

- Docker con raíz `apps/api`.
- `DATABASE_URL` desde la base administrada.
- secretos JWT generados por Render.
- `econexo-satellite`, worker que consulta NASA FIRMS cada 15 minutos y entrega los focos a la API con el token interno.
- en beta gratuita, migraciones idempotentes al iniciar el servicio (`RUN_MIGRATIONS_ON_START=true`).
- en producción paga, migraciones con `python -m app.migrate` como Pre-Deploy Command.
- health check `/health`.
- MQTT, S3 y servicio de anomalías desactivados hasta configurar proveedores externos.

## Opción B — servicio ya creado manualmente

En **Settings > Build & Deploy**:

```text
Language: Docker
Branch: main
Root Directory: apps/api
Dockerfile Path: Dockerfile
Docker Build Context: .
Pre-Deploy Command: `python -m app.migrate` solo en planes pagos
Health Check Path: /health
```

En **Environment > Add from .env**, pegar `.env.render.example` y reemplazar:

- `DATABASE_URL`: Internal Database URL de Render Postgres.
- `JWT_SECRET`: secreto de 64 caracteres.
- `INTERNAL_SERVICE_TOKEN`: otro secreto diferente.
- `PLATFORM_ADMIN_EMAILS`: email del administrador comercial de EcoNexo; admite varios separados por coma.
- `SALES_EMAIL`: email que recibirá solicitudes comerciales.
- `NASA_FIRMS_KEY`: MAP_KEY real solicitada en NASA FIRMS. En un Blueprint existente debe cargarse manualmente en `econexo-api`; el worker la recibe por referencia.

En un servicio pago con Pre-Deploy Command, usar:

```env
RUN_MIGRATIONS_ON_START=false
```

En el plan gratuito, que no admite Pre-Deploy Command, usar:

```env
RUN_MIGRATIONS_ON_START=true
```

El ejecutor usa advisory lock y checksums, por lo que no vuelve a aplicar migraciones registradas.

## Comprobaciones

```text
https://TU-SERVICIO.onrender.com/health
https://TU-SERVICIO.onrender.com/docs
https://TU-SERVICIO.onrender.com/ready
```

`/health` debe responder 200. `/ready` puede responder 503 hasta sincronizar el límite oficial GeoRef de Misiones y completar la auditoría territorial.

## Frontend Cloudflare

Reconstruir el frontend con:

```powershell
$env:NEXT_PUBLIC_API_URL="https://TU-SERVICIO.onrender.com"
$env:NEXT_PUBLIC_WS_URL="wss://TU-SERVICIO.onrender.com"
cd apps\web
npm ci
npm run deploy:cloudflare:production
```

La API debe contener en Render:

```env
PUBLIC_APP_URL=https://econexo-misiones.econexo-misiones.workers.dev
CORS_ORIGINS=https://econexo-misiones.econexo-misiones.workers.dev
```

No agregar barra final.

## Ingesta NASA FIRMS

El Blueprint crea `econexo-satellite` como Background Worker Starter. Este servicio tiene costo independiente en Render. La variable `NASA_FIRMS_KEY` se carga en `econexo-api`; el worker reutiliza esa variable y `INTERNAL_SERVICE_TOKEN` mediante referencias privadas de Render. Sin MAP_KEY, producción queda deliberadamente sin focos simulados.

Después del deploy, revisar los logs del worker. Una ejecución correcta informa `FIRMS: N focos de calor` y `Ingesta al API`.

## Servicios opcionales

La API core inicia con:

```env
MQTT_ENABLED=false
ANOMALY_ENABLED=false
S3_ENABLED=false
```

Para habilitar fotos, configurar un bucket S3/R2 privado y cambiar `S3_ENABLED=true`. Para telemetría en tiempo real, usar un broker MQTT con TLS y cambiar `MQTT_ENABLED=true`.
