# EcoNexo Misiones - puerta de lanzamiento oficial

## Estado del paquete

Este repositorio es un **candidato de lanzamiento técnico 1.0.0-rc.2**. Incluye controles territoriales, autenticación, ABM, reportes, trazabilidad, fuentes ambientales, módulo de incendios y humo, Alerta IA, aplicación móvil, páginas legales y despliegue Cloudflare. No constituye por sí mismo certificación legal, sanitaria, de laboratorio, de ciberseguridad ni homologación estatal.

## Bloqueantes técnicos

- Aplicar migraciones `01` a `09` en orden sobre una base nueva, o `06` a `09` sobre la base actual ya migrada. Usar respaldo y `ON_ERROR_STOP=1`.
- Sincronizar el límite oficial de Misiones desde GeoRef y confirmar `official: true`.
- Auditar datos externos con `misiones_external_data_audit`; todos los resultados deben ser cero.
- Publicar la API con HTTPS; nunca utilizar `localhost` en el build público.
- Configurar dominio, CORS exacto, proxy confiable y encabezados reenviados.
- Configurar NASA FIRMS y dejar `ALLOW_DEMO_SATELLITE_FIXTURES=false`.
- Configurar un WMS propio de Copernicus o mantener la capa deshabilitada.
- Ejecutar backup, restauración, smoke test y prueba de rollback.
- Integrar monitoreo, logs centralizados, alertas, uptime y expiración de certificados.
- Ejecutar pentest y corregir hallazgos críticos/altos.

## Bloqueantes institucionales

- Razón social, CUIT, domicilio, canal legal y responsable de tratamiento.
- Revisión jurídica argentina de términos, privacidad, cookies, reportes comunitarios y contratos.
- Acuerdo con cada organismo sobre umbrales, responsables, horarios, canales y retención.
- Validación de fórmulas y protocolos por profesionales ambientales/sanitarios y laboratorios intervinientes.
- Política explícita para uso de logos, denominaciones y documentos “oficiales”.
- Responsable humano para aprobar alertas R3-R5 y comunicaciones externas.

## Incendios forestales y humo

- Un foco térmico es una señal a verificar, no un incendio confirmado.
- La verificación puede combinar cámaras, IA visual, drones, brigadas, sensores y reportes de campo.
- En producción, la falla de FIRMS no habilita fixtures: se comunica “fuente no disponible”.
- Ante fuego o humo visible, el canal inmediato mostrado es el 911.
- EcoNexo complementa el esquema provincial; no reemplaza la autoridad competente.

## Prueba de aceptación mínima

1. Crear organización y segundo administrador.
2. Registrar dispositivo dentro de Misiones y rechazar uno fuera de la provincia.
3. Ingerir telemetría, generar snapshot y crear alerta supervisada.
4. Cargar reporte comunitario con consentimiento y moderarlo.
5. Consultar Open-Meteo y verificar separación entre sensor y modelo.
6. Ingerir una detección FIRMS real y revisar su fuente/hora.
7. Generar informe institucional completo, imprimir PDF y revocar enlace público.
8. Enviar una Alerta IA revisada a un canal de prueba.
9. Verificar `/health`, `/ready`, `/territory/boundary-status` y `/estado`.
10. Restaurar una copia de la base en un entorno aislado.
11. Ejecutar `scripts/preflight-launch.ps1` contra las URLs públicas y resolver todos los bloqueos.

## Criterio de aprobación

El lanzamiento se autoriza cuando no quedan bloqueantes críticos, el límite oficial está sincronizado, no existen registros operativos externos, las fuentes demo están deshabilitadas, la restauración fue probada y la autoridad interna firmó el acta de aceptación.
