# Panel administrativo y ABM/CRUD de EcoNexo

Versión: **2026-07-24**

## 1. Alcance

El panel **Admin Core** centraliza el gobierno de la plataforma por organización. La edición completa incluye ABM/CRUD, control de roles, PostGIS, credenciales de dispositivo, fuentes ambientales y auditoría.

## 2. Roles

| Rol | Lectura | Alta/edición operativa | Bajas sensibles | Administración de usuarios |
|---|---:|---:|---:|---:|
| `visualizador` | sí | no | no | no |
| `operador` | sí | dispositivos, reglas, geocercas, snapshots | no | no |
| `admin` | sí | sí | sí | sí |

La API vuelve a consultar el usuario en base de datos en cada sesión autenticada. Una cuenta desactivada o con rol modificado deja de operar aunque conserve un JWT anterior.

## 3. Entidades administrables

### 3.1 Organización

- nombre institucional;
- color primario;
- baseline de respuesta;
- identidad utilizada en informes y enlaces públicos.

Endpoint: `PATCH /admin/organization`

### 3.2 Usuarios

- alta con nombre, email, rol y contraseña temporal;
- cambio de rol;
- pausa/reactivación;
- baja lógica;
- prevención de eliminar o degradar al último administrador activo.

Endpoints:

```text
GET    /admin/users
POST   /admin/users
PATCH  /admin/users/{id}
DELETE /admin/users/{id}
```

### 3.3 Tipos de dispositivo

- nombre del tipo;
- diccionario de variables y unidades;
- edición y eliminación;
- desvinculación segura de los dispositivos al borrar un tipo.

Endpoints:

```text
GET    /devices/types
POST   /devices/types
PATCH  /devices/types/{id}
DELETE /devices/types/{id}
```

### 3.4 Dispositivos

- nombre y `external_id`;
- coordenadas;
- tipo;
- tags operativos;
- estado, batería, RSSI y última comunicación;
- rotación de credenciales MQTT de un solo uso.

Endpoints:

```text
GET    /devices
POST   /devices
PATCH  /devices/{id}
DELETE /devices/{id}
POST   /devices/{id}/rotate-credentials
```

La contraseña MQTT se devuelve solamente al crear o rotar. La base conserva un hash, no el secreto en claro.

### 3.5 Geocercas / zonas de riesgo

Cada zona circular guarda:

- nombre;
- dominio: `incendio`, `hidrica` o `general`;
- centro geográfico;
- radio entre 50 m y 100 km;
- polígono geográfico derivado en PostGIS.

Endpoints:

```text
GET    /zones
POST   /zones
PATCH  /zones/{id}
DELETE /zones/{id}
```

Al eliminar una zona, PostgreSQL aplica `ON DELETE SET NULL` en las reglas vinculadas. La API valida que una regla sólo pueda vincular una geocerca de la misma organización.

### 3.6 Reglas no-code

Una regla declara:

- tipo de alerta;
- una a ocho condiciones;
- lógica `AND`/`OR`;
- ventana temporal;
- geocerca opcional;
- tags de dispositivo;
- severidad;
- confirmación satelital;
- acciones;
- estado activo/pausado.

Endpoints:

```text
GET    /rules
POST   /rules
PATCH  /rules/{id}
PATCH  /rules/{id}/toggle
DELETE /rules/{id}
```

### 3.7 Fuentes ambientales

Desde Admin se habilitan o deshabilitan:

- Open-Meteo Forecast;
- Open-Meteo Air Quality / CAMS;
- Open-Meteo Flood / GloFAS;
- NASA FIRMS.

También se define:

- coordenada base;
- intervalo de actualización;
- radio FIRMS;
- nivel mínimo R0-R5;
- autoactivación de alertas.

Endpoint: `PATCH /admin/source-settings`

Las credenciales de proveedores no se exponen en esta respuesta.

### 3.8 Snapshots ambientales

- creación con metodología, coordenada, observaciones, índices, fuentes y limitaciones;
- activación posterior de alertas;
- borrado sólo por admin;
- vínculo de cada alerta con el snapshot que la originó.

Endpoints:

```text
POST   /environment/snapshots
GET    /environment/snapshots
GET    /environment/snapshots/latest
POST   /environment/snapshots/{id}/activate
DELETE /environment/snapshots/{id}
```

### 3.9 Informes oficiales

- borrador;
- publicación;
- revocación;
- eliminación;
- token público almacenado como hash;
- snapshot ambiental congelado dentro del informe.

### 3.10 Auditoría

Toda modificación sensible registra:

- organización;
- usuario;
- acción;
- recurso e ID;
- metadatos mínimos;
- fecha/hora.

Endpoint: `GET /admin/audit?limit=120`

La auditoría de aplicación no reemplaza logs de infraestructura, PostgreSQL audit, SIEM ni conservación legal.

## 4. Esquema de datos

Migraciones relevantes:

```text
01_schema.sql
02_auth_and_impact_reports.sql
03_spaceai_environmental_reports.sql
04_admin_abm_and_environment.sql
```

Tablas principales:

```text
organizations
users
user_legal_acceptances
device_types
devices
device_credentials
readings
risk_zones
rules
alerts
alert_sources
alert_events
citizen_reports
satellite_detections
environmental_source_settings
environmental_snapshots
environmental_alert_links
impact_reports
impact_report_shares
audit_events
```

PostGIS se usa para:

- puntos de dispositivos, reportes, alertas y snapshots;
- polígonos de geocercas;
- consultas de distancia y radio;
- prevención de mezcla entre organizaciones a nivel de aplicación.

## 5. Controles de seguridad

- `org_id` aplicado en consultas y mutaciones;
- validación de rol en backend;
- hash Argon2 para contraseñas y credenciales;
- token público de informes almacenado como hash;
- no exposición de `NASA_FIRMS_KEY`;
- alta/baja auditada;
- prevención de eliminar el último admin;
- geocerca validada dentro de la organización;
- credenciales MQTT mostradas una sola vez;
- secretos de producción validados al iniciar.

Para defensa en profundidad se recomienda incorporar PostgreSQL Row Level Security, mTLS o JWT por dispositivo, SIEM, rate limiting distribuido y aprobación dual para acciones críticas.

## 6. Operación de migraciones

En una base existente:

```bash
for migration in infra/db/migrations/*.sql; do
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration"
done
```

En producción:

1. backup y prueba de restauración;
2. migración en staging;
3. ventana de despliegue;
4. job único de migración antes de escalar réplicas;
5. smoke test de login, CRUD, reglas, snapshots e informes;
6. validación de índices PostGIS y planes de consulta.

## 7. Modo Cloudflare demo

En `NEXT_PUBLIC_DEMO_MODE=true`, el frontend emula las operaciones en `localStorage`:

- usuarios;
- tipos y dispositivos;
- credenciales de demostración;
- geocercas;
- reglas;
- fuentes;
- snapshots;
- informes y auditoría.

Cada navegador mantiene su propio dataset. No es multiusuario ni reemplaza PostgreSQL.
