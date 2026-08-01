# Despliegue de producción - EcoNexo Misiones

## Topología recomendada

- Frontend estático Next.js en Cloudflare Workers/Assets.
- API FastAPI detrás de load balancer, WAF y TLS.
- PostgreSQL 16 + PostGIS administrado, Multi-AZ y PITR.
- S3 privado con cifrado, lifecycle, antivirus y bloqueo público.
- MQTT con identidad y ACL por dispositivo.
- Redis para cuotas, rate limiting y revocación.
- Workers de ingesta, anomalías, notificaciones y FIRMS en red privada.
- Logs, métricas, tracing, uptime y alertas centralizadas.

## Variables

Copiar `.env.production.example` a `.env` en el entorno de despliegue. La API bloquea el arranque productivo cuando detecta secretos de ejemplo, URLs no HTTPS, CORS local, cifrado S3 ausente o proxy confiable abierto.

Variables indispensables:

```env
ENVIRONMENT=production
JWT_SECRET=<64 caracteres aleatorios>
INTERNAL_SERVICE_TOKEN=<otro secreto>
POSTGRES_PASSWORD=<secreto>
PUBLIC_APP_URL=https://app.econexo.com.ar
CORS_ORIGINS=https://app.econexo.com.ar
S3_PUBLIC_ENDPOINT=https://files.econexo.com.ar
S3_SERVER_SIDE_ENCRYPTION=AES256
FORWARDED_ALLOW_IPS=<CIDR del proxy>
NASA_FIRMS_KEY=<MAP_KEY>
ALLOW_DEMO_SATELLITE_FIXTURES=false
```

## Orden de despliegue

1. Crear ambientes separados, DNS, TLS, WAF y secretos.
2. Crear PostgreSQL/PostGIS y usuario de mínimo privilegio.
3. Ejecutar migraciones `01` a `09` como job único.
4. Desplegar API y confirmar `/health` y `/ready`.
5. Autenticarse como administrador y ejecutar `POST /territory/sync-georef`.
6. Confirmar `official: true` en `/territory/boundary-status`.
7. Ejecutar `SELECT * FROM misiones_external_data_audit`; todos los conteos deben ser cero.
8. Configurar S3, MQTT, FIRMS, WMS, Google y canales de notificación.
9. Construir el frontend con URLs públicas y desplegar Cloudflare.
10. Ejecutar smoke, E2E, carga, seguridad, backup/restore y rollback.
11. Ejecutar `scripts/preflight-launch.ps1` y firmar el acta de aceptación.

## Cloudflare productivo

```powershell
cd apps\web
Copy-Item .env.production.example .env.production.local
notepad .env.production.local
..\..\scripts\deploy-cloudflare-production.ps1
```

Cloudflare aloja el frontend; la API y PostgreSQL deben tener infraestructura pública separada. `localhost` nunca es válido para visitantes externos.

## Pre-flight

```powershell
.\scripts\preflight-launch.ps1 `
  -ApiUrl https://api.econexo.com.ar `
  -AppUrl https://app.econexo.com.ar
```

En un host con Docker y la base local disponible:

```powershell
.\scripts\preflight-launch.ps1 `
  -ApiUrl https://api.econexo.com.ar `
  -AppUrl https://app.econexo.com.ar `
  -CheckDockerDatabase
```

## Operación territorial

- Sincronizar GeoRef periódicamente y conservar fuente/fecha.
- No publicar detecciones fuera de Misiones.
- No sustituir fallas FIRMS con fixtures en producción.
- Un foco térmico es una señal; la confirmación exige evidencia adicional.
- Ante fuego o humo visible, el canal mostrado es 911.
- Mantener aprobación humana para comunicaciones R3-R5.

## Rollback y continuidad

Cada release debe tener imagen inmutable, migración identificada, plan de rollback, backup previo y prueba de restauración. No ejecutar migraciones destructivas al iniciar cada réplica. La recuperación debe incluir base, objetos S3, secretos, DNS y configuración de fuentes.
