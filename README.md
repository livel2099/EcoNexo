# EcoNexo — MVP

**Inteligencia bioclimatica activa. Un sistema de decision en tiempo real que reduce el impacto ambiental antes de que ocurra.**

> "El mercado ambiental no falla por falta de datos. Falla por falta de decision en tiempo real."

EcoNexo convierte flujos masivos de datos (sensores IoT + satelite + reportes ciudadanos) en **alertas automatizadas, prioritarias y accionables**. Cada pantalla responde: *¿que esta pasando AHORA y que accion tomo?*

---

## Arquitectura

```
                         ┌──────────────── Next.js (apps/web) ────────────────┐
                         │  Centro de Comando (dashboard)  ·  PWA ciudadana    │
                         └───────────▲───────────────────────────▲────────────┘
                                REST │ WebSocket            REST  │ (reportes)
                         ┌───────────┴───────────────────────────┴────────────┐
                         │            FastAPI core (apps/api)                  │
                         │  auth · orgs · devices · alerts · rules · reports   │
                         │  kpis · satellite · WS feed · pipeline correlacion  │
                         └── ▲ ──────── ▲ ─────── ▲ ──────── ▲ ─────── ▲ ──────┘
                             │          │         │          │         │
              anomaly-service│   ingest │  notify │ satellite│      PostGIS
              (PyTorch)      │  (Node)  │ (Node)  │ (OpenCV) │   (PostgreSQL+PostGIS)
                score IA     │          │         │  FIRMS   │
                             │          ▼         ▼          │
                             │       ┌──── Mosquitto (MQTT bus) ────┐
                             │       │ econexo/{org}/{dev}/telemetry│
                             └───────┤ econexo/internal/{org}/*     │◄── simulator + ESP32
                                     └──────────────────────────────┘
                                            MinIO (S3)  ── fotos de reportes
```

### Monorepo
| Path | Rol | Stack |
|------|-----|-------|
| `apps/api` | API core del sistema | Python + **FastAPI** |
| `apps/web` | Dashboard + PWA ciudadana | **Next.js** (App Router, TS) + **Leaflet** |
| `services/ingest` | Consumidor MQTT -> persiste/republica telemetria | **Node.js** |
| `services/notify` | Despacho de notificaciones (in-app real; email/SMS/WhatsApp stub) | **Node.js** |
| `services/anomaly` | Deteccion de anomalias (score IA real) | **PyTorch** |
| `services/satellite` | Vision satelital + ingesta FIRMS | **OpenCV** + NASA FIRMS |
| `simulator` | Emula nodos ESP32 por MQTT (alimenta la demo) | Node.js |
| `firmware` | Sketch ESP32 real (DHT11 + MQ-4) | Arduino/C++ |
| `infra` | DB (PostGIS), Mosquitto | SQL + config |
| `k8s` | Manifiestos por servicio | Kubernetes |

### Stack del dossier — dónde vive cada pieza
- **FastAPI** → `apps/api` (auth, alertas, dispositivos, reportes, reglas). Swagger auto en `/docs`.
- **Node microservicios** → `services/ingest` + `services/notify` (2 servicios independientes).
- **PostgreSQL + PostGIS** → `infra/db` — tipos `GEOGRAPHY(Point/Polygon)`, indices GiST, `ST_DWithin` (correlacion de nodos cercanos), `ST_Contains` (zonas de riesgo).
- **PyTorch** → `services/anomaly` — autoencoder entrenado sobre las series del seeder; emite score de confianza real (no hardcodeado).
- **OpenCV + FIRMS** → `services/satellite` — cliente NASA FIRMS real + procesamiento de raster termico (umbralizacion + morfologia).
- **MQTT + ESP32** → `firmware/esp32_node.ino` + `simulator` + broker Mosquitto.
- **Docker / K8s** → `docker-compose.yml` + `/k8s`.
- **S3** → MinIO local (fotos de reportes).

---

## Setup (desarrollo local)

Requisitos: **Docker** + **Docker Compose v2**.

```bash
cp .env.example .env            # ajustar secretos (JWT_SECRET, etc.)
docker compose up -d --build    # levanta TODO el ecosistema
docker compose run --rm api python -m app.seed    # datos semilla (o: make seed)
```

Abrir:
- **Dashboard (Centro de Comando):** http://localhost:3000  → login `admin@forestandes.econexo.ar` / `econexo123`
- **PWA ciudadana:** http://localhost:3000/reportar
- **API + Swagger:** http://localhost:8000/docs
- **MinIO consola:** http://localhost:9090

Usuarios semilla (password `econexo123` en las 3 orgs): `admin@<slug>.econexo.ar`, `operador@<slug>.econexo.ar`
(slugs: `muni-villa-lago`, `forestandes`, `patagonia-energia`).

### Demo end-to-end en vivo
```bash
make demo          # o: docker compose run --rm api python -m app.demo
```
Dispara la historia: **satelite detecta foco → nodos ESP32 confirman → ciudadano reporta → correlacion espacial + score IA = alerta critica (~92% confianza) → operador confirma → KPI de respuesta se actualiza.** Se ve en vivo en el dashboard (feed WebSocket).

Para telemetria continua en tiempo real:
```bash
make sim           # arranca el simulador de nodos ESP32 (perfil sim)
```

### Tests
```bash
make test          # pipeline de correlacion espacial + motor de reglas
```

---

## Mapeo local → AWS (produccion)

| Local (compose) | AWS | Notas |
|-----------------|-----|-------|
| `postgis` | **RDS PostgreSQL + PostGIS** | mismo esquema `infra/db` |
| `mosquitto` | **AWS IoT Core** | topics MQTT identicos; certs X.509 por device |
| `minio` | **S3** | interfaz S3-compatible (boto3), solo cambia endpoint/creds |
| `api` / `web` / `services/*` | **EKS** (ver `/k8s`) o ECS | imagenes Docker ya listas |
| `satellite` poll / `simulator` | **Lambda + EventBridge** | cron de ingesta FIRMS como Lambda programada |
| `.env` | **Secrets Manager / SSM** | cero secretos hardcodeados |

Deploy a EKS: aplicar los manifiestos de `/k8s` (deployment + service + configmap por servicio).

---

## Qué es real y qué es fixture

**Real y funcional:**
- Esquema PostGIS con queries espaciales reales (`ST_DWithin`, `ST_Contains`, indices GiST).
- FastAPI core completo con OpenAPI, JWT (argon2id), scoping multi-org y roles.
- Autoencoder PyTorch entrenado sobre las series del seeder → score de anomalia real.
- Procesamiento OpenCV de raster termico (umbralizacion + morfologia + contornos).
- Cliente NASA FIRMS real (endpoint CSV). Ingesta programada al pipeline.
- Bus MQTT (Mosquitto) real; ingest/notify como microservicios Node independientes.
- Correlacion multi-fuente + motor de reglas (con tests).
- Simulador de nodos ESP32 + firmware Arduino listo para flashear.

**Fixture / stub documentado:**
- **NASA FIRMS:** si `NASA_FIRMS_KEY` esta vacia, usa `services/satellite/fixtures/firms_sample.json` (respuesta grabada con formato real). Key gratuita: https://firms.modaps.eosdis.nasa.gov/api/
- **Raster satelital OpenCV:** el MVP sintetiza un raster termico de muestra con focos calientes (misma pipeline que un GeoTIFF real de Copernicus).
- **Copernicus:** cliente FIRMS implementado; Copernicus queda como extension documentada (mismo patron de ingesta).
- **email / SMS / WhatsApp** (`services/notify/adapters.js`): stub que loguea la intencion de envio. In-app es real (tabla `notifications`). Prod → SES / SNS / WhatsApp Cloud API.

---

## Los 4 KPIs del producto (en vivo)
1. **Tiempo de deteccion** de incidentes anomalos — objetivo **< 5 min** (latencia lectura→alerta).
2. **Precision del motor IA** — objetivo **85%+** (confirmadas / (confirmadas + descartadas)).
3. **Tasa de reportes ciudadanos validos** — objetivo **70%+** (verificados / moderados).
4. **Reduccion del tiempo de respuesta institucional** — objetivo **-40%** vs baseline configurable por org.

---

## Seguridad (dia 0)
- Cero secretos hardcodeados. `.env.example` por servicio; `.env` en `.gitignore`.
- Credenciales MQTT y tokens hasheados con **argon2id** (mostrados una sola vez).
- Validacion **Pydantic** (FastAPI) y tipado estricto TS. CORS restrictivo.
- JWT firmado; scoping de datos por organizacion en cada query.

---

## Roadmap
- **Fase 1 (este MVP):** ecosistema funcional en entornos de prueba — `docker compose up` levanta todo con datos semilla y demo.
- **Fase 2:** modelos base productivos (incendios forestales / anomalias hidricas) con reentrenamiento continuo; Copernicus; canales de notificacion reales; app store.
- **Fase 3:** multi-tenant white-label a escala, marketplace de reglas, federacion de sensores heredados.
 