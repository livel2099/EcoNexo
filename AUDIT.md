# Auditoría técnica y preparación de lanzamiento - EcoNexo Misiones

**Corte:** 27 de julio de 2026  
**Versión:** 1.0.0-rc.2  
**Criterio:** implementado significa presente y probado en el repositorio; no equivale a homologación externa.

## Resumen ejecutivo

| Área | Estado | Evidencia |
|---|---|---|
| Alcance Misiones | Implementado | 17 departamentos, 79 municipios, filtros web/API/DB/móvil y auditoría de externos |
| Límite territorial | Implementado con puerta | fallback local + sincronización oficial GeoRef; `/ready` informa el estado |
| Autenticación | Implementada | email/Argon2, Google opcional, RBAC y alta transaccional |
| Incendios y humo | Implementado | satélite, clima, aire, IoT, reportes, verificación humana y 911 |
| Alerta IA | Implementada | R0-R5, HTI, evidencia, aprobación y trazabilidad de comunicaciones |
| Informes | Implementados | documento extendido, fórmulas, fuentes, control de calidad, laboratorio y firmas |
| Admin Core | Implementado | ABM, licencias, fuentes, geocercas y auditoría |
| Reportes comunitarios | Implementados | formulario, foto, geolocalización, consentimiento y moderación |
| Seguridad de arranque | Reforzada | secretos, URLs HTTPS, CORS, cifrado S3 y proxy confiable exigidos en producción |
| Validación | Aprobada con salvedades | 28 pruebas API, Python y sintaxis TS/CSS/JSON/YAML aprobados |

## Hallazgo corregido: referencias a Corrientes

Se retiraron centros, datos de ejemplo y flujos que pudieran alimentar el producto con otra provincia. Corrientes permanece únicamente en pruebas automáticas que demuestran que una coordenada externa es rechazada. Los datos heredados no se borran silenciosamente: quedan excluidos de la operación y visibles en `misiones_external_data_audit` para corrección o archivo trazable.

## Criterio territorial productivo

La geometría empaquetada es un fallback para continuidad. Antes del lanzamiento se debe ejecutar `POST /territory/sync-georef`, comprobar `official: true` y validar los constraints territoriales. GeoRef se usa por ser el servicio público argentino de normalización y geometrías oficiales; no reemplaza mensura ni cartografía catastral.

## Incendios forestales

EcoNexo se presenta como sistema complementario. Una anomalía térmica no se etiqueta como incendio confirmado sin evidencia adicional. La correlación admite cámaras, IA visual, drones, sensores, brigadas y reportes. El marco documental referencia Ley Nacional 26.815, Ley provincial XVI-N°65 y el Plan Provincial de Manejo del Fuego. No se inventa una ley provincial específica de lectura satelital que no haya sido verificada.

## Riesgos abiertos que bloquean producción

1. **Infraestructura pública:** API HTTPS, PostgreSQL/PostGIS administrado, S3 privado, MQTT autenticado y Redis/WAF.
2. **Credenciales:** FIRMS MAP_KEY, WMS propio, Google OAuth y secretos gestionados fuera del repositorio.
3. **Continuidad:** backup/PITR, restauración, rollback, monitoreo, SLO, logs centralizados y runbooks.
4. **Seguridad:** pentest, análisis de dependencias, rate limiting distribuido, MFA/step-up y antivirus de evidencias.
5. **Institucional:** razón social, CUIT, domicilio, responsable de datos, contratos, DPA y aprobación de textos.
6. **Científico-operativo:** calibración local, validación de umbrales, responsables humanos y protocolo R3-R5.
7. **Laboratorio:** cadena de custodia, métodos, incertidumbre, firma y revisión profesional cuando corresponda.
8. **Móvil:** projectId EAS, firma, OAuth nativo, privacy manifests y pruebas en equipos reales.

## Criterio de salida

El sistema puede pasar a piloto controlado con datos minimizados y aprobación humana. El lanzamiento público requiere que `/ready` esté en estado `ready`, GeoRef sea oficial, la auditoría externa sea cero, los fixtures estén deshabilitados y exista acta de aceptación técnica, jurídica y operativa.

## rc.3 - Suscripciones y mensajes de acceso

- Implementado: notificación de login correcto por email/Google con IP anonimizada.
- Implementado: bandeja por administrador y consola global restringida por lista de emails.
- Implementado: límites transaccionales al crear/reactivar usuarios, dispositivos, geocercas, reglas e informes.
- Implementado: solicitud y activación manual de planes con trazabilidad.
- Pendiente de producción: integrar facturación, impuestos, conciliación, reintentos, mora y cancelación automática si se decide cobrar en línea.
- Pendiente de seguridad: enviar eventos a SIEM/observabilidad y establecer retención formal para metadatos de acceso.
