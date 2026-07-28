# Aplicar EcoNexo 1.0.0-rc.6.2 en Render

## 1. Aplicar sobre un clon limpio

```powershell
cd "C:\Users\Livel\Documents\ECONEXO"
git clone https://github.com/livel2099/EcoNexo.git EcoNexo-rc62
```

Descomprimir el proyecto completo o copiar el parche sobre `EcoNexo-rc62`. No copiar `.git`, `node_modules`, `.next`, `out` ni `.env`.

## 2. Auditar localmente

```powershell
cd .\EcoNexo-rc62
python scripts\audit-system.py
```

Para incluir el build estático:

```powershell
python scripts\audit-system.py --build-web
```

También puede usarse:

```powershell
.\scripts\preflight-render.ps1
```

## 3. Subir sin sobrescribir el remoto

```powershell
git add -A
git commit -m "EcoNexo rc.6.2 Copernicus Process API"
git fetch origin
git rebase origin/main
git push origin main
```

No usar `git push --force`.

## 4. Variables de la API

Importar `.env.render.example` en el Web Service `EcoNexo` y completar como mínimo:

```env
DATABASE_URL=<Internal Database URL de Render>
JWT_SECRET=<secreto de 64+ caracteres>
INTERNAL_SERVICE_TOKEN=<otro secreto de 64+ caracteres>

PUBLIC_APP_URL=https://econexo-web.onrender.com
CORS_ORIGINS=https://econexo-web.onrender.com
ECONEXO_WEB_ORIGIN=https://econexo-web.onrender.com

COPERNICUS_ENABLED_BY_DEFAULT=true
COPERNICUS_MODE=process_api
COPERNICUS_CLIENT_ID=<OAuth client ID CDSE>
COPERNICUS_CLIENT_SECRET=<OAuth client secret CDSE>
```

Las variables `COPERNICUS_CLIENT_ID` y `COPERNICUS_CLIENT_SECRET` pertenecen únicamente a la API.

## 5. Configuración del servicio API

```text
Root Directory: apps/api
Dockerfile Path: Dockerfile
Docker Build Context: .
Docker Command: vacío
Health Check Path: /health
```

Plan gratuito:

```env
RUN_MIGRATIONS_ON_START=true
```

Plan pago:

```text
Pre-Deploy Command: python -m app.migrate
```

```env
RUN_MIGRATIONS_ON_START=false
```

## 6. Frontend estático

```text
Root Directory: apps/web
Build Command: npm ci && npm run typecheck && npm run build:cloudflare:production
Publish Directory: out
```

Variables:

```env
NEXT_PUBLIC_API_URL=https://econexo.onrender.com
NEXT_PUBLIC_WS_URL=wss://econexo.onrender.com
NEXT_PUBLIC_DEMO_MODE=false
NEXT_PUBLIC_STATIC_EXPORT=true
```

Después de modificar variables `NEXT_PUBLIC_*`, usar `Clear build cache & deploy`.

## 7. Orden de publicación

1. desplegar API;
2. comprobar que la migración 15 fue aplicada;
3. abrir `/health`;
4. desplegar frontend con caché limpia;
5. cerrar sesión y volver a ingresar;
6. abrir `Admin Core > Fuentes SpaceAI`;
7. mantener `Usar Copernicus predeterminado del sistema`;
8. ejecutar `Probar Copernicus`;
9. abrir Centro de Comando y probar las cuatro capas;
10. ejecutar el pipeline y comprobar nodos, zonas, FIRMS y alertas.

## 8. Respuestas esperadas

`GET /health` debe informar:

```json
{
  "release": "1.0.0-rc.6.2-render",
  "features": {
    "copernicus_default_mode": "process_api",
    "copernicus_process_configured": true
  }
}
```

`POST /copernicus/test` debe devolver:

```json
{
  "ok": true,
  "provider": "process_api"
}
```

Si `copernicus_process_configured=false`, las credenciales no fueron cargadas en el servicio API correcto o no se guardó el despliegue.
