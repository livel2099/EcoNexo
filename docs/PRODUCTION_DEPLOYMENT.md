# Despliegue de producción — EcoNexo Misiones

## Topología recomendada

- Frontend Next.js estático en Cloudflare Workers/Assets.
- API FastAPI en Render Web Service.
- Supabase PostgreSQL 16 con PostGIS (conexión TLS desde Render).
- S3 o Cloudflare R2 privado para evidencias.
- Broker MQTT administrado con TLS para dispositivos.
- Servicios de anomalías, notificaciones e ingesta como servicios privados/workers cuando se habiliten.

La guía operativa específica está en [`RENDER_DEPLOY.md`](../RENDER_DEPLOY.md).

## Despliegue mínimo funcional

El core puede publicarse con PostgreSQL aunque todavía no estén configurados MQTT, S3 o el servicio de anomalías:

```env
MQTT_ENABLED=false
ANOMALY_ENABLED=false
S3_ENABLED=false
```

Las funciones que no dependen de esos adaptadores —autenticación, organizaciones, suscripciones, usuarios, mapas, reglas, informes y administración— continúan disponibles. La carga de fotografías responde 503 hasta habilitar almacenamiento.

## Migraciones

Con Supabase, cargar `DATABASE_URL` en Render con el URI de **Session pooler** (puerto `5432`) y `sslmode=require`. `MIGRATIONS_DATABASE_URL` es opcional para una conexión directa de DDL; sin ella, las migraciones usan `DATABASE_URL`.

El arranque valida el `sslmode` en producción: sin él, o con `disable`/`allow`/`prefer`, `python -m app.check_config` aborta con `DATABASE_URL_SSLMODE`.

`DB_SEARCH_PATH=public,extensions` es obligatorio en Supabase: PostGIS, `uuid-ossp` y `pgcrypto` se instalan en el esquema `extensions`, y el esquema de EcoNexo las invoca sin calificar. Las migraciones verifican esa visibilidad antes de aplicar nada y abortan con un mensaje que nombra el esquema, en vez de morir con un `function does not exist` a mitad de la 01.

Para usar el Transaction pooler (`6543`) hay que poner además `DB_STATEMENT_CACHE_SIZE=0`: `asyncpg` cachea prepared statements y ese pooler no los soporta. El Session pooler no lo necesita.

En un servicio pago, configurar el Pre-Deploy Command:

```bash
python -m app.migrate
```

En una instancia gratuita, Render no ofrece Pre-Deploy Command. En ese caso usar:

```env
RUN_MIGRATIONS_ON_START=true
```

El script de arranque valida el entorno, ejecuta las migraciones y recién después inicia Uvicorn. El ejecutor usa `schema_migrations`, checksum SHA-256 y advisory lock. En una base preexistente sin historial, se detiene para impedir que `01_schema.sql` se ejecute sobre objetos ya creados.

## Health y readiness

- `/health`: liveness del proceso; usar como Health Check de Render.
- `/ready`: valida PostgreSQL, PostGIS, controles territoriales y límite oficial de Misiones.

No usar `/ready` como health check inicial: puede responder 503 hasta sincronizar GeoRef y limpiar la auditoría territorial.

## Orden de lanzamiento

1. Crear el proyecto Supabase y confirmar que PostGIS está disponible.
2. Cargar en Render el secreto `DATABASE_URL` con el Session pooler TLS de Supabase; eliminar el valor heredado de Render Postgres.
3. Configurar las demás variables con `.env.render.example` o Blueprint.
4. Aplicar migraciones mediante Pre-Deploy en plan pago o al iniciar en plan gratuito.
5. Confirmar `/health` y `/docs`.
6. Sincronizar el límite oficial GeoRef desde Admin Core.
7. Confirmar `/ready`.
8. Desplegar el frontend Cloudflare con la URL pública de Render.
9. Configurar S3/R2, Google, FIRMS y MQTT según el alcance contratado.
10. Ejecutar pruebas de registro, login, licencias, reportes y alertas.
11. Configurar backups, monitoreo y rollback antes del lanzamiento oficial.
