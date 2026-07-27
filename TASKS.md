# Roadmap EcoNexo Misiones

## P0 - Candidato de lanzamiento técnico

- [x] Catálogo de 17 departamentos y 79 municipios.
- [x] Validación territorial en web, API, PostGIS, satélite, informes y móvil.
- [x] Sincronización y estado del límite oficial GeoRef.
- [x] Auditoría de datos históricos externos a Misiones.
- [x] Registro por email y Google OAuth opcional.
- [x] Centro de comando, Alerta IA y módulo Fuego/Humo.
- [x] Reporte comunitario completo.
- [x] Informes extensos con SpaceAI, fuentes, laboratorio y firmas.
- [x] Admin Core, licencias, reglas, dispositivos y geocercas.
- [x] App móvil Expo/React Native.
- [x] Scripts de deploy Cloudflare productivo y pre-flight.
- [x] 29 pruebas API y validación sintáctica del ensamblado.
- [ ] Completar identidad societaria y textos legales definitivos.
- [ ] Ejecutar `npm ci`, typecheck y build productivo en CI limpio.
- [ ] Aplicar migraciones 01-09 y sincronizar GeoRef en preproducción.

## P1 - Preproducción

- [ ] API y base administrada con HTTPS, backup/PITR y restauración probada.
- [ ] FIRMS real, WMS propio y atribuciones visibles.
- [ ] MQTT TLS/mTLS con ACL y rotación por dispositivo.
- [ ] WAF, Redis, cuotas, rate limiting distribuido y protección antiabuso.
- [ ] Google OAuth web/móvil y recuperación segura de cuenta.
- [ ] Observabilidad, SLO, alertas, dashboards, SIEM y runbooks.
- [ ] Re-encoding, EXIF stripping, antivirus y cuarentena de imágenes.
- [ ] Pruebas E2E, carga, accesibilidad, navegadores y dispositivos reales.
- [ ] Pentest y corrección de hallazgos altos/críticos.
- [ ] Validar que `misiones_external_data_audit` sea cero.

## P2 - Aceptación institucional

- [ ] Calibrar SpaceAI con estaciones, antecedentes y protocolos de Misiones.
- [ ] Definir responsables y aprobación humana para R3-R5.
- [ ] Validar documentos, cadena de custodia y firma con laboratorios/organismos.
- [ ] Contratos, DPA, retención, subencargados y uso de logos.
- [ ] Ejecutar piloto con criterios de éxito, baseline y falsos positivos.
- [ ] Probar comunicaciones WhatsApp/Telegram en canales autorizados.
- [ ] Firmar acta de aceptación y plan de respuesta a incidentes.

## P3 - Lanzamiento y escala

- [ ] Publicar dominio oficial y ficha de estado/metodología.
- [ ] Alta por invitación y onboarding contractual.
- [ ] App Store/Play Store con revisión de privacidad.
- [ ] Multi-región, DR y simulacros periódicos.
- [ ] Model registry, monitoreo de drift y evaluación independiente.
- [ ] Firma digital, sellado de tiempo e interoperabilidad institucional.

## Suscripciones y operación comercial

- [x] Catálogo de planes y límites por organización.
- [x] Sandbox calificado para nuevas altas.
- [x] Solicitudes de cambio y aprobación por administrador comercial.
- [x] Mensajes de login en Admin Core.
- [ ] Definir términos contractuales definitivos de cada plan y add-on.
- [ ] Integrar facturación/conciliación solo cuando la estructura fiscal y el medio de cobro estén aprobados.
- [ ] Definir política de gracia, mora, suspensión, reactivación y soporte.
