param(
  [string]$WebPath = (Join-Path $PSScriptRoot "..\apps\web")
)

$ErrorActionPreference = "Stop"
Set-Location $WebPath

if (-not (Test-Path ".env.production.local")) {
  throw "Falta apps/web/.env.production.local. Copialo desde .env.production.example y completa las URLs HTTPS."
}

$envText = Get-Content ".env.production.local" -Raw
$blocked = @("localhost", "REEMPLAZAR", "http://")
foreach ($token in $blocked) {
  if ($envText -match [regex]::Escape($token)) {
    throw "La configuracion productiva contiene '$token'. Corregila antes de publicar."
  }
}

Remove-Item -Recurse -Force ".next", "out" -ErrorAction SilentlyContinue
npm ci
npm run typecheck
npm run deploy:cloudflare:production:dry-run
npm run deploy:cloudflare:production

Write-Host "Deploy terminado. Verifica /estado y la API publica." -ForegroundColor Green
