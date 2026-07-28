# Despliegue de producción — EcoNexo Misiones

## Topología recomendada

- Frontend Next.js estático en Cloudflare Workers/Assets.
- API FastAPI en Render Web Service.
- Render Postgres 16 con PostGIS.
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

1. Crear Render Postgres y API en la misma región.
2. Configurar variables con `.env.render.example` o Blueprint.
3. Aplicar migraciones mediante Pre-Deploy en plan pago o al iniciar en plan gratuito.
4. Confirmar `/health` y `/docs`.
5. Sincronizar el límite oficial GeoRef desde Admin Core.
6. Confirmar `/ready`.
7. Desplegar el frontend Cloudflare con la URL pública de Render.
8. Configurar S3/R2, Google, FIRMS y MQTT según el alcance contratado.
9. Ejecutar pruebas de registro, login, licencias, reportes y alertas.
10. Configurar backups, monitoreo y rollback antes del lanzamiento oficial.
