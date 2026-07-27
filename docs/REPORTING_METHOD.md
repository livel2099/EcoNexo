# Método de informes técnicos EcoNexo / SpaceAI

Los informes institucionales se diseñaron para laboratorio, auditoría, municipio, organización, aseguradora o inversor. Ya no se limitan a un resumen breve: documentan la trazabilidad completa del análisis.

## Contenido mínimo

1. Portada, destinatario, período, versión y responsable.
2. Objeto, alcance, área de interés y preguntas de análisis.
3. Protocolo de adquisición, resolución temporal y fuentes.
4. Control de calidad, integridad y limitaciones.
5. Observaciones originales y unidades.
6. Matriz de índices R0-R5.
7. Fórmulas y cálculos intermedios por dominio.
8. Health Threat Index integrado.
9. Focos térmicos, humo, aire, clima y contexto hídrico.
10. Alertas y reportes correlacionados.
11. Cadena de evidencia y confiabilidad.
12. Hallazgos, recomendaciones y plan de verificación.
13. Referencias y anexos metodológicos.

## Fórmulas visibles

```text
Excedencia relativa (%) = (valor observado / valor de referencia) × 100

Score_i = severidad_i × persistencia_i × confiabilidad_i

HTI = Σ(w_i × Score_i × vulnerabilidad_poblacional) / Σ(w_i)
```

Persistencia sugerida:

```text
1.00 = evento aislado
1.25 = 2 a 3 días
1.50 = 4 a 7 días
2.00 = más de 7 días o exposición crónica
```

## Escala operativa

```text
R0 < 80%
R1 80-99%
R2 100-149%
R3 150-199%
R4 >= 200%
R5 regla específica de emergencia
```

AQI, índice UV, SPI, ruido, IDLH, calor extremo y variables binarias no deben transformarse mecánicamente a un porcentaje lineal. El informe debe indicar la regla categórica utilizada.
