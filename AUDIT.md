# EcoNexo — Auditoría de Software

> Registro de bugs, riesgos de seguridad y deuda técnica para control total del MVP.
> Fecha: 2026-07-07 · Versión: MVP Fase 1 · Auditor: revisión de código + runtime.

## Cómo leer este documento
- **Severidad:** 🔴 Crítica · 🟠 Alta · 🟡 Media · 🔵 Baja
- **Estado:** ✅ Resuelto · 🛠️ Mitigado/parcial · ⬜ Abierto
- Cada hallazgo tiene: ubicación, impacto, y recomendación.

> ⚠️ Contexto: es un **MVP de demo**. Varios ítems son aceptables para demo pero
> **bloqueantes para producción**. Están marcados como tal.

---

## Resumen ejecutivo

| # | Área | Severidad | Estado | Título |
|---|------|-----------|--------|--------|
| S1 | Seguridad | 🔴 | ✅ | Credenciales por defecto en el login |
| S2 | Seguridad | 🔴 | ⬜ | `/satellite/ingest` sin autenticación |
| S3 | Seguridad | 🟠 | ⬜ | `notify` expone notificaciones sin auth (IDOR por org_id) |
| S4 | Seguridad | 🟠 | ⬜ | Sin rate limiting en ingesta ni en endpoint público de reportes |
| S5 | Seguridad | 🟠 | 🛠️ | Secretos por defecto (JWT, DB, MQTT) en `.env.example` |
| S6 | Seguridad | 🟡 | 🛠️ | MQTT con acceso anónimo (broker dev) |
| S7 | Seguridad | 🟡 | ⬜ | Reputación ciudadana manipulable (token controlado por cliente) |
| S8 | Seguridad | 🟡 | ⬜ | Upload de fotos sin límite de tamaño ni validación de contenido |
| S9 | Seguridad | 🔵 | ⬜ | CORS y ausencia de HTTPS (dev) |
| C1 | Correctitud | 🟡 | ⬜ | KPI tiempo de detección infla por diseño del seeder |
| C2 | Correctitud | 🟡 | ⬜ | Score de anomalía inconsistente entre pipeline y consulta directa |
| C3 | Correctitud | 🔵 | ⬜ | `correlation_score` de reportes se calcula antes de existir la alerta |
| P1 | Performance | 🟠 | ⬜ | N+1 de queries al listar alertas |
| P2 | Performance | 🟡 | ⬜ | `publish()` abre una conexión MQTT nueva por mensaje |
| P3 | Performance | 🔵 | ⬜ | Sin paginación en listados (alerts/devices/reports) |
| Q1 | Calidad | 🟡 | ⬜ | Cobertura de tests mínima (solo core, sin integración API) |
| Q2 | Calidad | 🟡 | ⬜ | Sin CI/CD ni mypy/lint en pipeline |
| Q3 | Calidad | 🔵 | ⬜ | Web sin manejo de expiración de token (401 no redirige a login) |

---

## Seguridad

### S1 · 🔴 ✅ Credenciales por defecto en el login
- **Dónde:** `apps/web/app/login/page.tsx`
- **Problema:** los campos email/password venían pre-rellenados con `admin@forestandes.econexo.ar` / `econexo123`.
- **Riesgo:** cualquiera que abra la URL entra con un click; credenciales reales expuestas en el bundle JS.
- **Resuelto:** campos vacíos + `autoComplete="off"` + placeholders. Se mantiene solo un hint de demo textual.
- **Pendiente prod:** eliminar por completo el hint y forzar cambio de password en primer login.

### S2 · 🔴 ⬜ `/satellite/ingest` sin autenticación
- **Dónde:** `apps/api/app/routers/satellite.py:34` (`async def ingest`)
- **Problema:** el endpoint que inserta detecciones satelitales y **dispara alertas** no tiene `Depends(current_user)`. Está pensado como interno (lo llama `satellite-service`) pero queda expuesto en la API pública.
- **Riesgo:** un atacante puede inyectar focos de calor falsos y generar alertas de incendio (envenenamiento del sistema de decisión — justo lo que el producto promete evitar).
- **Recomendación:** proteger con un token de servicio (header `X-Service-Token`) o mover a red interna / API gateway. Mínimo: un secreto compartido validado por dependencia.

### S3 · 🟠 ⬜ `notify` expone notificaciones sin auth (IDOR)
- **Dónde:** `services/notify/index.js:45` (`GET /notifications/{org_id}`)
- **Problema:** devuelve las notificaciones de cualquier organización con solo conocer/adivinar su `org_id` (UUID). Sin token.
- **Riesgo:** fuga de información entre organizaciones (IDOR — Insecure Direct Object Reference).
- **Recomendación:** validar el JWT y que el `org_id` del token coincida con el de la URL, igual que hace la API core.

### S4 · 🟠 ⬜ Sin rate limiting
- **Dónde:** `apps/api` (global), `POST /reports` (público), `services/ingest` (MQTT).
- **Problema:** el plan de negocio pedía explícitamente *"rate limiting en ingesta"*. No está implementado en ningún punto.
- **Riesgo:** DoS por flood de reportes/telemetría; abuso del endpoint público de reportes; saturación del pipeline de correlación.
- **Recomendación:** `slowapi` en FastAPI (limitar `/reports` y `/auth/login`), throttle por device en `ingest`, y límite de mensajes por topic en Mosquitto.

### S5 · 🟠 🛠️ Secretos por defecto
- **Dónde:** `.env.example` (raíz y por servicio).
- **Problema:** `JWT_SECRET=change_me_dev_secret`, `POSTGRES_PASSWORD=econexo_dev_pw`, MQTT sin credenciales.
- **Mitigado:** están en `.env.example` (plantilla), el `.env` real está en `.gitignore` y NO se subió al repo. Documentado en README.
- **Pendiente prod:** generar secretos reales (`openssl rand -hex 32`) y gestionarlos con AWS Secrets Manager / SSM. Validar en el arranque que no queden los valores por defecto.

### S6 · 🟡 🛠️ MQTT anónimo
- **Dónde:** `infra/mosquitto/mosquitto.conf` (`allow_anonymous true`)
- **Problema:** el broker acepta cualquier conexión sin credenciales.
- **Mitigado:** es config de dev; las credenciales MQTT por dispositivo YA se generan y hashean (argon2) en el alta de device — falta activarlas en el broker.
- **Pendiente prod:** `allow_anonymous false` + password_file o certs X.509 (mapea a AWS IoT Core con policies por device).

### S7 · 🟡 ⬜ Reputación ciudadana manipulable
- **Dónde:** `apps/api/app/routers/reports.py` (`citizen_token` viene del cliente)
- **Problema:** el token del ciudadano lo genera y envía la PWA (`crypto.randomUUID()` en localStorage). Un atacante puede rotar tokens para evadir el score reputacional o inflar reportes.
- **Riesgo:** inyección de reportes falsos (riesgo que el propio plan identifica como a mitigar).
- **Recomendación:** vincular reputación a identidad más fuerte (device fingerprint + rate limit por IP, o login ciudadano opcional). El cruce con correlación IA ya mitiga parcialmente.

### S8 · 🟡 ⬜ Upload de fotos sin límites
- **Dónde:** `apps/api/app/routers/reports.py` (`photo: UploadFile`), `storage.py`
- **Problema:** no hay límite de tamaño de archivo ni validación real de tipo MIME (se confía en `content_type` del cliente).
- **Riesgo:** subida de archivos enormes (DoS de almacenamiento) o contenido no-imagen.
- **Recomendación:** limitar tamaño (p.ej. 8MB), validar magic bytes, y re-encodear la imagen server-side.

### S9 · 🔵 ⬜ CORS / HTTPS
- **Dónde:** `apps/api/app/main.py` (CORS), infra.
- **Problema:** CORS configurable pero permisivo en métodos/headers; sin TLS en dev.
- **Recomendación prod:** CORS restrictivo al dominio real, TLS terminado en el ALB/ingress, HSTS.

---

## Correctitud

### C1 · 🟡 ⬜ KPI de tiempo de detección inflado
- **Dónde:** `apps/api/app/routers/kpis.py` (KPI1) + `apps/api/app/seed.py` (`_seed_history`)
- **Problema:** el KPI muestra ~1560s (26 min), muy por encima del objetivo de 5 min. No es un bug de cálculo: el seeder crea alertas históricas con `detected_at` desfasado respecto a la última lectura horaria (gap de hasta ~1h). El cálculo es correcto; los datos semilla lo distorsionan.
- **Impacto:** da una impresión negativa en la demo (KPI en rojo).
- **Recomendación:** en el seeder, alinear `detected_at` a segundos después de la lectura disparadora, o excluir el histórico sintético del cálculo del KPI de detección.

### C2 · 🟡 ⬜ Score de anomalía inconsistente
- **Dónde:** `services/anomaly/app/model.py` (calibración sigmoide)
- **Problema:** la misma variable extrema da 1.00 vía el pipeline de la demo pero ~0.39 en una consulta directa `/score` con otra hora. La calibración depende de `err_mean/err_std` que se contaminan con las anomalías inyectadas durante el entrenamiento.
- **Impacto:** el score es direccional (anómalo > normal) pero poco estable.
- **Recomendación:** entrenar solo con datos etiquetados como normales, o usar percentiles robustos (p95/p99) del error en vez de media/desvío.

### C3 · 🔵 ⬜ `correlation_score` de reportes prematuro
- **Dónde:** `apps/api/app/routers/reports.py` (`_correlation_score`)
- **Problema:** el score cuenta alertas activas dentro de 2km al momento de crear el reporte; si el reporte llega antes que la alerta, cuenta 0 aunque luego se correlacione.
- **Recomendación:** recalcular el score de forma asíncrona cuando aparecen nuevas alertas/detecciones cercanas.

---

## Performance

### P1 · 🟠 ⬜ N+1 queries al listar alertas
- **Dónde:** `apps/api/app/routers/alerts.py:34-35`
- **Problema:** `list_alerts` hace 1 query para las alertas y luego 1 query por cada alerta para traer sus fuentes (bucle `for r in rows`). Con 20 alertas = 21 queries.
- **Impacto:** latencia creciente del panel principal (se refresca cada 15s + en cada evento WS).
- **Recomendación:** un solo query con `JOIN` + `json_agg` de `alert_sources`, o `LEFT JOIN LATERAL`.

### P2 · 🟡 ⬜ Conexión MQTT por mensaje
- **Dónde:** `apps/api/app/ws.py:82` (`publish`)
- **Problema:** cada publicación al bus abre y cierra una conexión MQTT nueva (`async with aiomqtt.Client(...)`).
- **Impacto:** overhead por alerta/reporte; presión sobre el broker bajo carga.
- **Recomendación:** mantener un cliente MQTT persistente reutilizable en el proceso (singleton con reconexión).

### P3 · 🔵 ⬜ Sin paginación
- **Dónde:** `alerts.py`, `devices.py`, `reports.py`
- **Problema:** los listados devuelven todo sin `LIMIT/OFFSET`.
- **Recomendación:** paginación por cursor (keyset sobre `detected_at`/`created_at`).

---

## Calidad / Deuda técnica

### Q1 · 🟡 ⬜ Cobertura de tests mínima
- **Dónde:** `apps/api/tests/`
- **Estado:** solo cubren correlación espacial y motor de reglas (el mínimo que pedía el plan). Sin tests de integración de la API, ni de los microservicios Node, ni del pipeline satélite.
- **Recomendación:** tests de integración con `httpx.AsyncClient` + una DB de test; smoke tests de ingest/notify.

### Q2 · 🟡 ⬜ Sin CI/CD
- **Problema:** `mypy` (strict) y linters configurados pero no se corren automáticamente. No hay GitHub Actions.
- **Recomendación:** workflow que corra `pytest`, `mypy`, `ruff` y `tsc --noEmit` en cada push. Build de imágenes en CI.

### Q3 · 🔵 ⬜ Web no maneja expiración de token
- **Dónde:** `apps/web/app/lib/api.ts` + páginas
- **Problema:** si el JWT expira (12h), las llamadas fallan con 401 pero la UI no redirige al login; queda en estado roto.
- **Recomendación:** interceptor que ante 401 limpie sesión y redirija a `/login`.

---

## Fixes aplicados en esta auditoría
- ✅ **S1** — credenciales por defecto removidas del login (`apps/web/app/login/page.tsx`).
- ✅ **UI** — mapa y panel lateral encuadrados en contenedores redondeados con margen (`apps/web/app/globals.css`).

## Prioridad recomendada para la próxima iteración
1. **S2** (satellite/ingest sin auth) — crítico, rápido de arreglar.
2. **S3** (IDOR en notify) — alto, rápido.
3. **S4** (rate limiting) — alto, pedido explícito del plan.
4. **P1** (N+1 alertas) — alto impacto en la experiencia de la demo.
5. **C1** (KPI de detección) — mejora la percepción de la demo.

## Nota de higiene de repo
- ✅ `.env` real ignorado y NO subido a GitHub (repo privado).
- ✅ Sin secretos reales en el historial (solo placeholders de dev documentados).
- ⬜ Considerar `git-secrets` o un pre-commit hook que bloquee secretos antes del commit.
