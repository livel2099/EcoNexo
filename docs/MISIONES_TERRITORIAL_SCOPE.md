# Alcance territorial EcoNexo Misiones

## Criterio de lanzamiento

EcoNexo se configura como plataforma provincial para Misiones. El catálogo empaquetado contiene 17 departamentos y 79 municipios. Ningún registro georreferenciado fuera de la provincia debe alimentar mapas, KPIs, correlaciones, alertas, snapshots o informes institucionales.

## Capas de control

1. **Frontend:** encuadre, centro y límites del mapa orientados a Misiones; señales externas ocultas y contabilizadas.
2. **API:** validación de coordenadas en altas y consultas; normalización de municipio y departamento.
3. **PostgreSQL/PostGIS:** constraints territoriales sobre dispositivos, alertas, reportes, detecciones satelitales, snapshots y geocercas.
4. **Fuentes externas:** NASA FIRMS se consulta con un bounding box exclusivo de Misiones y vuelve a filtrarse antes de guardar.
5. **Auditoría:** la vista `misiones_external_data_audit` informa cualquier registro histórico fuera del alcance.
6. **Geometría oficial:** la tabla `territory_boundaries` prioriza GeoRef Argentina. El polígono local es un fallback, no una delimitación catastral.

## Sincronización GeoRef

Aplicar primero las migraciones 06, 07, 08 y 09. Luego, con una sesión administradora:

```http
POST /territory/sync-georef
Authorization: Bearer <TOKEN_ADMIN>
```

Desde PowerShell:

```powershell
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Method Post `
  -Uri "https://api.econexo.com.ar/territory/sync-georef" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body "{}"
```

Verificación pública:

```text
GET /territory/boundary-status
GET /territory/geojson
GET /ready
```

`boundary-status` debe indicar `official: true` antes del lanzamiento público.

## Auditoría SQL obligatoria

```sql
SELECT * FROM misiones_external_data_audit;
SELECT * FROM misiones_boundary_status;
SELECT * FROM misiones_launch_status;
```

Todos los valores `external_rows` deben ser cero. La primera fila de `misiones_boundary_status` debe identificar `GeoRef Argentina (IGN/INDEC)` y `is_official = true`.

## Tratamiento de datos históricos externos

No se recomienda eliminar automáticamente datos heredados. Deben exportarse, clasificarse y corregirse o archivarse con trazabilidad. Mientras existan, las consultas operativas los excluyen. La validación de constraints `NOT VALID` se realiza únicamente después de dejar la auditoría en cero:

```sql
ALTER TABLE devices VALIDATE CONSTRAINT devices_inside_misiones_check;
ALTER TABLE alerts VALIDATE CONSTRAINT alerts_inside_misiones_check;
ALTER TABLE citizen_reports VALIDATE CONSTRAINT reports_inside_misiones_check;
ALTER TABLE satellite_detections VALIDATE CONSTRAINT satellite_inside_misiones_check;
ALTER TABLE environmental_snapshots VALIDATE CONSTRAINT snapshots_inside_misiones_check;
ALTER TABLE risk_zones VALIDATE CONSTRAINT risk_zones_inside_misiones_check;
```

## Limitación

GeoRef normaliza unidades territoriales oficiales, pero no reemplaza información catastral, mensura ni resolución administrativa específica. Para contratos que dependan de límites parcelarios o jurisdiccionales finos, la organización debe proveer la capa oficial correspondiente.
