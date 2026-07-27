param(
  [Parameter(Mandatory=$true)][string]$ApiUrl,
  [Parameter(Mandatory=$true)][string]$AppUrl,
  [switch]$CheckDockerDatabase
)

$ErrorActionPreference = "Stop"
$ApiUrl = $ApiUrl.TrimEnd('/')
$AppUrl = $AppUrl.TrimEnd('/')
$failures = New-Object System.Collections.Generic.List[string]

function Check-Url([string]$Name, [string]$Url) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 20
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
      $failures.Add("$Name respondio HTTP $($response.StatusCode)")
    } else {
      Write-Host "OK  $Name -> $Url" -ForegroundColor Green
    }
    return $response
  } catch {
    $failures.Add("$Name no disponible: $($_.Exception.Message)")
    return $null
  }
}

if (-not $ApiUrl.StartsWith('https://')) { $failures.Add('ApiUrl debe usar HTTPS') }
if (-not $AppUrl.StartsWith('https://')) { $failures.Add('AppUrl debe usar HTTPS') }

Check-Url 'Frontend' $AppUrl | Out-Null
Check-Url 'Health' "$ApiUrl/health" | Out-Null

try {
  $ready = Invoke-RestMethod -Uri "$ApiUrl/ready" -TimeoutSec 20
  if ($ready.status -ne 'ready') { $failures.Add('La API no esta ready') }
  if (-not $ready.checks.official_georef_boundary) { $failures.Add('Falta limite oficial GeoRef de Misiones') }
} catch {
  $failures.Add("No se pudo validar /ready: $($_.Exception.Message)")
}

try {
  $boundary = Invoke-RestMethod -Uri "$ApiUrl/territory/boundary-status" -TimeoutSec 20
  if (-not $boundary.official) { $failures.Add('boundary-status no informa official=true') }
} catch {
  $failures.Add("No se pudo validar boundary-status: $($_.Exception.Message)")
}

if ($CheckDockerDatabase) {
  docker compose exec -T postgis psql -U econexo -d econexo -v ON_ERROR_STOP=1 -c "SELECT * FROM misiones_external_data_audit; SELECT province, source, is_official FROM misiones_boundary_status LIMIT 2;"
  if ($LASTEXITCODE -ne 0) { $failures.Add('Fallo la auditoria territorial SQL') }
}

if ($failures.Count -gt 0) {
  Write-Host "`nPRE-FLIGHT BLOQUEADO" -ForegroundColor Red
  $failures | ForEach-Object { Write-Host "- $_" -ForegroundColor Red }
  exit 1
}

Write-Host "`nPRE-FLIGHT APROBADO: servicios publicos y limite oficial verificados." -ForegroundColor Green
