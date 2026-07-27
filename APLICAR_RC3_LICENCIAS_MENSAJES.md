# Aplicar EcoNexo Misiones 1.0.0-rc.3

Esta actualización agrega mensajes administrativos de login y suscripciones limitadas por organización.

## 1. Reemplazar archivos

Usar el ZIP completo o copiar el parche sobre la versión 1.0.0-rc.2 conservando la estructura de carpetas.

## 2. Configurar administración comercial

En `.env`:

```env
PLATFORM_ADMIN_EMAILS=miguel@livel.pro
SALES_EMAIL=comercial@econexo.com.ar
```

El email configurado debe corresponder a un usuario activo de EcoNexo con rol administrador.

## 3. Aplicar la migración

```powershell
docker compose exec -T postgis psql `
  -U econexo `
  -d econexo `
  -v ON_ERROR_STOP=1 `
  -f /docker-entrypoint-initdb.d/11_subscriptions_and_admin_login_notifications.sql
```

## 4. Reconstruir

```powershell
docker compose up -d --build --force-recreate api web
```

## 5. Verificar

```powershell
Invoke-RestMethod http://localhost:8000/health
$openapi = Invoke-RestMethod http://localhost:8000/openapi.json
$openapi.paths.PSObject.Properties.Name | Select-String "subscriptions|admin/notifications"
```

Abrir `http://localhost:3000`, ingresar y revisar:

- **Admin Core > Mensajes**
- **Admin Core > Suscripción**

## Comportamiento inicial

- Organizaciones nuevas: Sandbox calificado por 14 días.
- Organizaciones existentes: Piloto 8 semanas por 56 días al aplicar la migración 11.
- Activación y cambio de plan: manual desde la consola comercial.
- Los límites se pueden ampliar por contrato sin modificar el código.
