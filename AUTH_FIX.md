# Corrección de acceso EcoNexo

Esta edición incorpora:

- logotipo tecnológico visible dentro del panel de acceso, incluso en pantallas pequeñas;
- registro de organizaciones por email sin Google;
- `POST /auth/register` en FastAPI;
- primer usuario con rol `admin`;
- contraseña Argon2 y aceptación legal;
- indicador de estado API/base en la pantalla de acceso;
- mensajes separados para credenciales inválidas y API inaccesible;
- corrección del redireccionamiento que ocultaba errores `401` del login;
- CORS local para `localhost` y `127.0.0.1`;
- registro por email funcional también en el modo demo de Cloudflare.

## Aplicación en una base existente

No volver a ejecutar `01_schema.sql` cuando ya existe `org_vertical`. Aplicar:

```powershell
docker compose exec -T postgis psql -U econexo -d econexo -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/02_auth_and_impact_reports.sql
docker compose exec -T postgis psql -U econexo -d econexo -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/03_spaceai_environmental_reports.sql
docker compose exec -T postgis psql -U econexo -d econexo -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/04_admin_abm_and_environment.sql
```

Después reconstruir API y web:

```powershell
docker compose up -d --build --force-recreate api web
Invoke-RestMethod http://localhost:8000/health
```
