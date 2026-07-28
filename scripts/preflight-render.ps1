$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "[1/6] Buscando conflictos Git..."
$conflicts = Get-ChildItem apps,services,infra -Recurse -File |
  Where-Object { $_.FullName -notmatch 'node_modules|\\.next|\\out|__pycache__' } |
  Select-String -Pattern '^(<<<<<<<|=======|>>>>>>>)'
if ($conflicts) {
  $conflicts | ForEach-Object { Write-Host $_ }
  throw "Hay marcadores de conflicto sin resolver."
}

Write-Host "[2/6] Compilando Python..."
python -m compileall -q apps/api/app services/satellite/app

Write-Host "[3/6] Verificando migracion 14..."
if (-not (Test-Path "apps/api/migrations/14_telemetry_pipeline_and_map.sql")) {
  throw "Falta la migracion 14 dentro del contexto Docker de la API."
}
$infraHash = (Get-FileHash "infra/db/migrations/14_telemetry_pipeline_and_map.sql" -Algorithm SHA256).Hash
$apiHash = (Get-FileHash "apps/api/migrations/14_telemetry_pipeline_and_map.sql" -Algorithm SHA256).Hash
if ($infraHash -ne $apiHash) {
  throw "Las dos copias de la migracion 14 no coinciden."
}

Write-Host "[4/6] TypeScript..."
Push-Location apps/web
npm run typecheck
Pop-Location

Write-Host "[5/6] Validando YAML..."
python -c "import yaml,pathlib; [yaml.safe_load(pathlib.Path(p).read_text()) for p in ('render.yaml','render.production.yaml')]; print('YAML OK')"

Write-Host "[6/6] Estado Git..."
git status --short

Write-Host "Preflight aprobado. Para el Static Site de Render use: npm ci && npm run typecheck && npm run build:cloudflare:production"
