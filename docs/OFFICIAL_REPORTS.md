# Informes oficiales, partes y boletines SpaceAI

Versión: **2026-07-24**

## 1. Objetivo

EcoNexo convierte evidencia operativa en documentos trazables para organizaciones, municipios, programas/organismos (PO), inversores, aseguradoras y auditorías.

La sección **Reportes y alertas** permite guardar y activar un snapshot. La sección **Informes** utiliza ese snapshot congelado para crear un documento institucional sin recalcular retrospectivamente los datos.

## 2. Tipos documentales

| Tipo | Uso principal | Contenido ambiental |
|---|---|---|
| Desempeño operativo | gestión interna, financiadores, directorio | métricas, disponibilidad, tiempos y evidencia |
| Boletín de amenaza | comunicación preventiva y coordinación | HTI, R0-R5, dominios priorizados y acciones |
| Parte oficial | municipio, PO, organismo o autoridad | situación, fuentes, eventos, recomendaciones y limitaciones |
| Informe de episodio | incidente específico | cronología, señales, alertas, respuesta y cierre |

## 3. Cadena de evidencia

```text
Fuentes originales
  ├─ telemetría IoT
  ├─ Open-Meteo / CAMS / GloFAS
  ├─ NASA FIRMS
  ├─ reportes ciudadanos
  └─ alertas y acciones de operador
          │
          ▼
Snapshot ambiental inmutable
          │
          ├─ observaciones
          ├─ índices R0-R5
          ├─ alertas propuestas
          ├─ fuentes y confianza
          ├─ focos térmicos
          └─ limitaciones
          │
          ▼
Informe institucional
          ├─ borrador
          ├─ impresión / PDF
          ├─ CSV de respaldo
          ├─ brief para email
          └─ enlace público revocable
```

## 4. Contenido del documento

Un informe puede incorporar:

- organización y destinatario;
- tipo y período;
- resumen ejecutivo;
- métricas operativas;
- nivel HTI y escala R0-R5;
- observaciones ambientales;
- matriz por dominio;
- alertas y acciones sugeridas;
- focos térmicos y distancia;
- fuentes utilizadas;
- recomendaciones;
- metodología y limitaciones;
- fecha de publicación.

## 5. Matriz R0-R5

La plantilla incluye una leyenda fija:

| Nivel | Rango continuo | Interpretación |
|---|---|---|
| R0 | <80% | basal |
| R1 | 80-99% | vigilancia |
| R2 | 100-149% | alerta |
| R3 | 150-199% | amenaza alta |
| R4 | ≥200% | crítico operativo |
| R5 | regla específica | emergencia |

El documento aclara que AQI, UV, ruido, SPI, IDLH, calor y otras escalas no lineales deben interpretarse por categorías oficiales.

## 6. Flujo recomendado para un reporte oficial

1. Revisar el Observatorio y la comparación IoT/modelo.
2. Corroborar una señal con fuente secundaria o personal de campo.
3. Guardar snapshot en **Reportes y alertas**.
4. Activar alertas internas sólo con validación operacional.
5. Abrir **Informes**.
6. Seleccionar plantilla, destinatario y período.
7. Editar resumen y recomendaciones.
8. Revisar la vista previa y las limitaciones.
9. Exportar CSV como respaldo.
10. Imprimir/guardar PDF.
11. Publicar enlace sólo cuando el documento esté aprobado.
12. Revocar el enlace al vencer la necesidad de acceso.

## 7. Publicación segura

- El token público se genera con alta entropía.
- La base guarda el hash SHA-256, no el token original.
- El enlace puede revocarse sin eliminar el informe.
- El documento público no expone credenciales ni datos internos de usuarios.
- La publicación no sustituye control documental, firma digital o expediente oficial.

Para uso gubernamental se recomienda agregar:

- número de expediente;
- clasificación documental;
- responsable firmante;
- sello de tiempo;
- firma digital conforme normativa aplicable;
- cadena de custodia de adjuntos;
- política de retención.

## 8. Reglas de redacción

- Separar hechos observados, datos modelados e inferencias.
- No llamar “sensor” a una celda de modelo.
- Informar coordenada, período y zona horaria.
- Evitar causalidad sanitaria sin vigilancia epidemiológica.
- Expresar incertidumbre y confiabilidad.
- Señalar cuando una variable es proxy.
- Conservar las limitaciones aunque el documento sea ejecutivo.
- No afirmar certificación independiente si no existe auditoría externa.

## 9. Correspondencia con el documento SpaceAI

La implementación usa como referencia técnica:

- matriz de severidad R0-R5;
- excedencia relativa para variables continuas;
- escalas específicas para AQI, UV, calor, SPI e IDLH;
- persistencia y confiabilidad;
- integración de aire, agua, clima, radiación, gases y vectores;
- co-exposición y vulnerabilidad poblacional;
- advertencias sobre proxies y calibración local.

Archivo de referencia: `docs/reference/SpaceAI_indicadores_amenaza_ambiental_salud_publica_v1.docx`.

## 10. Pendientes para carácter oficial pleno

Antes de presentar un informe como documento oficial de una autoridad:

- validar umbrales contra normativa nacional/provincial/municipal;
- aprobar protocolo con salud pública, ambiente y protección civil;
- incorporar responsables y firma;
- definir niveles de clasificación y acceso;
- calibrar con estaciones y eventos locales;
- establecer SLA de validación;
- realizar revisión jurídica y de protección de datos;
- documentar continuidad operativa y contingencia de fuentes.
