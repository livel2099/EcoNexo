# EcoNexo rc.6 en Render

Esta edición despliega tres componentes:

```text
Supabase PostgreSQL/PostGIS -> Base EcoNexo
API FastAPI         -> EcoNexo / econexo.onrender.com
Frontend estático   -> econexo-web.onrender.com
```

Los Blueprints despliegan API y frontend en Render. `DATABASE_URL` queda como secreto manual de Render y apunta a Supabase; ya no se vincula una base de Render.

## 1. API existente

### Conectar Supabase

1. Crear el proyecto de Supabase y conservar su contraseña únicamente en un gestor de secretos.
2. En **Connect**, copiar el URI de **Session pooler** (puerto `5432`), no el Transaction pooler (`6543`). Agregar `?sslmode=require` si no viene incluido.
3. En Render > EcoNexo API > Environment, eliminar el `DATABASE_URL` heredado de la base suspendida y cargar la URL de Supabase como secreto. Nunca exponerla con prefijo `NEXT_PUBLIC_`.
4. Verificar que PostGIS esté habilitado/disponible en Supabase. La primera migración de EcoNexo ejecuta `CREATE EXTENSION IF NOT EXISTS postgis`.
5. Dejar `DB_SEARCH_PATH=public,extensions`. Cuando PostGIS se habilita desde el panel de Supabase queda instalado en el esquema `extensions`, no en `public`: ahí `CREATE EXTENSION IF NOT EXISTS` no hace nada, pero `uuid_generate_v4()` y las funciones `ST_*` tampoco resuelven. `python -m app.migrate` detecta ese caso antes de aplicar nada y aborta con el nombre del esquema en el mensaje.
6. Mantener `DB_STATEMENT_CACHE_SIZE=100`. Ponerlo en `0` **solo** si se usa el Transaction pooler (`:6543`), que no soporta prepared statements y responde `prepared statement "__asyncpg_stmt_x__" already exists`.

Para una conexión directa exclusiva de DDL se puede definir `MIGRATIONS_DATABASE_URL`; si se deja vacía, `python -m app.migrate` usa `DATABASE_URL` (Session pooler).

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
DATABASE_URL=SUPABASE_SESSION_POOLER_URL_CON_SSLMODE_REQUIRE
DB_SEARCH_PATH=public,extensions
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
Si el log muestra `socket.gaierror: Name or service not known`, la API conserva una URL de Render suspendida o un host incompleto. Reemplazá el secreto por la URL de Session pooler de Supabase y redesplegá; no es un problema de CORS.

Si el arranque aborta con `Configuracion incompleta o insegura: DATABASE_URL_ENCODING`, la contraseña tiene caracteres reservados sin codificar. `urlparse` interpreta un `[` como apertura de host IPv6 y falla con un `ValueError` que habla de direcciones IP, no de la contraseña; **asyncpg usa el mismo parser, así que la conexión tampoco abriría**. Codificar en la contraseña: `[`→`%5B`, `]`→`%5D`, `@`→`%40`, `/`→`%2F`, `?`→`%3F`, `#`→`%23`, `:`→`%3A`.

Si el error es `socket.gaierror` o `Network is unreachable` contra un host `db.<ref>.supabase.co`, esa es la **conexión directa**, que en Supabase resuelve solo por IPv6. Render no tiene salida IPv6: hay que usar el host del Session pooler (`aws-<n>-<region>.pooler.supabase.com`, usuario `postgres.<ref>`).

Si el arranque aborta con `Configuracion incompleta o insegura: DATABASE_URL_SSLMODE`, la URL no lleva `sslmode` o lleva uno que acepta texto plano (`disable`, `allow`, `prefer`). El tráfico a Supabase sale a internet: usar `sslmode=require` como mínimo.

Si `python -m app.migrate` aborta con `Extensiones fuera del search_path`, corregir `DB_SEARCH_PATH` con los esquemas que indica el mensaje. `python -m app.migrate --status` sigue funcionando en ese estado para inspeccionar qué migraciones faltan.
