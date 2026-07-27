# EcoNexo Misiones - reporte de validación

**Fecha:** 27 de julio de 2026  
**Versión:** 1.0.0-rc.3  
**Alcance:** web, API, PostgreSQL/PostGIS, SpaceAI, Fuego/Humo, sanidad forestal, informes, Admin Core, suscripciones, mensajes de acceso y app móvil.

## Resultado del ensamblado

| Control | Método | Resultado |
|---|---|---|
| Pruebas API | `pytest -q` en `apps/api` | **37 aprobadas** |
| Sintaxis Python | `python -m compileall -q app` | Aprobada |
| Sintaxis TypeScript/TSX | `typescript.transpileModule` sobre `apps` | **47 archivos**, 0 errores sintácticos |
| CSS | `tinycss2` | **985 reglas**, 0 errores |
| JSON | parseo completo | Aprobado |
| YAML | parseo completo | Aprobado |
| Planes comerciales | pruebas de catálogo y esquemas | Precios, sandbox y overrides verificados |
| Secretos | exclusión y búsqueda de archivos sensibles | Sin `.env` reales ni claves privadas en la entrega |

## Cobertura funcional validada

- Login y registro por email; Google OAuth opcional.
- Mensaje interno por cada acceso correcto, con proveedor, horario, agente, origen e IP anonimizada.
- Bandeja de mensajes y lectura independiente por administrador.
- Planes `sandbox`, `diagnostic`, `pilot_8_weeks`, `municipal`, `province_pro`, `enterprise` y `academy`.
- Solicitud de cambio, aprobación manual, estado, vencimiento, consumo y límites por organización.
- Restricciones de usuarios activos, dispositivos, geocercas, reglas e informes mensuales.
- Sobrescritura contractual de límites y activación de módulos por administrador comercial.
- Centro de comando, Misiones territorial, Copernicus configurable, incendios/humo, plagas forestales, Alerta IA e informes.

## Controles pendientes en destino

El entorno de ensamblado no dispone de las dependencias npm del proyecto y el gateway usado previamente devolvió HTTP 503. Por lo tanto, el chequeo sintáctico de TypeScript fue exitoso, pero el typecheck semántico y el build de Next.js deben repetirse después de instalar dependencias:

```powershell
cd apps\web
npm ci
npm run typecheck
npm run build:cloudflare:production
npm run deploy:cloudflare:production:dry-run
```

La migración 11 también debe probarse con respaldo contra la instancia PostgreSQL/PostGIS de destino. No se incorporó un gateway de cobro automático: la aprobación es manual, coherente con ventas consultivas, diagnóstico, piloto y contrato SaaS.

## Dictamen

El paquete es un **candidato técnico 1.0.0-rc.3**. Los precios provienen del plan de negocios entregado; los límites numéricos son una configuración operativa inicial editable por contrato. El lanzamiento comercial exige completar datos societarios, términos definitivos, infraestructura pública, facturación, política de mora, soporte y aceptación operativa.
