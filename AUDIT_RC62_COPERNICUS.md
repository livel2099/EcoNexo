# Auditoría integral — EcoNexo 1.0.0-rc.6.2

**Alcance:** código adjunto `ECONEXO BETA (2)(1).zip`, consolidación Render rc.6.1, API FastAPI, frontend Next.js, base PostGIS, Copernicus, FIRMS, telemetría, pipeline, administración y empaquetado.

## 1. Resultado ejecutivo

La entrega adjunta no era desplegable como versión final: incluía una copia antigua de la API, dependencias y artefactos compilados dentro del ZIP, y contratos de tests que no coincidían con el código. Se tomó como base la última consolidación estable rc.6.1 y se incorporaron los cambios de Copernicus, telemetría y administración requeridos.

**Resultado rc.6.2:** aprobado para desplegar en Render una vez configuradas las credenciales productivas de PostgreSQL, JWT, token interno y Copernicus CDSE. No se incluyen secretos reales.

## 2. Hallazgos en el archivo adjunto

| Hallazgo | Evidencia | Riesgo | Resolución |
|---|---:|---|---|
| Paquete excesivo | 18.809 entradas; 832.222.267 bytes sin comprimir | deploy lento, ruido y exposición accidental | ZIP final excluye dependencias y artefactos |
| Repositorio Git incluido | 3.596 entradas `.git` | historial y metadatos innecesarios | excluido del paquete |
| `node_modules` incluido | 14.211 entradas | binarios de otra plataforma y cientos de MB | se usa `npm ci` en Render |
| `.next` y `out` incluidos | 2.694 + 117 entradas | build obsoleto/incompatible | excluidos y reconstruidos por Render |
| Python cache incluido | 107 entradas `__pycache__` | basura de runtime | excluido |
| Configuración antigua | `release_version=1.0.0-rc.4-render` | despliegue desincronizado | consolidada en rc.6.2 |
| Faltaban rutas nuevas | `main.py` adjunto no registraba Copernicus/pipeline/plataforma | funcionalidades invisibles | routers consolidados y auditados |
| Faltaba migración 14/15 | el adjunto terminaba en migración 13 | esquema incompatible con UI | migraciones 14 y 15 incluidas y sincronizadas |
| Tests y contratos desalineados | test importaba `PasswordChangeIn` inexistente | falla en colección | contratos y endpoints reconciliados |

## 3. Copernicus: corrección de arquitectura

### Situación anterior

- WMS dependía de un `INSTANCE_ID` cargado manualmente por organización.
- La interfaz podía habilitar Copernicus sin un proveedor realmente operativo.
- Las capas quedaban bloqueadas o degradadas cuando la URL WMS faltaba.
- Se mezclaban nombres internos (`MOISTURE_INDEX`, `NBR_RAW`) con nombres técnicos de índices.

### Implementación rc.6.2

- Process API es el modo predeterminado.
- OAuth2 `client_credentials` se resuelve en FastAPI.
- Sentinel-2 L2A es la colección utilizada.
- Evalscript propio para TRUE_COLOR, NDVI, NDMI y NBR.
- Proxy autenticado `/copernicus/image` para evitar secretos en el navegador.
- Estado y diagnóstico en `/copernicus/status` y `/copernicus/test`.
- WMS oficial se conserva como override/fallback.
- El mapa inicia con Color natural y permite seleccionar las cuatro capas.
- Si faltan credenciales, se muestra un estado explícito y fallbacks rotulados en Humedad/Quema.

## 4. Seguridad

### Controles verificados

- RBAC y JWT para imágenes, pruebas y configuración.
- OAuth client secret no aparece en respuestas ni variables públicas.
- WMS restringido al dominio oficial y a una ruta con `INSTANCE_ID` válido.
- URLs de token y Process API verificadas contra dominios oficiales en producción.
- BBOX validado y recortado a Misiones.
- Dimensiones máximas y rango temporal acotados.
- Rate limiting de prueba e imágenes.
- Timeout y manejo de HTTP 401/429/5xx.
- Validación de `Content-Type` y firma PNG.
- Caché en memoria con TTL y sin persistencia de access tokens.
- CORS con origen oficial de Render, métodos/headers autorizados y preflight cacheado.
- Un solo manejador global de excepciones; errores 500 no filtran secretos.
- Escaneo de marcadores Git, `.env` reales y claves privadas.
- Administrador general protegido por email + rol, no por una ruta “oculta” solamente.

### Dependencias web

- `next` 15.5.21.
- `react` y `react-dom` 19.0.8.
- El lockfile conserva versiones exactas.

La auditoría de vulnerabilidades remota de npm no pudo completarse en el entorno de ensamblado porque el endpoint del registro devolvió HTTP 503. CI debe ejecutar `npm audit` o una herramienta SCA con conectividad normal antes de la publicación estable.

## 5. Datos y concurrencia

La migración 15:

- agrega política de proveedor de sistema;
- habilita Copernicus por defecto en registros existentes;
- conserva WMS explícito como override;
- almacena última prueba, error y capas informadas;
- migra etiquetas de humedad/quema a NDMI/NBR;
- cierra corridas de pipeline huérfanas;
- crea una restricción única parcial para impedir dos corridas `running` simultáneas por organización.

El pipeline captura también la carrera de inserción para devolver un estado coherente en lugar de generar dos procesos concurrentes.

## 6. Pruebas ejecutadas

| Prueba | Resultado |
|---|---|
| Compilación Python (`compileall`) | aprobada |
| Suite API (`pytest -q`) | **70 aprobadas** |
| OAuth token cache | aprobada |
| Process API con Bearer y PNG | aprobada |
| Evalscript/bandas Sentinel-2 | aprobada |
| BBOX limitado a Misiones | aprobada |
| WMS oficial y prevención SSRF | aprobada |
| Parser GetCapabilities y ServiceException | aprobada |
| Secretos ausentes del status público | aprobada |
| CORS Render y GeoJSON defensivo | aprobada |
| Migraciones API/infra sincronizadas | aprobada |
| Guarda concurrente del pipeline | aprobada |
| Construcción de FastAPI | **98 objetos / 82 rutas únicas / 83 operaciones documentadas** |
| TypeScript (`tsc --noEmit`) | aprobado |
| JSON y YAML | aprobados |
| Sintaxis shell y servicios Node.js | aprobada |
| Marcadores de conflicto | ninguno |
| `.env` reales / claves privadas | ninguno |

### Limitaciones del entorno de auditoría

- El build Next.js completo no pudo descargar el binario opcional Linux de SWC porque el gateway de paquetes respondió HTTP 503. El typecheck sí fue aprobado. El workflow de CI y Render ejecutan `npm ci` y el build nuevamente.
- No se realizó una llamada real a una cuenta Copernicus porque el paquete no incluye credenciales del usuario. La integración se probó con `httpx.MockTransport`, contratos de payload y rutas completas.
- No se ejecutó un pentest externo ni una prueba de carga distribuida.

## 7. Variables obligatorias en Render

```env
ENVIRONMENT=production
RELEASE_VERSION=1.0.0-rc.6.2-render
DATABASE_URL=<INTERNAL_DATABASE_URL>
JWT_SECRET=<64+ caracteres>
INTERNAL_SERVICE_TOKEN=<64+ caracteres distintos>
PUBLIC_APP_URL=https://econexo-web.onrender.com
CORS_ORIGINS=https://econexo-web.onrender.com
FORWARDED_ALLOW_IPS=*
MQTT_ENABLED=false
S3_ENABLED=false
ANOMALY_ENABLED=false
RUN_MIGRATIONS_ON_START=true

COPERNICUS_ENABLED_BY_DEFAULT=true
COPERNICUS_MODE=process_api
COPERNICUS_CLIENT_ID=<CDSE OAuth client ID>
COPERNICUS_CLIENT_SECRET=<CDSE OAuth client secret>
COPERNICUS_TOKEN_URL=https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token
COPERNICUS_PROCESS_URL=https://sh.dataspace.copernicus.eu/process/v1
COPERNICUS_HTTP_TIMEOUT_SECONDS=45
COPERNICUS_TIME_RANGE_DAYS=90
COPERNICUS_MAX_CLOUD_COVERAGE=80
COPERNICUS_MAX_DIMENSION=1024
COPERNICUS_CACHE_SECONDS=600
```

## 8. Orden de despliegue

1. Aplicar el parche sobre un clon limpio.
2. Ejecutar `python scripts/audit-system.py`.
3. Subir a GitHub sin `--force`.
4. Desplegar API y verificar aplicación de migración 15.
5. Confirmar `/health` y `/copernicus/status` autenticado.
6. Desplegar frontend con caché limpia.
7. En Admin Core, ejecutar `Probar Copernicus`.
8. Abrir Centro de Comando y validar Color natural, NDVI, Humedad y Área quemada.
9. Ejecutar pipeline y confirmar dispositivos, geocercas, FIRMS y alertas.

## 9. Criterio de aceptación

La integración se considera operativa cuando:

- `/health` informa `copernicus_process_configured=true`;
- `/copernicus/test` devuelve `ok=true` y `provider=process_api`;
- el mapa recibe PNG para las cuatro capas;
- no aparecen secretos en Network/Console;
- el preflight CORS devuelve el origen exacto del frontend;
- el pipeline no permite dos corridas simultáneas por organización;
- la suite y el typecheck permanecen en verde.
