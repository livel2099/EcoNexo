# Migrar una base EcoNexo existente a Misiones 1.0.0-rc.2

Realizar backup antes de ejecutar cambios. No volver a correr `01_schema.sql` si la base ya contiene el esquema principal.

Desde PowerShell, en la raiz del proyecto:

```powershell
$files = @(
  "05_modules_mobile_and_alert_shares.sql",
  "06_misiones_territory_launch.sql",
  "07_misiones_launch_governance.sql",
  "08_official_georef_boundary.sql",
  "09_misiones_release_candidate.sql"
)

foreach ($file in $files) {
  Write-Host "Aplicando $file..."
  docker compose exec -T postgis psql `
    -U econexo `
    -d econexo `
    -v ON_ERROR_STOP=1 `
    -f "/docker-entrypoint-initdb.d/$file"
  if ($LASTEXITCODE -ne 0) { throw "Fallo $file" }
}
```

Luego iniciar API/web, ingresar como administrador y sincronizar el limite oficial desde Admin Core o `POST /territory/sync-georef`.

Verificar:

```sql
SELECT * FROM misiones_boundary_status;
SELECT * FROM misiones_external_data_audit;
SELECT * FROM misiones_launch_status;
```

Para lanzamiento, el limite debe ser oficial y todos los conteos externos deben ser cero. Corregir o archivar datos heredados antes de validar constraints `NOT VALID`.

## Migración 10: Copernicus y sanidad forestal

```powershell
docker compose exec -T postgis psql -U econexo -d econexo -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/10_copernicus_forestry_pests.sql
```

Después reconstruir API y web:

```powershell
docker compose up -d --build --force-recreate api web
```

Ingresar a `Admin Core > Fuentes SpaceAI`, cargar la URL WMS propia de Copernicus Data Space, probar GetCapabilities, seleccionar los nombres reales de las capas y guardar.
