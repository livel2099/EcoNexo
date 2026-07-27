# EcoNexo — Investor readiness

**Fecha de corte:** 24 de julio de 2026
**Estado:** prototipo funcional preproducción, preparado para demostración, pilotos controlados y due diligence técnica.

## Tesis

EcoNexo busca reducir el tiempo entre una señal ambiental y una decisión operativa. El producto unifica fuentes que normalmente están separadas —sensores IoT, meteorología, atmósfera, hidrología, satélite, ciudadanía y reglas— y conserva evidencia de cómo se detectó, priorizó, atendió y comunicó cada evento.

La propuesta se diferencia por transformar datos heterogéneos en una capa operativa trazable: observación, Health Threat Index, alertas R0-R5, geocercas, acciones y documentos institucionales emitidos desde el mismo sistema.

## Activos demostrables en el repositorio

- Arquitectura modular web/API/microservicios con separación multiorganización.
- Observatorio SpaceAI con comparación entre telemetría física y contexto geoespacial modelado.
- Índices explicables de aire, estrés térmico, humedad, incendio/humo, riesgo hídrico, UV y aptitud vectorial.
- Correlación con Open-Meteo Forecast, Copernicus CAMS, GloFAS y focos térmicos NASA FIRMS.
- Health Threat Index con severidad, persistencia, confianza, co-exposición y evidencia visible.
- Snapshots ambientales inmutables para reproducibilidad y auditoría.
- Correlación espacial PostGIS, geocercas y pipeline de alertas multifuente.
- Detección de anomalías y procesamiento satelital integrados como servicios.
- Flujo completo de reporte ciudadano, moderación y trazabilidad.
- Login/alta con Google verificado del lado servidor.
- Panel administrador con ABM de organización, usuarios, dispositivos, credenciales, reglas, fuentes y zonas.
- Informes institucionales para organizaciones/PO con anexos SpaceAI, publicación revocable y exportaciones.
- Marca tecnológica propia: logotipo SVG animado, circuitos, movimiento de datos y línea IA.
- Base de seguridad: secretos externos, tokens internos, almacenamiento privado, validación de archivos y encabezados.
- Docker/Kubernetes, CI y documentación de producción.

## Señales de madurez técnica alcanzadas

- Separación explícita entre “sensor observado” y “modelo/proxy”.
- RBAC y aislamiento por organización en operaciones administrativas.
- Auditoría de cambios sensibles.
- Rotación de credenciales de dispositivo.
- Reglas asociables a zonas de riesgo.
- Evidencia congelada dentro de informes para evitar documentos que cambien retroactivamente.
- Pruebas automatizadas de API y validación TypeScript.

## Lo que todavía debe probarse con evidencia de mercado

1. **Cliente y dolor:** entrevistas documentadas con municipios, forestales, energía, agua, salud, aseguradoras y organismos.
2. **Pilotos:** cartas de intención, alcance, responsables, baseline, fuentes locales y criterios de éxito.
3. **Economía:** precio aceptado, costo de hardware/instalación, soporte, margen y ciclo de venta.
4. **Impacto:** metodología, línea base, atribución, verificación y no duplicación.
5. **Validez técnica:** calibración territorial, falsos positivos/negativos y comparación con mediciones de referencia.
6. **Equipo:** fundadores, dedicación, funciones, antecedentes, vesting y plan de contratación.
7. **Legal:** sociedad, IP, contratos, datos, seguros y jurisdicciones.
8. **Producción:** SLA, SLO, DR, pentest, accesibilidad, observabilidad y revisión de fuentes/licencias.

## Uso propuesto de capital

El informe para VELA modela tres escenarios entre USD 250.000 y USD 400.000, con un caso base de USD 350.000 para 24 meses. Son supuestos de planificación, no costos históricos ni términos confirmados de un fondo.

Prioridades del caso base:

- producto, plataforma, datos y equipo técnico;
- calibración SpaceAI, IA explicable y metodología de impacto;
- hardware, instalación, mantenimiento y pilotos;
- seguridad, privacidad, legal, seguros y certificaciones;
- desarrollo comercial, alianzas y compras públicas;
- cloud, observabilidad, continuidad y contingencia.

## Próximo hito financiable

Llegar a una ronda institucional con:

- tres pilotos operativos y al menos dos clientes pagos o contratos equivalentes;
- métricas de detección, precisión, cobertura, tiempo de respuesta y disponibilidad con baseline;
- índices SpaceAI calibrados en al menos una vertical y territorio;
- unit economics por vertical y costo por nodo/área monitoreada;
- paquete jurídico/IP completo;
- controles de producción y auditoría externa focalizada;
- pipeline comercial trazable y plan regional.

## Data room recomendada

Usar la estructura de [docs/DUE_DILIGENCE_CHECKLIST.md](docs/DUE_DILIGENCE_CHECKLIST.md), junto con:

- [docs/SPACEAI_OPEN_METEO.md](docs/SPACEAI_OPEN_METEO.md)
- [docs/OFFICIAL_REPORTS.md](docs/OFFICIAL_REPORTS.md)
- [docs/ADMIN_ABM.md](docs/ADMIN_ABM.md)
- [docs/BRAND_SYSTEM.md](docs/BRAND_SYSTEM.md)
- [AUDIT.md](AUDIT.md)

El código por sí solo no prueba tracción, impacto, precisión o valuación. Esos resultados deben completarse con contratos, métricas de piloto, validación independiente y evidencia comercial antes de circular el memo final a inversores.
