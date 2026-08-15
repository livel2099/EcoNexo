# EcoNexo — Guía de Accesos y Puertos

> Historial y referencia de TODAS las URLs del sistema, qué es cada una y con
> qué credenciales se entra. Fecha: 2026-07-07.

## ⚠️ Concepto clave
EcoNexo NO es una sola página: es un **ecosistema de varios servicios**, cada uno
en su propio **puerto**. Cada servicio tiene su **propio login** (o no tiene).
Usar las credenciales de un servicio en otro **no funciona** — es un error común.

---

## Mapa de accesos

| URL | Qué es | ¿Login? | Credenciales |
|-----|--------|---------|--------------|
| http://localhost:3000 | **Dashboard EcoNexo** (Centro de Comando) — la app principal | Sí, usuarios de la app | ver tabla de abajo |
| http://localhost:3000/reportar | **PWA ciudadana** (reportes) | No, es pública | — |
| http://localhost:8000/docs | **API + Swagger** (documentación interactiva de la API) | No (es documentación) | — |
| http://localhost:9090 | **MinIO** (consola de almacenamiento S3, guarda las fotos) | Sí, credenciales de MinIO | `econexo` / `econexo_dev_pw` |
| http://localhost:8000/health | Health check de la API (JSON) | No | — |
| http://localhost:8200/health | Health check de notify-service | No | — |
| http://localhost:8100/health | Health check de anomaly-service | No | — |

> Puertos internos (no se entra por navegador): PostGIS `5432`, Mosquitto MQTT `1883`.

---

## 1. Dashboard EcoNexo — http://localhost:3000
La aplicación que construimos. Acá se ve el Centro de Comando, dispositivos,
reglas y reportes. **Este es el login que importa para usar el producto.**

Usuarios semilla (los creó el `seed`), password **`econexo123`** en todos:

| Organización | Rol | Email |
|--------------|-----|-------|
| ForestAndes (forestal) | Admin | `admin@forestandes.econexo.ar` |
| ForestAndes (forestal) | Operador | `operador@forestandes.econexo.ar` |
| Municipio Villa del Lago | Admin | `admin@muni-villa-lago.econexo.ar` |
| Municipio Villa del Lago | Operador | `operador@muni-villa-lago.econexo.ar` |
| Patagonia Energía | Admin | `admin@patagonia-energia.econexo.ar` |
| Patagonia Energía | Operador | `operador@patagonia-energia.econexo.ar` |

> El formato del email es `rol@<slug-de-la-org>.econexo.ar`. El slug NO lleva
> espacios. En tu captura escribiste `operador@econexo123 econexo.ar` — eso está
> mal formado y además era para MinIO, no para la app.

---

## 2. PWA ciudadana — http://localhost:3000/reportar
Pública, sin login. Es la app mobile-first donde un vecino carga un reporte
(tipo de incidente, foto, ubicación). No requiere credenciales a propósito.

---

## 3. API + Swagger — http://localhost:8000/docs
NO es una pantalla de login. Es la **documentación interactiva** de todos los
endpoints de la API (generada automáticamente por FastAPI). Sirve para probar
la API y entender los contratos. Para llamar endpoints protegidos desde ahí,
primero se obtiene un token en `POST /auth/login` con un usuario de la tabla de
arriba, y se pega en el botón "Authorize".

---

## 4. MinIO (almacenamiento) — http://localhost:9090
Es la **consola de administración del almacenamiento de objetos** (donde se
guardan las fotos de los reportes ciudadanos). Es una herramienta de
infraestructura, NO parte de la experiencia del usuario final.

- **Usuario:** `econexo`
- **Contraseña:** `econexo_dev_pw`

Estas credenciales salen de `MINIO_ROOT_USER` y `MINIO_ROOT_PASSWORD` en el
archivo `.env` (copiado de `.env.example`). Son DISTINTAS a las de la app.

> Normalmente no necesitás entrar acá. Solo sirve para ver/administrar los
> archivos subidos. La app usa MinIO por detrás automáticamente.

---

## Por qué hay tantos servicios (no es que "creé 3 páginas de más")
El plan de negocio exigía un stack específico y cada pieza corre como su propio
servicio (arquitectura de microservicios, containerizada con Docker):

- **Dashboard (3000)** — lo que ve el operador.
- **API (8000)** — el cerebro: auth, alertas, reglas, KPIs.
- **MinIO (9090)** — almacén de fotos (equivale a AWS S3 en producción).
- **anomaly (8100)** — IA de detección de anomalías (PyTorch).
- **notify (8200)** — despacho de notificaciones.
- Y por detrás: PostGIS (datos), Mosquitto (MQTT), ingest, satellite, simulator.

Las "páginas de login" que viste (3000 y 9090) son de **dos servicios distintos**:
la app y el almacenamiento. Son ambas necesarias, con credenciales separadas por
seguridad.

---

## Nota sobre `eco3.html`
El archivo `Downloads/eco3.html` **no forma parte de EcoNexo**. Es una página de
ChatGPT guardada desde el navegador (su título es "Activar Windows 11" y su
contenido apunta a chatgpt.com). Se puede borrar sin afectar nada.
