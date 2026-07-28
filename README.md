# EcoNexo

**Plataforma de inteligencia ambiental para detectar, correlacionar y documentar incidentes antes de que escalen.**

EcoNexo combina sensores IoT, observación satelital, meteorología, reportes ciudadanos y reglas operativas para producir alertas priorizadas, trazabilidad e informes institucionales. Esta edición fue preparada como **candidato de lanzamiento técnico 1.0.0-rc.4 para la provincia de Misiones**. La arquitectura y los flujos principales están implementados y territorialmente restringidos; la publicación oficial todavía exige completar identidad societaria, revisión jurídica, infraestructura pública, credenciales productivas y la puerta de aceptación indicada en la documentación.

## Deploy en Render

La API incluye Blueprint, migraciones versionadas y plantilla de variables:

- `render.yaml` — beta gratuita, con migraciones al iniciar.
- `render.production.yaml` — producción paga, con migraciones Pre-Deploy.
- `.env.render.example` — configuración para pegar en Render.
- `RENDER_DEPLOY.md` — guía paso a paso.


## Qué incorpora esta edición

- **Login y registro completo por email y contraseña**; el primer usuario crea la organización y queda como administrador.
- Google Identity Services permanece como proveedor opcional cuando se configura `GOOGLE_CLIENT_ID`.
- Centro de comando multiorganización, dispositivos, alertas, reglas, KPI, mapa y feed en tiempo real, limitado a los 17 departamentos y 79 municipios de Misiones.
- **Alerta IA / Observatorio SpaceAI** con telemetría por dispositivo, contexto Open-Meteo/CAMS/GloFAS, focos NASA FIRMS, gemelo digital, mensajes revisables y Health Threat Index R0-R5.
- Módulo licenciable **Focos de incendio forestal y humo**, con lenguaje claro, mapa base nítido, evidencia satelital diferenciada de confirmación oficial y registro de comunicaciones.
- **Admin Core / ABM** para usuarios, roles, organización, geocercas PostGIS, fuentes ambientales, dispositivos, reglas y auditoría.
- Bandeja **Mensajes**: cada login correcto por email o Google notifica a los administradores con contexto de acceso e IP anonimizada.
- Suscripciones limitadas por organización: sandbox, diagnóstico, piloto, municipal, provincia/pro, enterprise y academia; solicitud, aprobación comercial, vencimiento, consumo y módulos habilitados.
- Canal ciudadano con formulario completo, consentimiento, geolocalización bajo demanda, carga de fotografías, token firmado, límites de uso, validación de imágenes y moderación.
- Módulo **Informes para organizaciones y PO** con reportes operativos y ambientales extensos, fórmulas, cálculos por dominio, observaciones, fuentes, limitaciones, snapshot SpaceAI, impresión/PDF, CSV, resumen para email y enlace público revocable.
- Cliente móvil nativo en **Expo + React Native** para Android/iOS con Inicio, Fuego y Humo, Alerta IA, reportes con foto/ubicación y cuenta.
- Identidad visual tecnológica: logotipo construido por circuitos, fondo de trazas, paquetes de datos y línea IA animada.
- Términos, privacidad, cookies, seguridad, accesibilidad, metodología pública, estado del sistema, footer legal, robots y sitemap.
- Protección del endpoint satelital y del servicio de notificaciones mediante credencial interna.
- Bucket privado, referencias S3 internas, URLs firmadas, encabezados de seguridad y rechazo de secretos de ejemplo en producción.
- Docker multietapa, usuario no-root, manifiestos Kubernetes, CI y documentación de despliegue/due diligence.

## Arquitectura

```text
                              ┌──────────── Next.js ────────────┐
                              │ acceso email/Google · dashboard · PWA │
                              │ informes · legales · mapa       │
                              └──────────────┬──────────────────┘
                                             │ REST / WebSocket
                              ┌──────────────▼──────────────────┐
                              │ FastAPI core                    │
                              │ auth · RBAC · alertas · reglas  │
                              │ reportes · informes · auditoría │
                              └───┬────────┬────────┬───────────┘
                                  │        │        │
                         PostgreSQL/   MQTT bus   S3 privado
                           PostGIS       │       (evidencias)
                                        │
                    ┌───────────────────┼────────────────────┐
                    │                   │                    │
               ingest Node       anomaly PyTorch     satellite OpenCV/FIRMS
                    │                                        │
                 ESP32 /                                  token interno
                simulador
```

| Ruta | Responsabilidad | Tecnología |
|---|---|---|
| `apps/web` | Acceso, dashboard, PWA ciudadana, informes y marco legal | Next.js 15, React 19, TypeScript, Leaflet |
| `apps/api` | API, autenticación, separación por organización, correlación, informes | FastAPI, asyncpg, JWT, Google Auth |
| `apps/mobile` | Cliente móvil, mapa, reportes, licencias y Alerta IA | Expo SDK 56, React Native, TypeScript |
| `services/ingest` | Consumo MQTT y persistencia de telemetría | Node.js |
| `services/notify` | Notificaciones internas autenticadas | Node.js |
| `services/anomaly` | Puntaje de anomalías | PyTorch |
| `services/satellite` | Detecciones FIRMS y procesamiento raster | Python, OpenCV |
| `infra/db` | Esquema PostGIS y migraciones | PostgreSQL/PostGIS |
| `k8s` | Referencia de despliegue | Kubernetes |

## Inicio local

Requisitos: Docker y Docker Compose v2.

```bash
cp .env.example .env
# Configure JWT_SECRET e INTERNAL_SERVICE_TOKEN con al menos 32 caracteres.
docker compose up -d --build
docker compose run --rm api python -m app.seed
```

Abrir:

- App: `http://localhost:3000`
- API/Swagger: `http://localhost:8000/docs`
- Reporte ciudadano: `http://localhost:3000/reportar`
- MinIO: `http://localhost:9090`

Datos demo: `admin@misiones.econexo.ar` / `econexo123`. Estas credenciales son exclusivamente locales y no deben existir en un entorno real.

## Login y registro

El flujo principal funciona sin Google: seleccioná **Crear organización**, completá organización, vertical, administrador, email y contraseña, aceptá los textos legales y la API creará en una transacción la organización y su primer usuario administrador. La ruta es `POST /auth/register`.

Google es opcional. Para habilitarlo en web y, si corresponde, en Android/iOS:

1. Crear un cliente OAuth 2.0 de tipo **Web application** en Google Cloud Console.
2. Registrar `http://localhost:3000` y el dominio productivo como JavaScript origins.
3. Asignar el cliente web a `GOOGLE_CLIENT_ID`; Docker lo entrega al backend y a `NEXT_PUBLIC_GOOGLE_CLIENT_ID` durante el build web. Para clientes nativos, agregar sus IDs separados por coma en `GOOGLE_CLIENT_IDS`.
4. Reiniciar/reconstruir la app.

Para Google, el backend valida firma, audiencia, emisor, vencimiento y `email_verified`; usa `sub` como identificador estable. Si `GOOGLE_CLIENT_ID` queda vacío, la interfaz oculta Google y mantiene disponible el registro por email. Detalle: [docs/EMAIL_AUTH.md](docs/EMAIL_AUTH.md) y [docs/GOOGLE_AUTH.md](docs/GOOGLE_AUTH.md).

## Informes para organizaciones o PO

Dentro del dashboard, la sección **Informes** permite:

1. seleccionar período y destinatario (`organización`, `municipio`, `programa/organismo — PO`, `inversor`, `aseguradora` o `auditoría`);
2. consolidar dispositivos, alertas, severidad, tiempos y reportes ciudadanos;
3. agregar resumen y recomendaciones;
4. imprimir/guardar PDF, exportar CSV o copiar un brief para email;
5. publicar un enlace de alta entropía, almacenado como hash y revocable.

Los documentos aclaran metodología y límites: no equivalen a una certificación independiente. Incluyen excedencia relativa, `Score_i`, HTI, matriz R0-R5, reglas categóricas, detalle por dominio, observaciones, procedencia, focos térmicos y checklist de validación. Detalle: [docs/IMPACT_REPORTS.md](docs/IMPACT_REPORTS.md) y [docs/REPORTING_METHOD.md](docs/REPORTING_METHOD.md).

## Migraciones

En una base nueva, Docker ejecuta `infra/db/migrations/*.sql`. En una base existente, aplicar en orden y con respaldo:

```bash
for migration in infra/db/migrations/*.sql; do
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration"
done
```

Las migraciones 02-04 agregan identidad por contraseña/Google, aceptación legal, informes institucionales, snapshots SpaceAI, fuentes ambientales, geocercas y auditoría. La migración 05 agrega licencias modulares y trazabilidad de comunicaciones de Alerta IA. Las migraciones 06-09 incorporan alcance Misiones, exclusión de registros externos, auditoría territorial y límite provincial versionado con sincronización oficial desde GeoRef Argentina. La migración 10 incorpora Copernicus y sanidad forestal; la 11 agrega planes, suscripciones, límites de consumo, solicitudes comerciales y mensajes administrativos de login. En Render, `python -m app.migrate` registra checksums y usa un advisory lock. El plan gratuito ejecuta migraciones al arrancar; el plan pago debe usar Pre-Deploy Command antes de escalar réplicas.

## Validación

```bash
make validate
# o por separado
cd apps/api && pytest -q
cd apps/web && npm ci && npm run typecheck && npm run build
```

Estado de esta entrega:

- API: 39 pruebas aprobadas (`pytest -q`).
- Python: compilación de módulos aprobada (`python -m compileall`).
- Web y móvil: archivos TypeScript/TSX parseados con TypeScript 5.8.3 sin errores de sintaxis.
- JSON, YAML y CSS: parseo aprobado; la hoja CSS contiene 985 reglas de nivel superior sin errores.
- La instalación completa de dependencias web, el `npm run typecheck` y el build de Next.js deben repetirse en la estación de destino: el entorno de ensamblado no pudo completar `npm ci` por indisponibilidad de su gateway de paquetes.
- La app móvil incluye código fuente y perfiles EAS; no incluye APK/IPA porque faltan el `projectId`, las credenciales de firma y la ejecución del build externo.

## Aplicación móvil

```bash
cd apps/mobile
cp .env.example .env
npm install
npx expo install --fix
npm run typecheck
npm run start:clear
```

Para un teléfono físico, `EXPO_PUBLIC_API_URL` debe apuntar a la IP LAN de la computadora o a una API HTTPS pública; `localhost` refiere al propio teléfono. Los perfiles EAS `preview` y `production` están incluidos, pero el `projectId`, credenciales de tienda, URLs públicas y clientes OAuth nativos deben completarse antes de generar binarios. Ver [docs/MOBILE_APP.md](docs/MOBILE_APP.md).

## Producción

No publicar con valores de ejemplo. Como mínimo:

- dominio/TLS, CORS exacto y Google origin productivo;
- Secrets Manager/External Secrets y rotación;
- PostgreSQL administrado con PostGIS, backup/PITR y migraciones;
- S3 privado con cifrado, lifecycle, CORS restringido y análisis de archivos;
- MQTT autenticado por dispositivo o AWS IoT Core;
- WAF/API gateway y rate limiting distribuido;
- observabilidad, alertas, runbooks y prueba de restauración;
- asesoría legal argentina, contratos, DPA, identidad societaria y registro/obligaciones aplicables;
- prueba de penetración y auditoría de accesibilidad.

Puerta de lanzamiento: [docs/OFFICIAL_LAUNCH_MISIONES.md](docs/OFFICIAL_LAUNCH_MISIONES.md). Alcance territorial: [docs/MISIONES_TERRITORIAL_SCOPE.md](docs/MISIONES_TERRITORIAL_SCOPE.md). Guía de infraestructura: [docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md). Plantilla productiva: [`.env.production.example`](.env.production.example). Scripts: [`scripts/`](scripts/). Riesgos abiertos: [AUDIT.md](AUDIT.md).

## Documentación clave

- [Preparación para inversión](INVESTOR_READINESS.md)
- [Seguridad](SECURITY.md)
- [Due diligence](docs/DUE_DILIGENCE_CHECKLIST.md)
- [Checklist legal](docs/LEGAL_LAUNCH_CHECKLIST.md)
- [Fuentes de datos](docs/DATA_SOURCES.md)
- [SpaceAI y Open-Meteo](docs/SPACEAI_OPEN_METEO.md)
- [Admin Core / ABM](docs/ADMIN_ABM.md)
- [Suscripciones y mensajes administrativos](docs/SUBSCRIPTIONS_AND_ADMIN_MESSAGES.md)
- [Reportes oficiales](docs/OFFICIAL_REPORTS.md)
- [Método de informes técnicos](docs/REPORTING_METHOD.md)
- [Módulo Fuego y Humo](docs/FIRE_SMOKE_MODULE.md)
- [Marco operativo de incendios en Misiones](docs/MISIONES_FIRE_POLICY.md)
- [Alcance territorial de Misiones](docs/MISIONES_TERRITORIAL_SCOPE.md)
- [Migrar una base existente](docs/MIGRATE_EXISTING_MISIONES.md)
- [Puerta de lanzamiento oficial](docs/OFFICIAL_LAUNCH_MISIONES.md)
- [Cloudflare productivo](docs/DEPLOY_CLOUDFLARE_PRODUCTION.md)
- [Aplicación móvil](docs/MOBILE_APP.md)
- [Sistema de marca](docs/BRAND_SYSTEM.md)
- [Despliegue Kubernetes](k8s/README.md)
- [Reporte de validación del ensamblado](VALIDATION_REPORT.md)
- [Cambios de esta edición](CHANGELOG.md)

## Licencia y confidencialidad

El repositorio no declara una licencia open source. Ver [LICENSE.md](LICENSE.md). Antes de compartirlo con terceros, confirmar titularidad del código, licencias de dependencias, marcas, datos, modelos y contribuciones.

### Copernicus Sentinel-2 en tiempo de ejecución

La configuración recomendada ya no depende de una variable pública de compilación. Un administrador carga la URL de su instancia Sentinel Hub en `Admin Core > Fuentes SpaceAI`, ejecuta GetCapabilities y guarda los nombres de las capas. La variable `NEXT_PUBLIC_COPERNICUS_WMS_URL` se conserva solamente como fallback.

### Sanidad forestal del norte

La navegación incluye un módulo licenciable para San Antonio y General Manuel Belgrano. Combina contexto meteorológico, NDVI, humedad, recorridas, trampas, reportes y trazabilidad. El radar de Bernardo de Irigoyen se usa como contexto meteorológico regional y no confirma ni identifica una plaga.
# EcoNexo
# EcoNexo
# econexoarg
# econexo
# ECONEXO-BETA
# EcoNexo

## Consola privada del administrador general (rc.5)

La edición incluye una consola no enlazada en la navegación pública:

```text
/plataforma
```

El correo autorizado es `econexoargentina@gmail.com` mediante `PLATFORM_ADMIN_EMAILS`. La contraseña inicial se configura únicamente en Render con `PLATFORM_ADMIN_INITIAL_PASSWORD`; nunca debe incorporarse al repositorio ni usar el prefijo `NEXT_PUBLIC_`. El primer ingreso exige cambiarla en `/cambiar-contrasena`.

Guía completa: [`ADMIN_GENERAL_OCULTO.md`](ADMIN_GENERAL_OCULTO.md).
