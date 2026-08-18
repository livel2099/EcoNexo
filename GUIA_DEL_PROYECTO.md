# EcoNexo — guía del proyecto desde cero

Versión `1.0.0-rc.6.2-render` · 18 de agosto de 2026

Esta guía está escrita para alguien que nunca vio el proyecto. Explica qué problema
resuelve, cómo está armado, qué hace cada parte y cómo levantarlo. No hace falta conocer
el código para leerla.

---

## 1. Qué es EcoNexo

EcoNexo es una plataforma de decisión ambiental en tiempo real para la provincia de
Misiones, Argentina: 17 departamentos y 79 municipios.

El problema que ataca es concreto. Cuando se inicia un incendio forestal, un vertido o una
crecida, la información existe pero está repartida: un sensor mide humo, un satélite
detecta calor, un vecino ve una columna gris, el servicio meteorológico informa viento. Por
separado, ninguna de esas señales alcanza para actuar. Juntas y cruzadas en el espacio y en
el tiempo, sí.

EcoNexo hace ese cruce. Toma cuatro fuentes:

1. **Sensores IoT** (nodos ESP32) que publican temperatura, humedad, partículas y gases;
2. **Observación satelital** — focos térmicos de NASA FIRMS e imágenes de Copernicus;
3. **Meteorología y calidad del aire** — Open-Meteo, CAMS y GloFAS;
4. **Reportes ciudadanos** con foto y ubicación.

Y produce tres cosas:

- **alertas priorizadas** con un porcentaje de confianza y las fuentes que las respaldan;
- **trazabilidad** — cada confirmación, descarte o escalamiento queda registrado;
- **informes institucionales** exportables y compartibles por enlace revocable.

### Lo que EcoNexo no es

Esto importa tanto como lo anterior, y está declarado en la propia interfaz:

- **no es un canal de emergencias.** Ante fuego o riesgo inmediato se llama al 911;
- **no confirma un incendio por sí solo.** La evidencia satelital es un indicio; la
  confirmación corresponde a los organismos competentes;
- **no reemplaza una certificación independiente.** Los informes son documentación
  trazable, no peritajes.

### Alcance territorial

La edición actual está restringida a Misiones. Las señales que caen fuera del límite
provincial se excluyen del centro de comando de forma deliberada. El límite se carga desde
GeoRef (IGN/INDEC): 29.918,90 km². Si esa sincronización no se ejecuta, el sistema usa un
polígono de reserva más grosero de 37.533 km² y las validaciones quedan corridas en los
bordes.

---

## 2. Cómo está armado

Nueve servicios que se levantan juntos con Docker Compose.

| Servicio | Tecnología | Para qué sirve | Puerto |
|---|---|---|---|
| `web` | Next.js 15 · React 19 · TypeScript | Interfaz completa | 3000 |
| `api` | FastAPI · Python 3.12 | Núcleo: autenticación, alertas, informes, territorio | 8000 |
| `postgis` | PostgreSQL 16 + PostGIS 3.4 | Base de datos con geometría | 5432 |
| `mosquitto` | Eclipse Mosquitto 2 | Bus MQTT para los sensores | 1883 |
| `minio` | MinIO | Almacenamiento de fotos, compatible con S3 | 9000 / 9090 |
| `anomaly` | Python | Servicio de detección de anomalías | 8100 |
| `ingest` | Node.js | Consume MQTT y escribe lecturas | interno |
| `notify` | Node.js | Notificaciones | 8200 |
| `satellite` | Python | Consulta NASA FIRMS periódicamente | interno |

Además, fuera de Compose:

- `apps/mobile` — aplicación Expo / React Native para Android e iOS;
- `firmware/esp32_node.ino` — el firmware del nodo físico;
- `simulator/` — simulador de nodos ESP32, para probar sin hardware.

### El recorrido de un dato

```
Sensor ESP32
   └─ publica por MQTT ──► mosquitto
                              └─► ingest ──► guarda en postgis (tabla readings)
                                                │
NASA FIRMS ──► satellite ───────────────────────┤
Open-Meteo / CAMS ──► el navegador consulta ────┤
Reporte ciudadano ──► api ──► foto a minio ─────┤
                                                ▼
                                    motor de reglas (rules)
                                                │
                                                ▼
                                    alerta con confianza y fuentes
                                                │
                                                ▼
                                  centro de comando · informes
```

El punto interesante es el cruce: una alerta nace cuando varias fuentes coinciden en la
misma zona y ventana de tiempo. Una regla puede pedir, por ejemplo, temperatura sobre 42°
**y** humedad bajo 18% — o un foco satelital **más** un reporte ciudadano cercano.

### La base de datos

38 tablas. Las principales:

- `organizations` — cada organización es un inquilino aislado del resto;
- `users` — con rol `admin` u `operador`, contraseñas con hash Argon2;
- `devices` / `device_types` / `readings` — la red de sensores y su telemetría;
- `alerts` / `alert_sources` / `alert_events` — alertas, de qué fuentes vienen y qué se hizo;
- `rules` — las condiciones que disparan alertas;
- `citizen_reports` / `citizens` — reportes de la comunidad;
- `satellite_detections` — focos térmicos;
- `risk_zones` / `territory_boundaries` — geometría PostGIS;
- `impact_reports` — informes institucionales;
- `audit_events` — auditoría;
- `subscription_plans` / `organization_subscriptions` / `organization_modules` — planes y
  módulos habilitados;
- `schema_migrations` — control de versiones del esquema.

El aislamiento entre organizaciones es real: un administrador de una no ve los datos de
otra. Está verificado.

---

## 3. Qué se puede hacer con la plataforma

### 3.1 Centro de Comando

La pantalla principal. Tiene cuatro zonas, y las tres primeras se pliegan para darle más
espacio al mapa:

**Indicadores.** Cuatro medidores con su objetivo: tiempo de detección (meta: menos de 5
minutos), precisión del motor de IA (85% o más), reportes válidos (70% o más) y reducción
del tiempo de respuesta (40%). Se pintan en verde cuando cumplen y en amarillo cuando no.

**Inteligencia Terrestre.** Condiciones en vivo de Open-Meteo y CAMS para la coordenada del
centro de monitoreo: temperatura y sensación térmica, humedad ambiente y de suelo, viento
con dirección y ráfaga, PM2.5 y PM10, y aerosoles. Cada métrica tiene su miniserie de
tendencia. La insignia indica si el dato es «en vivo» o de «caché».

**Mapa operacional.** Leaflet con el límite provincial dibujado. Muestra nodos en línea,
focos satelitales, alertas críticas y reportes ciudadanos, cada uno con su color. Permite
elegir la base (OpenStreetMap o control oscuro) y superponer capas de Copernicus. Al plegar
los paneles vecinos el mapa se expande y se reencuadra solo.

**Alertas priorizadas.** Cada alerta muestra su severidad, el porcentaje de confianza (verde
si supera 85%, amarillo si supera 60%) y las fuentes que la sustentan. Sobre cada una se
puede **confirmar** (es real), **descartar** (falso positivo) o **escalar** (elevarla). Toda
acción queda registrada.

### 3.2 Fuego y humo

Módulo licenciable. Combina focos térmicos, contexto meteorológico y registro de
comunicaciones, con lenguaje deliberadamente claro: responde «¿hay un incendio confirmado?»
con «no con estos datos solamente» y explica por qué. El selector de capas del mapa ofrece
únicamente «Área quemada», que es la que corresponde al módulo.

### 3.3 Plagas forestales

Módulo licenciable, orientado al norte de la provincia (San Antonio y General Manuel
Belgrano). Integra contexto meteorológico, índices satelitales NDVI y de humedad,
recorridas, trampas y reportes. Aporta contexto y trazabilidad; no identifica una plaga por
sí mismo. Sus capas de mapa son «Vegetación NDVI» y «Humedad».

### 3.4 Alerta IA (Observatorio SpaceAI)

El análisis asistido por IA. Reúne telemetría por dispositivo, contexto de Open-Meteo,
CAMS y GloFAS, focos de NASA FIRMS, un gemelo digital del territorio y un índice de amenaza.

Ese índice, el **Health Threat Index**, va de R0 a R5:

| Nivel | Significado |
|---|---|
| R0 | sin amenaza |
| R1 | baja |
| R2 | moderada |
| R3 | elevada — umbral típico de alerta operativa |
| R4 | alta |
| R5 | crítica |

El administrador define desde qué nivel se activan alertas automáticas; por defecto R3.

El módulo redacta además mensajes preventivos listos para WhatsApp, Telegram, medios u
organismos. **El envío siempre queda bajo revisión humana** y se registra en auditoría.

### 3.5 Dispositivos

Inventario de nodos: identificador, ubicación, última telemetría y cuáles están en línea.
Los nodos ESP32 publican por MQTT y aparecen en el mapa en tiempo real.

### 3.6 Reglas

El motor de automatización. Se define una condición —variable, operador, umbral y ventana
de tiempo— y qué severidad y acciones dispara. Las condiciones se combinan con `Y` u `O`, y
una regla puede exigir confirmación satelital antes de disparar.

### 3.7 Reportes ciudadanos

La página `/reportar` es **pública**: no hace falta cuenta. Se elige territorio y tipo de
incidente (humo, incendio, inundación, vertido u otro), se describe lo observado, se puede
adjuntar una foto de hasta 8 MB, se comparte la ubicación —que debe estar dentro de
Misiones— y se acepta el tratamiento de datos.

El reporte se cruza con sensores y satélite para su validación, y la organización
destinataria decide.

### 3.8 Informes

Genera documentos formales. Se elige período y destinatario (organización, municipio,
programa u organismo, inversor, aseguradora o auditoría) y el sistema consolida
dispositivos, alertas, severidad, tiempos de respuesta y reportes. Se agrega un resumen y
recomendaciones, y se exporta a PDF o CSV.

También se puede publicar con un **enlace público revocable**, para compartir sin dar
acceso a la plataforma.

### 3.9 Admin Core

Solo para administradores de la organización: usuarios y roles, datos de la organización,
geocercas PostGIS, fuentes ambientales y de SpaceAI, dispositivos, reglas y auditoría.
Incluye una bandeja de mensajes que registra cada inicio de sesión con su contexto e IP
anonimizada.

### 3.10 Consola de plataforma

Ruta oculta `/plataforma`, para el administrador general de EcoNexo. No se publica en el
menú, ni en el mapa del sitio, ni en la documentación de la API.

La seguridad **no** depende de que la dirección sea difícil de adivinar: todos los
endpoints `/platform/*` exigen sesión válida, rol `admin`, organización activa y correo
incluido en `PLATFORM_ADMIN_EMAILS`.

Permite ver todas las organizaciones y usuarios, buscar, cambiar roles, dar de baja
lógicamente, restablecer contraseñas temporales con cambio obligatorio, y suspender o
reactivar organizaciones. Ver `ADMIN_GENERAL_OCULTO.md`.

### 3.11 EcoBot

Asistente flotante disponible en toda la plataforma. Responde sobre módulos, cómo reportar,
alertas, niveles R0–R5, informes, dispositivos, reglas, planes y acceso.

Funciona con una base de conocimiento local: **sin llamadas externas, sin costo y sin
conexión**. Está preparado para conectarle un modelo de lenguaje más adelante —
`resolveAnswer()` es el único punto de resolución.

### 3.12 Aplicación móvil

Expo y React Native, para Android e iOS. Tiene inicio, Fuego y humo, Alerta IA, reportes
con foto y ubicación, y la cuenta. Usa las mismas credenciales que la web.

### 3.13 Planes

De menor a mayor alcance: Sandbox, Diagnóstico, Piloto, Municipal, Provincia/Pro,
Enterprise y Academia. Cada suscripción gestiona solicitud, aprobación, vencimiento,
consumo y módulos habilitados. Fuego y humo y Plagas forestales pueden requerir plan.

---

## 4. Cómo levantarlo

### Requisitos

Docker Desktop con el motor corriendo. Nada más: todo lo demás va en contenedores.

### Puesta en marcha

```bash
cp .env.example .env
docker compose -p econexo-fixed up -d --build
docker compose -p econexo-fixed run --rm api python -m app.migrate --baseline-existing
docker compose -p econexo-fixed run --rm api python -m app.seed
```

> **Usá siempre `-p econexo-fixed`.** Si existe otra copia del repositorio en la máquina,
> comparte el nombre de proyecto de Compose y las dos terminan peleando por los mismos
> contenedores, volúmenes y puertos. Pasó, y dejó la base con migraciones mezcladas.

La tercera línea hace falta solo la primera vez: la imagen de PostGIS ejecuta las
migraciones al inicializar el volumen, y `--baseline-existing` registra ese estado en el
historial.

Después conviene cargar el límite provincial oficial, o las validaciones territoriales
quedan corridas en los bordes:

```bash
curl -X POST http://localhost:8000/territory/sync-georef \
     -H "Authorization: Bearer <token-de-admin>"
```

### Direcciones

| Qué | Dónde |
|---|---|
| Aplicación | http://localhost:3000 |
| Documentación de la API | http://localhost:8000/docs |
| Consola de MinIO | http://localhost:9090 |
| Reporte ciudadano (público) | http://localhost:3000/reportar |

### Credenciales de demostración

Las crea `app.seed`. Contraseña `econexo123` en todas.

| Rol | Correo | Organización |
|---|---|---|
| admin | `admin@misiones.econexo.ar` | Municipalidad de Posadas — 12 nodos |
| operador | `operador@misiones.econexo.ar` | Municipalidad de Posadas |
| admin | `admin@corredor-yaboti-demo.econexo.ar` | Corredor Verde Yabotí — 14 nodos |
| operador | `operador@corredor-yaboti-demo.econexo.ar` | Corredor Verde Yabotí |
| admin | `admin@red-energetica-obera-demo.econexo.ar` | Red Energética Oberá — 12 nodos |
| operador | `operador@red-energetica-obera-demo.econexo.ar` | Red Energética Oberá |

El seed carga 3 organizaciones, 38 nodos, 30 días de lecturas con ciclos diurnos y
anomalías inyectadas, reglas precargadas y alertas históricas. Es idempotente: se puede
volver a correr.

### Comandos habituales

```bash
docker compose -p econexo-fixed logs -f          # seguir los registros
docker compose -p econexo-fixed ps               # estado de los servicios
docker compose -p econexo-fixed down             # detener (conserva los datos)
docker compose -p econexo-fixed down -v          # detener y BORRAR los volúmenes

docker compose -p econexo-fixed --profile sim up -d simulator   # simulador ESP32
docker compose -p econexo-fixed run --rm --no-deps web npm run typecheck
```

> Al cambiar código de Python hay que **reconstruir**, no solo recrear:
> `docker compose -p econexo-fixed up -d --build api`. Con `--force-recreate` a secas el
> contenedor se rehace desde la imagen vieja y el cambio no tiene efecto.

### Los tests de la API

Hoy `make test-api` **no funciona**, por dos motivos independientes: `apps/api/.dockerignore`
excluye la carpeta `tests`, y `pytest` está en `requirements-dev.txt` y no en
`requirements.txt`. Mientras tanto, montando el repositorio:

```bash
docker run --rm --network econexo-fixed_default \
  -v "<ruta-del-repo>:/repo" -w /repo/apps/api \
  -e POSTGRES_HOST=postgis -e POSTGRES_USER=econexo \
  -e POSTGRES_PASSWORD=<clave> -e POSTGRES_DB=econexo \
  --user root econexo-fixed-api \
  sh -c "pip install -q -r requirements-dev.txt; python -m pytest -q"
```

Son 70 pruebas y pasan todas.

---

## 5. Configuración

Todo se controla por variables de entorno. `.env.example` es la referencia completa; las
que más se tocan:

| Variable | Para qué |
|---|---|
| `JWT_SECRET` | Firma de las sesiones. **Cambiar en producción.** |
| `LOGIN_ATTEMPT_LIMIT` | Intentos de acceso permitidos (10 por defecto) |
| `LOGIN_ATTEMPT_WINDOW_SECONDS` | Ventana de esos intentos (900 por defecto) |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Activa el acceso con Google |
| `NASA_FIRMS_KEY` | Focos térmicos reales |
| `COPERNICUS_CLIENT_ID` / `_SECRET` | Capas satelitales |
| `PLATFORM_ADMIN_EMAILS` | Quién puede entrar a `/plataforma` |
| `RUN_MIGRATIONS_ON_START` | Migrar al arrancar (útil en Render Free) |

En una demostración con varias personas detrás de la misma conexión conviene subir
`LOGIN_ATTEMPT_LIMIT`: el contador es por dirección de origen, así que entre todas agotan
el límite y se bloquean entre sí.

Las variables `NEXT_PUBLIC_*` se incorporan **durante el build**. Cambiarlas exige
reconstruir el frontend; en Render, con `Clear build cache & deploy`.

---

## 6. Seguridad

Lo que ya está resuelto:

- contraseñas con Argon2, nunca en texto plano;
- sesiones firmadas con expiración;
- aislamiento entre organizaciones, verificado;
- validación territorial en web, API, PostGIS, satélite, informes y móvil;
- fotos en almacenamiento privado, servidas con enlaces firmados de corta duración;
- auditoría de acciones e inicios de sesión con IP anonimizada;
- rutas de plataforma excluidas de la documentación pública y marcadas `noindex`.

Lo que **sigue abierto**, con su detalle en `TAREAS_INTEGRACION_2026-08-18.md`:

- **el límite de intentos se puede evadir.** `rate_limit.py` confía en la cabecera
  `X-Forwarded-For` sin validarla: cualquiera puede enviarla y estrenar contador en cada
  petición. Hacerlo configurable no arregla esto;
- **no hay bloqueo de cuenta** ante fuerza bruta dirigida a un usuario concreto;
- **`/orgs/public` devuelve todas las organizaciones** sin autenticación;
- **el contenedor `anomaly` corre como root**;
- **faltan las cabeceras de seguridad del frontend**, incluida la política de contenido.

---

## 7. Despliegue

Está preparado para tres destinos, cada uno con su documentación:

| Destino | Archivo |
|---|---|
| Render | `render.yaml`, `render.production.yaml`, `RENDER_DEPLOY.md` |
| Cloudflare | `CLOUDFLARE.md` |
| Kubernetes | `k8s/` |

La correspondencia con AWS, si se migra: PostGIS → RDS con PostGIS · Mosquitto → AWS IoT
Core · MinIO → S3 · API, web y servicios → EKS o ECS · simulador y anomalías → Lambda con
EventBridge.

---

## 8. Dónde seguir leyendo

| Archivo | Contenido |
|---|---|
| `README.md` | Referencia de comandos y despliegue |
| `TAREAS_INTEGRACION_2026-08-18.md` | Trabajo aplicado, verificaciones y pendientes |
| `ADMIN_GENERAL_OCULTO.md` | Consola de plataforma |
| `SECURITY.md` | Política de seguridad |
| `CHANGELOG.md` | Historial de versiones |
| `MANUAL_USUARIO_ECONEXO.html` | Manual para la persona usuaria final |
| `AUDIT.md` | Auditoría del sistema |
| `docs/` | Documentación técnica por tema |

### Mapa del código

```
apps/
  api/     FastAPI. app/routers/ tiene un archivo por área
           (auth, alerts, devices, reports, rules, impact_reports,
            territory, platform, subscriptions, copernicus, satellite…)
  web/     Next.js App Router.
           app/       una carpeta por ruta
           components/ los paneles de cada módulo
           app/lib/   cliente de la API, territorio, SpaceAI, inteligencia terrestre
  mobile/  Expo / React Native

services/  anomaly · ingest · notify · satellite
infra/db/migrations/   el esquema, numerado y en orden
firmware/  esp32_node.ino
simulator/ nodos simulados, para probar sin hardware
k8s/       manifiestos de Kubernetes
```
