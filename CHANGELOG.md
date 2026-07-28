# Changelog

## 1.0.0-rc.4 - 2026-07-27

- Corregidas respuestas HTTP 204 del panel de mensajes administrativos.
- Configuración de producción compatible con Render mediante `DATABASE_URL`.
- Blueprints beta y producción, migraciones con checksum y advisory lock.
- Adaptadores MQTT, S3 y anomalías opcionales para el despliegue core.
- Dockerfile con validación previa, puerto `PORT` y compilación de sintaxis.
- Plantillas `.env.render.example` y documentación de despliegue.
- Pool PostgreSQL configurable y soporte de URL interna administrada.
- CI corregido para dependencias de desarrollo separadas.
- Script de arranque Docker separado y validado; migraciones al inicio para plan gratuito y Pre-Deploy para plan pago.
- Guardas de producción rechazan placeholders de `.env` antes de abrir el servidor.

## 1.0.0-rc.3 - 2026-07-27

- Notificación interna por cada login correcto mediante email o Google, con IP anonimizada, proveedor y contexto de acceso.
- Nueva bandeja `Admin Core > Mensajes`, lectura individual y contador de pendientes por administrador.
- Catálogo de planes basado en el plan de negocios: diagnóstico, piloto 8 semanas, municipal, provincia/pro, enterprise y academia.
- Sandbox calificado de 14 días para altas nuevas; sin prueba gratuita abierta e ilimitada.
- Límites por licencia para usuarios, dispositivos, geocercas, reglas e informes mensuales, con respuesta HTTP 402 al excederlos.
- Solicitudes de cambio de plan, aprobación manual y consola comercial restringida por `PLATFORM_ADMIN_EMAILS`.
- Sincronización de módulos licenciados y posibilidad de sobrescribir límites por contrato.
- Migración `11_subscriptions_and_admin_login_notifications.sql`.


## 2026-07-25 — Fuego y humo, Alerta IA, informes de laboratorio y app móvil

### Producto y comunicación
- Nuevo módulo licenciable **Focos de incendio forestal y humo** con lenguaje claro, estado de licencia, mapa, señales térmicas, contexto de propagación, humo probable y mensajes revisables.
- Observatorio renombrado a **Alerta IA**, con borradores para WhatsApp, Telegram, email a laboratorios y copia, siempre bajo aprobación humana.
- Formulario de reportes comunitarios/institucionales con ubicación, foto, descripción, auditoría y cola de moderación.
- Mapa base activado por defecto; capas Copernicus opcionales y retiro automático de mosaicos degradados para evitar visualizaciones pixeladas o vacías.
- Integración del logotipo oficial en acceso, módulo Fuego y Humo y activos móviles.
- Logotipo oficial incorporado también al centro de comando y a las portadas de informes; el símbolo tecnológico animado permanece como recurso visual secundario.
- Estabilidad del mapa mejorada evitando reinicializaciones por referencias de coordenadas y manteniendo el mapa base visible cuando la capa satelital falla.

### Informes y datos
- Informes ampliados con fórmulas de excedencia, Score por indicador y HTI, matriz R0-R5, observaciones, cálculos por dominio, procedencia, limitaciones y checklist de validación.
- Migración 05 para licencias por organización y trazabilidad de comunicaciones de Alerta IA.
- Nuevos endpoints `/modules/me`, `/modules/alert-share` y `/reports/internal`.
- Google OAuth admite una lista explícita de audiences web/Android/iOS mediante `GOOGLE_CLIENT_IDS`.

### Móvil
- Nueva app Expo/React Native para Android e iOS con Inicio, Fuego y Humo, Alerta IA, reportes con cámara/ubicación y cuenta.
- SecureStore, mapas nativos, Google opcional y perfiles EAS de preview/producción.

## 2026-07-24 — Acceso local, registro por email y marca visible

### Autenticación
- Registro transaccional de organizaciones mediante email y contraseña en `POST /auth/register`.
- Primer usuario creado con rol administrador, aceptación legal y hash Argon2.
- Google OAuth pasa a ser opcional; con `GOOGLE_CLIENT_ID` vacío se oculta el proveedor externo.
- Mensajes diferenciados para credenciales inválidas y API inaccesible.
- Corrección del redireccionamiento automático ante `401` durante el intento de login.

### Experiencia y conectividad
- Logotipo tecnológico visible dentro del panel de acceso en escritorio y móvil.
- Indicador de estado de API/base con acción de reintento.
- CORS local compatible con `localhost` y `127.0.0.1`.
- Registro por email habilitado también en la demo estática de Cloudflare.
- 20 pruebas de API y chequeo TypeScript aprobados.

## 2026-07-24 — SpaceAI, Admin Core y ensamblado final

### Inteligencia ambiental
- Observatorio por dispositivo con telemetría local y contexto Open-Meteo, CAMS y GloFAS.
- Integración preparada para NASA FIRMS mediante credencial de entorno.
- Health Threat Index y dominios R0-R5 basados en la metodología SpaceAI.
- Gemelo digital, AI Threat Line, circuitos y trazas de datos animadas.

### Administración y documentos
- Admin Core con ABM de usuarios, roles, organización, geocercas, fuentes y auditoría.
- Snapshots ambientales versionados y activación supervisada de alertas.
- Informes de desempeño, boletines, partes institucionales e informes de episodio con anexo SpaceAI.
- Migraciones 03 y 04 para persistencia ambiental y controles administrativos.

### Marca y calidad
- Logotipo SVG tecnológico, favicon/PWA actualizado y estilos responsivos.
- 17 pruebas de API, compilación Python y chequeo TypeScript aprobados.
- Build Next.js pendiente de repetición en CI por indisponibilidad HTTP 503 del binario SWC Linux en el entorno de ensamblado.

## 2026-07-23 — Investor-ready hardening

### Producto
- Nueva pantalla inicial de posicionamiento, login y creación de organización.
- Registro e inicio de sesión con Google Identity Services.
- Nueva sección de informes institucionales para organizaciones y PO.
- Documento ejecutivo imprimible, CSV, brief para correo y enlaces revocables.
- Rediseño del canal ciudadano con ubicación explícita y consentimiento.
- Páginas de términos, privacidad, cookies, seguridad y accesibilidad.

### Backend y datos
- Verificación server-side de Google ID tokens y vinculación por `sub`.
- Migración de identidad, aceptación legal, informes y auditoría.
- Protección del endpoint satelital y del servicio de notificaciones.
- Token ciudadano firmado, límites y validación de archivos.
- Bucket privado y URLs firmadas.
- Validación de secretos de producción y encabezados de seguridad.

### Ingeniería
- Docker web multietapa con Next standalone y usuario no-root.
- Docker API no-root.
- Manifiestos Kubernetes reforzados, PDB e ingress de referencia.
- CI, Dependabot, documentación de producción y due diligence.
- 17 pruebas de API y chequeo TypeScript aprobados en la preparación.

## 2026-07-23 - Cloudflare static export fix

- Declared `app/robots.ts` and `app/sitemap.ts` as `force-static` metadata routes so Next.js 15 can include them in `output: "export"` builds.
- Anchored `outputFileTracingRoot` to `apps/web` to avoid ambiguous workspace-root detection when multiple npm lockfiles exist.

## 1.0.0-misiones-rc · 2026-07-27

- Reorientación integral a la provincia de Misiones: 17 departamentos, 79 municipios, centros operativos, mapas, seeds, móvil, formularios y reportes.
- Exclusión de coordenadas externas en dispositivos, alertas, reportes, snapshots, geocercas, detecciones, KPIs y métricas institucionales.
- Migraciones 06-08 con guardas PostGIS, auditoría de filas externas y límite oficial versionado.
- Sincronización administrativa del límite provincial desde GeoRef Argentina y endpoint GeoJSON para el mapa.
- NASA FIRMS limitado a Misiones; fixtures deshabilitados por defecto y prohibidos implícitamente en producción salvo activación expresa.
- Readiness `/ready`, estado territorial, página pública `/estado` y metodología `/metodologia`.
- Informes institucionales ampliados con código documental, territorio, laboratorio, muestra, protocolo, fórmulas, QA, revisión y firmas.
- Worker Cloudflare productivo separado (`econexo-misiones`) y variables completas de build.
- Panel Admin Core con puerta de lanzamiento y sincronización GeoRef.

## 1.0.0-rc.2 - 2026-07-27

- Seed institucional corregido con provincia, departamento, municipio y alcance territorial para Posadas, San Pedro/Yaboti y Obera.
- Usuario demo del backend alineado con `admin@misiones.econexo.ar`.
- Mensaje demo de incendio cambiado de "confirmado" a senal multifuente pendiente de verificacion.
- Etiqueta FIRMS sin clave cambiada de fixture a "sin datos reales".
- Guardia de arranque productivo ampliada: HTTPS, CORS, S3 cifrado y proxy confiable.
- Plantilla `.env.production.example` y scripts PowerShell para deploy y pre-flight.
- Documentacion de validacion, auditoria, roadmap y produccion actualizada.
- 29 pruebas API aprobadas; 44 archivos TypeScript/TSX y 860 reglas CSS validadas.

## 1.0.0-rc.2 - Copernicus y sanidad forestal norte

- Configuración WMS de Copernicus por organización y en tiempo de ejecución.
- Prueba segura de GetCapabilities desde Admin Core.
- Nombres de capas configurables para color natural, NDVI, humedad y área quemada.
- Nuevo módulo licenciable de vigilancia preventiva de plagas forestales.
- Área prioritaria San Antonio y contexto del radar meteorológico de Bernardo de Irigoyen.
- Advertencias explícitas: el radar no identifica especies ni confirma una plaga.
- Migración `10_copernicus_forestry_pests.sql`.
