# EcoNexo — corrección y validación para Render

Fecha de validación: 31/07/2026  
Versión revisada: `1.0.0-rc.6.2`

## Resultado

El error original quedó corregido. La pantalla `app/cambiar-contrasena/page.tsx` ahora importa una función que existe y cuyo contrato está implementado de extremo a extremo:

- Frontend: `apps/web/app/lib/api.ts` exporta `changePassword(...)`.
- Backend: `POST /auth/change-password` en `apps/api/app/routers/auth.py`.
- Esquema: `PasswordChangeIn` en `apps/api/app/schemas.py`.
- La operación valida la contraseña actual, guarda el nuevo hash, elimina `must_change_password`, genera auditoría y notificación.

La causa real no era solamente esa importación: el código fuente del ZIP mezclaba una revisión antigua del frontend con componentes, tipos, rutas y migraciones de una revisión más nueva. Se restauraron los contratos coherentes de la versión `rc.6.2` sin eliminar el aviso de cookies agregado posteriormente.

## Otras correcciones aplicadas

- Recuperación de tipos y funciones usados por administración, dispositivos, telemetría, autenticación y estado de sesión.
- Restauración de los esquemas y rutas FastAPI correspondientes.
- Sincronización byte a byte de las migraciones de `apps/api/migrations` e `infra/db/migrations`.
- Corrección de la migración 15 para que `copernicus_enabled` tenga `DEFAULT true` y para evitar ejecuciones simultáneas duplicadas del pipeline.
- Incorporación de `decode_geojson_geometry` requerida por los contratos territoriales.
- Alineación de `package.json` y `package-lock.json` en `1.0.0-rc.6.2`.
- Fijación de Node.js `22.16.0` mediante:
  - `apps/web/.node-version`
  - `engines.node` en `package.json`
  - `NODE_VERSION` en `render.yaml` y `render.production.yaml`
- Conservación del componente `CookieConsent` y su integración en el layout.

## Validaciones ejecutadas

- TypeScript: `npm run typecheck` — aprobado.
- Lockfile: `npm ci --ignore-scripts --dry-run --offline` — aprobado; incluye SWC para Linux que Render instalará con `npm ci`.
- Python: compilación de módulos — aprobada.
- API: 70 pruebas — aprobadas.
- FastAPI: 98 objetos de ruta, 82 rutas únicas y rutas críticas presentes.
- JSON y YAML: `package*.json`, `render.yaml` y `render.production.yaml` — válidos.
- Migraciones: 16 archivos sincronizados — aprobado.
- Higiene: sin `.env` productivos ni claves privadas dentro del paquete.
- Configuración simulada de producción Render — aprobada.
- Resultado estructurado: `VALIDATION_RENDER_FIX.json`.

## Límite de la validación local

El build completo de Next.js no pudo terminar dentro de este contenedor porque el ZIP original traía un `node_modules` de Windows y aquí no existe el binario opcional `@next/swc-linux-x64-gnu`. No es un error del código corregido: el lockfile sí contiene SWC para Linux y la simulación de `npm ci` lo selecciona correctamente. Render ejecutará el build desde dependencias limpias con:

```bash
npm ci && npm run typecheck && npm run build:cloudflare:production
```

No se debe subir `node_modules` al repositorio.

## Despliegue recomendado

### Beta o prueba

Usar `render.yaml`. Crea PostgreSQL, API Docker y frontend estático en planes gratuitos.

### Producción persistente

Usar `render.production.yaml`. Incluye base PostgreSQL paga, almacenamiento ampliable, API `starter`, migraciones en `preDeployCommand` y despliegue después de los checks.

### Variables manuales

Render pedirá o permitirá completar las variables declaradas con `sync: false`:

- `COPERNICUS_CLIENT_ID` y `COPERNICUS_CLIENT_SECRET`: cargar ambas o dejar ambas vacías.
- `NASA_FIRMS_KEY`: necesaria para focos FIRMS reales.
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_IDS` y `NEXT_PUBLIC_GOOGLE_CLIENT_ID`: necesarias solamente para login con Google.
- Credenciales WMS/instancia Copernicus: opcionales según el modo usado.

Para crear o restablecer el administrador general en una base nueva, seguir el procedimiento de `RENDER_DEPLOY.md`: activar temporalmente el bootstrap, ingresar, cambiar la contraseña y volver a desactivarlo.

## Verificación después del deploy

1. Comprobar `https://econexo.onrender.com/health`.
2. Revisar `https://econexo.onrender.com/docs`.
3. Abrir el frontend y probar login.
4. Probar el cambio obligatorio de contraseña.
5. Verificar CORS y WebSocket desde el dominio del frontend.
6. Ejecutar las migraciones y luego una corrida controlada del pipeline.
7. Si se modificó cualquier variable `NEXT_PUBLIC_*`, ejecutar **Clear build cache & deploy** en el sitio estático.

> Advertencia: la base PostgreSQL gratuita de Render es temporal. Para conservar datos reales, usar el blueprint de producción o actualizar el plan antes del vencimiento.
