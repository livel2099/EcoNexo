# Validación EcoNexo 1.0.0-rc.6

## Resultado

- API: 50 pruebas aprobadas.
- Python: `compileall` aprobado para API y servicio satelital.
- OpenAPI: 79 rutas registradas y 65 documentadas; consola `/platform/*` excluida de Swagger.
- TypeScript: `npm run typecheck` aprobado.
- CSS: parseo PostCSS aprobado.
- YAML/JSON: parseo aprobado.
- Conflictos Git: sin marcadores `<<<<<<<`, `=======` ni `>>>>>>>` en código fuente.

## Rutas verificadas

```text
/health
/ready
/auth/change-password
/platform/summary
/pipeline/settings
/pipeline/run
/pipeline/runs
/pipeline/bootstrap
/devices
/devices/{device_id}/readings
/satellite/detections
/zones
```

## Limitación del entorno de ensamblado

El build integral de Next.js no pudo completarse localmente porque el gateway del entorno devolvió HTTP 503 al descargar el paquete opcional Linux `@next/swc-linux-x64-gnu`. El chequeo TypeScript y el parseo CSS sí finalizaron correctamente. Render ejecuta `npm ci` en Linux y debe instalar ese binario durante su build nativo.

## Prueba operativa pendiente en infraestructura

La ejecución real de migraciones PostGIS, Open-Meteo y NASA FIRMS requiere una base PostgreSQL/PostGIS y acceso saliente desde Render. El proyecto incluye validaciones, timeouts y degradación parcial para que una fuente externa no derribe el pipeline completo.
