# Despliegue Cloudflare - EcoNexo Misiones

## Demo autónoma

La demo no utiliza API ni base central:

```powershell
cd apps\web
npm ci
npx wrangler login
npm run deploy:cloudflare
```

Worker: `econexo-demo`.

## Frontend oficial conectado a API

Crear `apps/web/.env.production.local` a partir de `.env.production.example` y completar URLs HTTPS, identidad legal, Google OAuth y WMS propio.

```powershell
cd apps\web
Copy-Item .env.production.example .env.production.local
notepad .env.production.local
Remove-Item -Recurse -Force .next, out -ErrorAction SilentlyContinue
npm ci
npm run typecheck
npm run deploy:cloudflare:production:dry-run
npm run deploy:cloudflare:production
```

Worker: `econexo-misiones`, configurado en `wrangler.production.jsonc`.

Variables mínimas:

```env
NEXT_PUBLIC_DEMO_MODE=false
NEXT_PUBLIC_STATIC_EXPORT=true
NEXT_PUBLIC_API_URL=https://api.econexo.com.ar
NEXT_PUBLIC_WS_URL=wss://api.econexo.com.ar
NEXT_PUBLIC_APP_URL=https://app.econexo.com.ar
NEXT_PUBLIC_GOOGLE_CLIENT_ID=
NEXT_PUBLIC_COPERNICUS_WMS_URL=
NEXT_PUBLIC_LEGAL_ENTITY_NAME=
NEXT_PUBLIC_LEGAL_CUIT=
NEXT_PUBLIC_LEGAL_ADDRESS=Misiones, Argentina
NEXT_PUBLIC_LEGAL_JURISDICTION=Provincia de Misiones
NEXT_PUBLIC_LEGAL_EMAIL=
```

## Condición indispensable

Cloudflare solo aloja el frontend estático. La API FastAPI, PostgreSQL/PostGIS, almacenamiento privado, MQTT y tareas satelitales deben estar publicados por separado. La URL `http://localhost:8000` no es accesible para usuarios externos.

## Verificación posterior

```powershell
npx wrangler deployments list --config wrangler.production.jsonc
curl.exe -I https://econexo-misiones.<subdominio>.workers.dev
curl.exe https://api.econexo.com.ar/health
curl.exe https://api.econexo.com.ar/ready
curl.exe https://api.econexo.com.ar/territory/boundary-status
```

Abrir también:

```text
https://app.econexo.com.ar/estado
https://app.econexo.com.ar/metodologia
```
