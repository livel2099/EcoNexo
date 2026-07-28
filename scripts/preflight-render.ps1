param(
  [switch]$BuildWeb
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$arguments = @("scripts/audit-system.py")
if ($BuildWeb) { $arguments += "--build-web" }

python @arguments
if ($LASTEXITCODE -ne 0) {
  throw "La auditoría de EcoNexo encontró errores."
}

Write-Host "Preflight Render aprobado." -ForegroundColor Green
Write-Host "Build recomendado: npm ci && npm run typecheck && npm run build:cloudflare:production"
