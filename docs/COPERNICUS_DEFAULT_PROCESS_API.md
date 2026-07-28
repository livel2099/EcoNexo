# Copernicus predeterminado en EcoNexo 1.0.0-rc.6.2

## Objetivo

EcoNexo utiliza **Copernicus Data Space Ecosystem (CDSE)** como proveedor satelital predeterminado. La integración recomendada ya no depende de que cada organización cargue manualmente una URL WMS: el backend consume **Sentinel Hub Process API** mediante OAuth2 `client_credentials`, procesa Sentinel-2 L2A y entrega al mapa una imagen PNG autenticada.

WMS se conserva como alternativa por organización para instalaciones que ya cuentan con un `INSTANCE_ID` propio.

## Por qué no existe una credencial universal incluida

Copernicus exige credenciales vinculadas a una cuenta CDSE. Para Process API se debe crear un OAuth client y para OGC/WMS una configuración con `INSTANCE_ID`. EcoNexo no incluye ni comparte credenciales y no expone secretos en el frontend.

## Variables de Render — servicio API

```env
COPERNICUS_ENABLED_BY_DEFAULT=true
COPERNICUS_MODE=process_api

COPERNICUS_CLIENT_ID=PEGAR_CLIENT_ID_DE_CDSE
COPERNICUS_CLIENT_SECRET=PEGAR_CLIENT_SECRET_DE_CDSE

COPERNICUS_TOKEN_URL=https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token
COPERNICUS_PROCESS_URL=https://sh.dataspace.copernicus.eu/process/v1
COPERNICUS_HTTP_TIMEOUT_SECONDS=45
COPERNICUS_TIME_RANGE_DAYS=90
COPERNICUS_MAX_CLOUD_COVERAGE=80
COPERNICUS_MAX_DIMENSION=1024
COPERNICUS_CACHE_SECONDS=600
```

Opcionales para fallback WMS de sistema:

```env
COPERNICUS_INSTANCE_ID=
COPERNICUS_WMS_URL=
```

No crear variables `NEXT_PUBLIC_COPERNICUS_CLIENT_ID` ni `NEXT_PUBLIC_COPERNICUS_CLIENT_SECRET`.

## Variables del frontend

El frontend solo necesita las URLs de EcoNexo:

```env
NEXT_PUBLIC_API_URL=https://econexo.onrender.com
NEXT_PUBLIC_WS_URL=wss://econexo.onrender.com
NEXT_PUBLIC_DEMO_MODE=false
NEXT_PUBLIC_STATIC_EXPORT=true
```

Las imágenes Process API se solicitan a `/copernicus/image` con el JWT del usuario. El navegador nunca se autentica directamente contra CDSE.

## Capas disponibles

| EcoNexo | Índice/producto | Bandas Sentinel-2 L2A | Uso operativo |
|---|---|---|---|
| Color natural | TRUE_COLOR | B04, B03, B02 | contexto visual del territorio |
| Vegetación | NDVI | B08, B04 | vigor/cobertura vegetal |
| Humedad | NDMI | B08, B11 | humedad vegetal y superficial relativa |
| Quema | NBR | B08, B12 | señal de huella/severidad de quema |

Estas capas son indicadores remotos. No sustituyen una inspección de campo ni certifican por sí solas un incendio, daño o área quemada oficial.

## Flujo operativo

1. La organización mantiene `copernicus_enabled=true` y `copernicus_use_system_default=true`.
2. `GET /copernicus/status` resuelve el proveedor efectivo sin devolver secretos.
3. `POST /copernicus/test` solicita un mosaico de prueba de 64 × 64 px sobre Misiones.
4. El mapa solicita `GET /copernicus/image` con capa, BBOX y dimensiones.
5. El backend limita el BBOX al territorio operativo, obtiene/reutiliza el token OAuth y llama a Process API.
6. Se valida que la respuesta sea PNG, se almacena temporalmente en caché y se entrega al usuario autenticado.
7. Ante falta de credenciales, Humedad y Área quemada mantienen fallbacks operativos claramente rotulados; Color natural y NDVI informan configuración pendiente.

## Seguridad aplicada

- secretos únicamente en el backend;
- URLs OAuth y Process limitadas a dominios oficiales;
- WMS limitado a `sh.dataspace.copernicus.eu/ogc/wms/<INSTANCE_ID>`;
- bloqueo de SSRF mediante normalización estricta;
- BBOX recortado a Misiones;
- dimensiones y rango temporal limitados;
- rate limiting para prueba e imágenes;
- timeout de red;
- token OAuth almacenado solo en memoria y renovado antes del vencimiento;
- caché de imágenes sin datos de usuario;
- auditoría de pruebas por organización;
- respuestas de error sin client secret, access token ni payload sensible.

## Verificación en producción

### Estado general

```text
GET https://econexo.onrender.com/health
```

Debe informar:

```json
{
  "features": {
    "copernicus_default_mode": "process_api",
    "copernicus_process_configured": true
  }
}
```

### Desde la interfaz

1. Ingresar con rol administrador.
2. Abrir `Admin Core > Fuentes SpaceAI`.
3. Mantener activado `Usar Copernicus predeterminado del sistema`.
4. Presionar `Probar Copernicus`.
5. Verificar que informe `Process API` y una imagen PNG recibida.
6. Volver al Centro de Comando y alternar Color natural, NDVI, Humedad y Área quemada.

### Diagnóstico de fallas

| Estado | Interpretación | Acción |
|---|---|---|
| `provider=none` | no hay OAuth ni WMS efectivo | cargar credenciales en la API |
| OAuth HTTP 401 | client ID/secret rechazados | regenerar o copiar nuevamente el OAuth client |
| HTTP 429 | límite temporal del proveedor | esperar y reducir frecuencia |
| Process API 400 | petición o permisos no admitidos | revisar logs y cuenta CDSE |
| imagen vacía/no disponible | nubes o falta de escenas en el rango | ampliar `COPERNICUS_TIME_RANGE_DAYS` con cautela |
| WMS sin capas | INSTANCE_ID inválido o configuración vacía | revisar Configuration Utility |
| CORS en navegador | origen web no permitido | corregir `PUBLIC_APP_URL` y `CORS_ORIGINS` |

## Fuentes oficiales de referencia

- WMS y configuración OGC: `https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/OGC/WMS.html`
- Process API: `https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html`
- Autenticación: `https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html`
- Dashboard CDSE: `https://shapps.dataspace.copernicus.eu/dashboard/`
