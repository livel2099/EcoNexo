# EcoNexo — Tablero de Tareas

> Estado vivo del MVP. `[x]` hecho · `[~]` en progreso · `[ ]` pendiente.
> Última actualización: 2026-07-06 (sesión 1 — runtime validado)

## Fase 1 — Ecosistema funcional (Sem 0-8)

### Sem 1-2 · Arquitectura de datos y ecosistema
- [x] Monorepo scaffolded (`apps/`, `services/`, `firmware/`, `simulator/`, `k8s/`, `infra/`)
- [x] Esquema PostGIS completo (GEOGRAPHY, GiST, ST_DWithin/ST_Contains, `nearby_devices`)
- [x] `docker-compose.yml` con todos los servicios (validado con `config`)
- [x] Esquema de topics MQTT + broker Mosquitto
- [x] `.env.example` por servicio + `.gitignore` (secretos fuera)
- [x] Makefile (up/seed/demo/sim/test)

### Sem 3-4 · Dashboard operativo + APIs del núcleo
- [x] FastAPI core: config, db pool, security (argon2+JWT)
- [x] Routers: auth, orgs, devices, alerts, rules, reports, kpis, satellite
- [x] Pipeline de correlación multi-fuente (score real)
- [x] Feed WebSocket + puente MQTT
- [x] Seeder (3 orgs, ~38 nodos, 30 días de historial, anomalías inyectadas)
- [x] Dashboard "Centro de Comando" (banner, 4 KPIs, mapa Leaflet, alertas priorizadas)
- [x] OpenAPI/Swagger (auto FastAPI)

### Sem 5-6 · Redes y flujos satelitales
- [x] Cliente NASA FIRMS (real + fixture grabado)
- [x] Procesamiento OpenCV (raster térmico, umbralización + morfología)
- [x] Ingesta programada satélite -> pipeline de alertas
- [ ] Copernicus (documentado como extensión; mismo patrón)

### Sem 7-8 · App ciudadana + motor de alertas
- [x] Motor de reglas (CRUD + evaluación AND/OR + require_satellite)
- [x] Reglas precargadas (incendio forestal / anomalía hídrica / aire)
- [x] anomaly-service PyTorch (autoencoder, score real)
- [x] PWA ciudadana mobile-first (`/reportar`)
- [x] Filtro inteligente de reportes (correlación IA + reputación dinámica)
- [x] Microservicios Node (ingest + notify con adapters stub)
- [x] Simulador de nodos ESP32 + firmware Arduino real
- [x] Tests: correlación espacial + motor de reglas

### Infra / entrega
- [x] Manifiestos K8s (namespace, config, api, web, servicios, cronjob satélite)
- [x] README maestro (arquitectura, setup, mapeo local->AWS, real vs fixture, roadmap)

## Runtime — VALIDACIÓN EN VIVO (✅ COMPLETA)
- [x] Arrancar Docker Desktop daemon
- [x] `docker compose up -d --build` — todo el ecosistema levanta (8 servicios)
- [x] `make seed` — 3 orgs, 38 nodos, 82k lecturas, reglas, KPIs
- [x] Verificar `/health` de api, anomaly, notify — OK
- [x] `make test` — 11/11 tests pasan dentro del contenedor
- [x] `make demo` — historia end-to-end: alerta crítica 92% multi-fuente
- [x] Dashboard HTTP 200; API responde login/KPIs/devices/alerts/rules
- [x] Pipeline satélite: FIRMS fixture -> OpenCV (3 zonas) -> ingesta -> 2 alertas
- [x] anomaly-service PyTorch entrenado (6 variables), score real anómalo>normal
- [x] Bugs de runtime arreglados: email-validator, 204 body, SRID mixto, fechas fixture
- [ ] PWA `/reportar` envía reporte real y se correlaciona (validar en navegador)
- [ ] `make sim` — telemetría en tiempo real por WebSocket (validar en navegador)


## UI — Pulido (✅ hecho esta sesión)
- [x] Navegación entre vistas: Centro de Comando · Dispositivos · Reglas · Reportes
- [x] Detalle de nodo: drawer con series temporales (sparkline SVG), batería, RSSI, ubicación
- [x] CRUD visual de reglas (crear/pausar/borrar sin tocar código, modal con condiciones)
- [x] Backoffice de moderación de reportes (scores correlación IA + reputación visibles, verificar/rechazar)
- [x] KPIs con barras de progreso vs objetivo
- [x] Alertas: barra de confianza, tiempo relativo, pills coloreadas por fuente
- [x] Leyenda del mapa + barra de feed "EN VIVO"
- [x] Override de dev (bind-mount + polling) para hot-reload sin rebuild
- [ ] Selector de organización / white-label (color primario por org)
- [ ] Notificaciones in-app en el header (campana)
- [ ] Capas del mapa conmutables con checkboxes


## Backlog / Fase 2+
- [ ] Copernicus real
- [ ] Canales de notificación reales (SES/SNS/WhatsApp)
- [ ] Reentrenamiento continuo del modelo
- [ ] mypy estricto en CI + lint front
