# Política de seguridad de EcoNexo

## Estado

EcoNexo es un prototipo preproducción. Los controles implementados reducen riesgos obvios, pero no constituyen una certificación ni reemplazan una revisión independiente.

## Controles incorporados

- JWT con vencimiento y separación por organización.
- Contraseñas con Argon2; Google ID tokens verificados en backend.
- Credencial compartida para servicios internos sensibles.
- Rechazo de secretos de ejemplo cuando `ENVIRONMENT=production`.
- Sesión web en `sessionStorage` y limpieza ante 401.
- Tokens ciudadanos firmados y rate limiting básico por proceso/IP.
- Archivos limitados a JPEG/PNG/WebP, magic bytes y máximo configurable.
- Bucket privado, claves S3 internas y URLs firmadas de lectura.
- Tokens públicos de informes almacenados como SHA-256 y revocables.
- CORS configurable y encabezados de seguridad.
- Docker no-root para web/API y referencias Kubernetes con recursos/probes.

## Controles obligatorios antes de producción

- WAF/API gateway y rate limiting distribuido (Redis o equivalente).
- MQTT con identidad por dispositivo, ACL por tópico y rotación.
- Escaneo/normalización de imágenes, antivirus y eliminación de metadatos EXIF.
- Secret manager, KMS, rotación y separación por ambiente/cuenta.
- SAST, SCA, SBOM, firma de imágenes y escaneo de contenedores.
- Auditoría completa de acciones administrativas y exportable a SIEM.
- MFA o política equivalente para administradores; flujo de invitación y baja.
- Pentest independiente y corrección de hallazgos críticos/altos.
- Backups cifrados, PITR, prueba de restauración y plan de continuidad.

## Reporte de vulnerabilidades

No abrir una issue pública con datos sensibles. Informar de manera privada al contacto legal/seguridad configurado para el entorno, con:

- activo y versión;
- impacto estimado;
- pasos mínimos de reproducción;
- evidencia no destructiva;
- datos de contacto.

No acceder a información de terceros, degradar el servicio, realizar ingeniería social ni exfiltrar datos. La organización operadora debe formalizar plazos, safe harbor y canal antes del lanzamiento comercial.
