# EcoNexo rc.6 en Render

Esta edición despliega tres componentes:

```text
PostgreSQL/PostGIS  -> econexo-db
API FastAPI         -> EcoNexo / econexo.onrender.com
Frontend estático   -> econexo-web.onrender.com
```

Los archivos `render.yaml` y `render.production.yaml` también permiten crear la arquitectura completa mediante Blueprint.

## 1. API existente

En el Web Service de la API:

```text
Runtime: Docker
Branch: main
Root Directory: apps/api
Dockerfile Path: Dockerfile
Docker Build Context: .
Docker Command: vacío
Health Check Path: /health
```

En el plan gratuito:

```env
RUN_MIGRATIONS_ON_START=true
```

En un plan pago con Pre-Deploy Command:

```text
Pre-Deploy Command: python -m app.migrate
```

```env
RUN_MIGRATIONS_ON_START=false
```

Importar `.env.render.example` y completar como mínimo:

```env
DATABASE_URL=INTERNAL_DATABASE_URL_DE_RENDER
JWT_SECRET=SECRETO_ALEATORIO_1
INTERNAL_SERVICE_TOKEN=SECRETO_ALEATORIO_2
PUBLIC_APP_URL=https://econexo-web.onrender.com
CORS_ORIGINS=https://econexo-web.onrender.com
PLATFORM_ADMIN_EMAILS=econexoargentina@gmail.com
SALES_EMAIL=econexoargentina@gmail.com
```

Para obtener focos reales dentro del pipeline integrado:

```env
NASA_FIRMS_KEY=MAP_KEY_DE_NASA_FIRMS
FIRMS_INLINE_ENABLED=true
FIRMS_SOURCE=VIIRS_SNPP_NRT
```

Sin `NASA_FIRMS_KEY`, producción no inventa focos. El resto del pipeline y los nodos Open-Meteo siguen funcionando.

## 2. Administrador general

Solo durante el primer alta o restablecimiento:

```env
PLATFORM_ADMIN_BOOTSTRAP_ENABLED=true
PLATFORM_ADMIN_INITIAL_PASSWORD=CONTRASENA_TEMPORAL_SEGURA
PLATFORM_ADMIN_FORCE_PASSWORD_CHANGE=true
PLATFORM_ADMIN_RESET_INITIAL_PASSWORD=true
```

Ingresar con `econexoargentina@gmail.com`, cambiar la clave y luego dejar:

```env
PLATFORM_ADMIN_BOOTSTRAP_ENABLED=false
PLATFORM_ADMIN_INITIAL_PASSWORD=
PLATFORM_ADMIN_RESET_INITIAL_PASSWORD=false
```

La consola privada se abre manualmente en:

```text
https://econexo-web.onrender.com/plataforma/
```

## 3. Frontend estático

En el Static Site:

```text
Branch: main
Root Directory: apps/web
Build Command: npm ci && npm run typecheck && npm run build:cloudflare:production
Publish Directory: out
Node: 22.16.0 (fijado por NODE_VERSION, .node-version y package.json)
```

Importar `.env.web.render.example`. Para el servicio API actual:

```env
NEXT_PUBLIC_API_URL=https://econexo.onrender.com
NEXT_PUBLIC_WS_URL=wss://econexo.onrender.com
NEXT_PUBLIC_DEMO_MODE=false
NEXT_PUBLIC_STATIC_EXPORT=true
```

Después de cambiar una variable `NEXT_PUBLIC_*`, usar **Clear build cache & deploy** porque Next.js incorpora esos valores durante el build.

## 4. Orden de despliegue

1. Subir el código a `main`.
2. Desplegar la API primero para aplicar la migración `14_telemetry_pipeline_and_map.sql`.
3. Verificar `https://econexo.onrender.com/health`.
4. Verificar `https://econexo.onrender.com/docs`.
5. Reconstruir `econexo-web` con caché limpia.
6. Ingresar como administrador.
7. Abrir `Admin Core > Telemetría`.
8. Usar **Crear red inicial y ejecutar** o crear nodos manualmente.
9. En Centro de Comando, usar **Ejecutar pipeline**.

## 5. Qué actualiza el pipeline

Cada corrida puede:

- actualizar nodos virtuales Open-Meteo;
- persistir temperatura, humedad, humedad superficial del suelo, precipitación, viento, ráfagas y VPD;
- actualizar estados online/offline;
- consultar NASA FIRMS cuando existe MAP_KEY;
- deduplicar focos;
- correlacionar focos con geocercas de incendio o multiamenaza;
- evaluar reglas no-code;
- crear alertas y fuentes de evidencia;
- refrescar el mapa y el feed por WebSocket.

Los nodos virtuales aparecen como cuadros, triángulos o círculos, según la configuración guardada en Admin Core.

## 6. Capas del mapa

Las opciones Humedad y Área quemada ya no quedan bloqueadas:

- **Humedad:** muestra un proxy operativo basado en lecturas de nodos/Open-Meteo cuando no hay WMS.
- **Área quemada:** muestra halos FIRMS como proxy de focos térmicos; no se presenta como perímetro quemado confirmado.
- **Color natural y NDVI:** permanecen seleccionables, pero requieren una instancia WMS válida para mostrar un mosaico satelital.

Para mosaicos reales, configurar en `Admin Core > Fuentes SpaceAI`:

```text
https://sh.dataspace.copernicus.eu/ogc/wms/INSTANCE_ID
```

Luego probar GetCapabilities y asignar los nombres de capas.

## 7. Diagnóstico rápido

```text
GET https://econexo.onrender.com/health
GET https://econexo.onrender.com/ready
GET https://econexo.onrender.com/docs
```

En el navegador, el request de estado debe apuntar a:

```text
https://econexo.onrender.com/health
```

Si apunta a `localhost`, el frontend fue construido con variables antiguas. Si devuelve CORS, corregir `CORS_ORIGINS` en la API y redesplegarla.
