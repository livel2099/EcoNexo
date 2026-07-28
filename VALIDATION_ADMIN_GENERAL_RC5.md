# Validación — EcoNexo Admin General rc.5

Fecha: 2026-07-28

## Resultado

- 45 pruebas de API aprobadas en el entorno disponible.
- 60 rutas públicas OpenAPI construidas.
- Rutas `/platform/*` registradas en FastAPI y excluidas de Swagger.
- `/auth/change-password` incluido en OpenAPI.
- 47 archivos TypeScript/TSX analizados: 0 errores de sintaxis.
- Python AST y `compileall`: aprobados.
- JSON: válido.
- YAML principal: válido.
- CSS: 0 errores de parseo.
- Scripts shell: sintaxis válida.
- Migraciones 12 y 13 idénticas entre `infra/db/migrations` y `apps/api/migrations`.

## Cobertura funcional revisada

- bootstrap del administrador general por variables de entorno;
- contraseña Argon2 y cambio obligatorio;
- protección por correo, rol y JWT;
- alta, modificación, baja lógica y restablecimiento de usuarios;
- activación y suspensión de organizaciones;
- licencias globales existentes;
- auditoría global;
- rutas privadas sin menú, sitemap ni OpenAPI;
- manejo defensivo del almacenamiento del navegador.

## Límites de esta validación

El registro npm no estuvo disponible en este entorno, por lo que no se ejecutó el build completo de Next.js con `npm ci`. Render/GitHub debe ejecutar:

```bash
cd apps/web
npm ci
npm run typecheck
npm run build:cloudflare:production
```

Docker tampoco está disponible en este entorno; la sintaxis y el flujo de inicio se validaron sin construir la imagen.
