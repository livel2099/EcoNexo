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

## Revisión de integraciones y nueva navegación (19/10/2026)

El inicio del espacio de trabajo agrupa las tareas del campo y el seguimiento. La configuración de la organización está en Más herramientas → Configuración; el diagnóstico global continúa reservado al administrador de plataforma. Paraguay organiza ubicación, clima, evaluación, satélite e informes en cinco pasos y permite dibujar el contorno del lote.

`render.yaml` deja MQTT_ENABLED, ANOMALY_ENABLED y S3_ENABLED en false. Es una configuración explícita: cambiar los indicadores visuales no conecta esos servicios.

- MQTT: requiere un broker accesible y una lectura de un sensor real. Revisar host, puerto y las medidas de autenticación y transporte del broker antes de habilitarlo. Un nodo sin datos recientes también puede estar desconectado o tener un reloj incorrecto; no demuestra que falte configurar MQTT.
- Anomalías: requiere desplegar el servicio y revisar ANOMALY_SERVICE_URL. Habilitarlo no acredita entrenamiento ni precisión; la validación predictiva sigue pendiente hasta reunir y contrastar evidencia.
- S3: requiere bucket, endpoint, región, credenciales, cifrado y acceso autorizado. No es requisito para exportar el informe HTML de soja.
- FIRMS y Copernicus: la presencia de configuración no prueba conectividad, cuota ni permisos por organización. Comprobar una consulta real y la fecha/cobertura de sus resultados.

El diagnóstico devuelve `configured_unverified` o `disabled_or_missing`, `verified=false` y pasos de revisión sin exponer valores de credenciales. La revisión del repositorio no acredita el estado del despliegue remoto. Para cerrar cada pendiente, configurar el servicio real y comprobar su operación desde ese entorno.


## Incidente: soja sin contexto y predicciones sin fuente (19/10/2026)

En producción se comprobó que la web consultaba `/paraguay/soja/context` mientras la API fijada a un commit anterior devolvía 404. La API tenía desactivado Auto-Deploy por haberse publicado un commit específico: publicar la web no actualiza ese servicio. Desplegar manualmente la misma revisión de API y web y verificar la ruta en `/openapi.json`.

Los registros de la API mostraron Open-Meteo HTTP 429 con límite diario agotado. Predicciones usa ahora MET Norway Locationforecast como respaldo para incendio, lluvia y calor si MET_NO_FALLBACK_ENABLED está habilitado y MET_NO_USER_AGENT contiene la identificación y el contacto autorizados. Comparte el caché de la telemetría y deduplica coordenadas. La atribución y el proveedor se guardan en cada emisión. Los modelos entrenados no se aplican al otro proveedor sin validación; se conserva el índice heurístico con su fuente. PM2.5 sigue requiriendo su fuente de calidad del aire. Si faltan horas no se interpolan: un horizonte de 72 h puede no estar disponible en el respaldo, aunque 6/24 h sí.

Soja consulta ese mismo respaldo si falla Open-Meteo. Presenta siete días completos en UTC desde mañana, agregando cuatro bloques de seis horas sin repartir lluvia entre intervalos. MET Norway no entrega ET0 ni variables del suelo: quedan ausentes y no se calcula balance hídrico. El informe identifica fuente, zona horaria y limitaciones. Esta cobertura parcial no se presenta como evaluación agronómica completa.

La autorización para enviar coordenadas de nodos y lotes y el contacto comercial a api.met.no fue otorgada por el usuario durante la reparación. La interfaz de habilitación identifica ambos proveedores. Verificar primero el endpoint público y después una consulta autenticada real de cada módulo; `/health` por sí solo no comprueba estos contratos.
