# Informes institucionales para organizaciones y PO

## Alcance

La sección **Informes** no reemplaza a **Reportes ciudadanos**. El reporte ciudadano es evidencia de campo; el informe institucional consolida indicadores para comunicar resultados a una organización, municipio, programa/organismo (PO), inversor, aseguradora o auditoría.

## Flujo

1. Usuario autenticado selecciona título, destinatario y período.
2. La API consulta datos de su organización y calcula métricas.
3. Se guarda un borrador con resumen, hallazgos y recomendaciones.
4. La UI muestra un documento ejecutivo listo para imprimir o guardar como PDF.
5. Puede exportarse CSV o copiarse un resumen para correo.
6. Al publicar, la API genera un token aleatorio; guarda sólo su hash y devuelve un enlace.
7. Publicar de nuevo revoca el enlace anterior. También puede revocarse o eliminarse explícitamente.

## Métricas actuales

- dispositivos totales y operativos;
- alertas totales, abiertas y críticas;
- tiempo medio de detección cuando existe evidencia;
- reportes ciudadanos y verificados;
- métricas del modelo/KPI disponibles para la organización.

## Endpoints

```text
GET    /impact-reports
POST   /impact-reports
GET    /impact-reports/{id}
POST   /impact-reports/{id}/publish
POST   /impact-reports/{id}/revoke
DELETE /impact-reports/{id}
GET    /impact-reports/public/view/{token}
```

Los endpoints privados aplican organización desde el JWT. El endpoint público sólo entrega un informe publicado cuyo hash coincida.

## Uso seguro

- No incluir datos personales innecesarios en resumen, hallazgos o recomendaciones.
- El enlace es compartible: tratarlo como información confidencial hasta contar con acceso nominativo.
- Revocar el enlace al finalizar la relación o ante envío incorrecto.
- Definir retención y clasificación documental por contrato.
- No presentar métricas calculadas como impacto causal o certificación independiente sin metodología y verificación.

## Próximas mejoras

- expiración configurable de enlaces;
- acceso nominativo/OTP para documentos sensibles;
- historial de versiones y firma/aprobación;
- PDF generado en servidor con hash del documento;
- anexos de evidencia y redacción/anonimización;
- plantillas por cliente/vertical e identidad de marca;
- indicadores IRIS+/ODS mapeados y verificación externa.
