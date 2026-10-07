# Ciclo predictivo de Econexo

Implementación: incendios, anegamiento por lluvias y riesgo sanitario ambiental por calor y PM2.5, por organización, nodo de vigilancia y horizontes de 6, 24 y 72 horas. Cada riesgo conserva fuentes, features, evidencia, métricas, consentimiento y modelos propios. La cobertura operativa es el área de vigilancia de 5 km del nodo, que debe verificarse en campo; la grilla del proveedor puede ser más gruesa.

## Riesgos y objetivos separados

| `hazard` | Fuente y features | Resultado positivo verificable | Alcance |
|---|---|---|---|
| `fire` | Pronóstico meteorológico: temperatura, humedad, viento, lluvia | Incendio en el área del nodo | Condiciones meteorológicas; falta combustible e ignición |
| `hydric` | Pronóstico meteorológico: lluvia total, pico horario, máximo acumulado en 6 h | Anegamiento pluvial documentado | No equivale a crecida fluvial ni mapa de inundación |
| `health_heat` | Pronóstico meteorológico: sensación térmica máxima/mínima y horas ≥35 °C | Incidente sanitario asociado al calor, verificado con un protocolo local | Exposición ambiental, sin diagnóstico individual ni predicción de brotes |
| `health_air` | Copernicus CAMS vía Open-Meteo: PM2.5 medio/máximo y horas ≥35 μg/m³ | Incidente sanitario asociado a PM2.5, verificado con un protocolo local | Exposición ambiental modelada; grilla global aproximada de 45 km |

Los cortes y pesos de los índices iniciales son heurísticos experimentales; no son umbrales oficiales, límites legales ni probabilidades. PM2.5 se promedia sobre el horizonte elegido, no se presenta como un promedio regulatorio de 24 h cuando el horizonte difiere. La lluvia de `hydric` se fecha al inicio de la hora de acumulación: Open-Meteo entrega la suma de la hora precedente, y se excluyen las acumulaciones que comienzan antes de la ventana futura. No se usa sequía como etiqueta de anegamiento.

El responsable local debe fijar una definición consistente de caso, su fecha de inicio, área y evidencia antes de entrenar. Para salud se registran referencias y evidencia agregada sin datos personales de pacientes; un pico de pronóstico no demuestra un incidente sanitario. Una fuente de evidencia debe ser independiente del modelo que se evalúa. Las etiquetas negativas exigen cobertura suficiente para verificar la ausencia del objetivo concreto; no se deducen de la ausencia de alertas o consultas recibidas.

## Funciones implementadas

- Pronósticos futuros del lado servidor, con temperatura, humedad, viento y precipitación horarios de Open-Meteo.
- Validación de horas futuras completas, unidades, rangos físicos, timestamps, duplicados y valores finitos. Un dato faltante impide emitir esa ventana; no se sustituye por cero.
- Ledger inmutable de emisiones: hora del servidor, período válido, ubicación histórica, fuente, serie horaria, features, versión, umbral, explicación, acción, hash y score/probabilidad.
- Índice meteorológico explicable `fire-weather-index-v1`, identificado como heurístico. No es el índice FWI oficial ni una probabilidad calibrada de incendio.
- Resultados independientes: incidente verificado o cobertura completa sin incidente. No se utilizan las confirmaciones de alertas como ground truth automático.
- Evaluación por versión y horizonte: precision/recall de ventanas, falsas alarmas, eventos omitidos incluso sin pronósticos, recall de eventos, anticipación, Brier y calibración por grupos de probabilidad.
- Modelo supervisado de regresión logística, calibración independiente, comparación con prevalencia y el índice inicial, registro de artefactos, datos de referencia, versión y huella del dataset.
- Activación manual en modo sombra, persistencia de la línea base en paralelo, reversión, pausa por horizonte y auditoría.
- Diagnóstico de deriva de features recientes frente a las estadísticas de entrenamiento.
- Pantalla **Centro de Comando → Predicción** con habilitación de fuente, emisiones, resultados, evaluación y modelos; controles según rol.

## Puesta en marcha

1. Aplicar las migraciones `17_predictive_cycle.sql` y `18_predictive_multihazard.sql` con el mecanismo existente (`python -m app.migrate` desde `apps/api`, o `RUN_MIGRATIONS_ON_START=true` en el despliegue). Si 17 ya está aplicada, ejecutar solo las pendientes. Ambos directorios contienen copias idénticas. La migración 18 conserva los registros y permisos antiguos como `fire`, refuerza las referencias al riesgo exacto y no activa riesgos nuevos. No modificar migraciones ya aplicadas ni marcar las nuevas como baseline de una base existente que aún no tiene estas tablas.
2. Desplegar API y frontend. No requiere instalar otra librería de ML: el entrenamiento y la inferencia utilizan Python estándar.
3. Un administrador entra en **Predicción**, elige el riesgo y horizonte y autoriza explícitamente la consulta a Open-Meteo con las coordenadas de los nodos de su organización. Para PM2.5, el consentimiento indica Calidad del Aire/CAMS. La fuente está deshabilitada por defecto. Esta habilitación se audita y es independiente por riesgo y horizonte. `OPEN_METEO_AIR_QUALITY_URL` permite configurar la fuente de aire; `OPEN_METEO_API_KEY` utiliza su endpoint comercial cuando está presente.
4. Pulsar **Generar pronóstico**. Si la fuente aún está deshabilitada, un administrador puede autorizarla con el checkbox y este botón la habilita y emite en una misma operación. No requiere entrenar previamente un modelo: el pronóstico ambiental inicial usa variables futuras reales del proveedor y un índice heurístico explícito. La emisión manual se limita al riesgo y horizonte seleccionados. Se procesa cada nodo con `pipeline_enabled=true`, dentro de Misiones y sin tags `demo`, `simulator`, `fixture` o `simulated`. Si no hay nodos aptos, se muestra la causa. Una emisión por día UTC, nodo, horizonte y versión evita sobreponderar reintentos.
5. Para emisión programada, establecer `PREDICTIVE_ENABLED=true` en el entorno de la API. El scheduler existente del pipeline debe estar activo y la organización habilitada en sus ajustes de telemetría. Esta variable nunca habilita la fuente de un tenant que no dio su autorización. En Docker Compose ya se pasa la variable al contenedor.
6. Registrar incidentes del riesgo seleccionado aunque no haya alertas. Para un período sin incidente, indicar una cobertura que incluya toda la ventana pronosticada. La evidencia requiere fecha, fuente, referencia única por riesgo, notas, verificador y declaración explícita de cobertura. Las fechas locales de la pantalla se envían con zona horaria.
7. Con suficiente evidencia, pulsar **Entrenar candidato**. Revisar evaluación, activar en sombra y seguir verificando resultados prospectivos. Mantener revisión humana de las decisiones operativas.

La emisión consulta los horizontes habilitados de la organización. Al activar un modelo dentro del mismo día, el siguiente intento conserva la emisión inicial y agrega la nueva versión, sin sobrescribirla.

## Aprendizaje sin fuga temporal

El entrenamiento utiliza exclusivamente pronósticos iniciales archivados y maduros. No reconstruye features históricas a partir de clima observado posterior. Ordena las muestras cronológicamente y separa aproximadamente 60% para entrenar, 20% para calibrar y 20% para test. Agrupa las fronteras por instante de emisión y elimina de entrenamiento/calibración las ventanas cuyo final alcance el bloque siguiente. La normalización procede solo del entrenamiento; la calibración y la elección del umbral, solo del bloque de calibración.

Se exigen al menos 120 muestras etiquetadas; cada bloque resultante debe contener al menos 20 muestras, 5 incidentes y 5 no incidentes. Estas cantidades son puertas operativas mínimas para evitar entrenamientos degenerados; no certifican validez estadística. El candidato debe mejorar Brier frente a la prevalencia del entrenamiento y al índice meteorológico usado como score comparativo, y lograr recall mínimo de 0,6 en test. El índice comparativo sigue siendo una heurística, no una probabilidad validada.

El test retrospectivo no acredita generalización espacial ni desempeño prospectivo. La activación permanece en sombra: muestra avisos para revisión, sin disparar automáticamente respuestas institucionales ni notificaciones externas. No hay modelo propio entrenado con datos ficticios o precisión inventada. Si faltan datos reales suficientes, la API devuelve un bloqueo explicativo y se mantiene la línea base.

## Interpretación de métricas

- **Desconocido:** una ventana madura sin evento positivo ni período negativo que la cubra completamente queda pendiente. La falta de reportes no crea una etiqueta negativa.
- **Ventanas:** una observación puede evaluar varios horizontes o emisiones solapadas. Los TP/FP/FN corresponden a ventanas, no al número de incendios únicos.
- **Eventos:** cada registro independiente se cuenta una vez por versión/horizonte, aunque lo anticipen varias emisiones. La anticipación usa el primer aviso previo que cubra su instante real de inicio. Los incidentes sin cobertura de una emisión se cuentan como omitidos.
- **Período:** cada versión se evalúa desde su primera emisión dentro del intervalo consultado. Los incidentes anteriores a la existencia de esa versión no penalizan al nuevo candidato.
- **Territorio:** los resultados se emparejan por nodo y centro histórico del área. Mover un nodo no etiqueta retroactivamente pronósticos de otra ubicación. La referencia de un incidente debe identificar un registro real, evitando registrar varias veces el mismo hecho.
- **Brier y calibración:** solo se calculan sobre probabilidades de modelos supervisados, no sobre el índice heurístico. Se muestra el tamaño de cada grupo de calibración.
- **Deriva:** exige al menos 20 features recientes. Una diferencia de medias de al menos 2 desviaciones de entrenamiento en alguna feature marca revisión. Esto detecta un cambio de distribución, no demuestra caída de precisión; no hace reentrenamiento ni reversión silenciosos.

La evaluación está acotada a 10.000 predicciones y 10.000 observaciones por consulta. Si excede el límite, exige reducir el período, en vez de publicar métricas truncadas. La pantalla consulta 90 días; el entrenamiento usa 180 por defecto, configurable hasta 730 mediante la API. Las primeras 100 emisiones se consultan para el tablero, que muestra 30 y explicita el límite.

## Contratos de API

| Ruta | Uso | Rol |
|---|---|---|
| `GET /predictions?horizon_hours=24&limit=100` | Ledger reciente de la organización | Usuario autenticado |
| `POST /predictions/run` | Emisión idempotente de horizontes habilitados | Admin / operador |
| `GET /predictions/evaluation?horizon_hours=24&days=90` | Métricas y registro de modelos | Usuario autenticado |
| `GET /predictions/observations` | Evidencia independiente | Usuario autenticado |
| `POST /predictions/observations` | Verificación con fechas zonificadas y cobertura explícita | Admin / operador |
| `GET /predictions/settings` | Fuente habilitada y modelo por horizonte | Usuario autenticado |
| `POST /predictions/models/train` | Candidato supervisado con evaluación temporal | Admin |
| `POST /predictions/models/deploy` | Habilitación, pausa, activación o reversión | Admin |

Para habilitar, `/models/deploy` exige `enabled=true`, `external_weather_consent=true`, `horizon_hours` y `hazard` (por compatibilidad, omitir `hazard` significa `fire`). `model_id=null` selecciona el índice inicial; un UUID selecciona un candidato elegible de la misma organización, riesgo y horizonte. Las consultas de ledger, evaluación y observaciones aceptan `?hazard=hydric`, `health_heat`, `health_air` o `fire`. El entrenamiento y la verificación incluyen `hazard` en el JSON. `POST /run?hazard=hydric` emite solo ese riesgo; sin filtro, emite todos los habilitados, como el scheduler. Si una fuente falla, los otros riesgos pueden emitirse y se devuelve el error del riesgo sin cobertura. Pausar utiliza `enabled=false`. La base impide actualizaciones y eliminaciones de emisiones, observaciones y artefactos. Las verificaciones conflictivas y las referencias duplicadas devuelven 409. Entrenamientos y emisiones manuales tienen límites de solicitudes.

## Límites actuales y próximas extensiones

El modelo inicial usa meteorología futura. Aún no incorpora combustible, topografía, usos del suelo, fuentes de ignición o series IoT como features del modelo supervisado. Su eficacia real debe demostrarse con evidencia del territorio y suficiente cobertura, incluidas temporadas distintas. Las etiquetas son verificadas por operadores y requieren un protocolo de calidad de campo; la aplicación no puede garantizar que una declaración humana sea correcta.

El proveedor no entrega una hora de emisión del modelo en este contrato. Se conserva la hora de recepción, se declara desconocida la hora de emisión del proveedor y se registra el límite de cache de 5 minutos; la serie exacta utilizada queda archivada. Los nodos virtuales aportan contexto meteorológico modelado, no mediciones físicas.

Para ampliar a crecidas fluviales se necesitan niveles y caudales observados, umbrales de estaciones, cuencas, drenaje, relieve y evidencia de desborde. Para brotes epidemiológicos se necesitan series de casos agregados, vigilancia entomológica cuando corresponda, demora de notificación y objetivos/horizontes propios. Estos objetivos aún no están implementados y no se deducen del clima o PM2.5. Antes de pasar del modo sombra a decisiones automáticas, validar prospectivamente, por territorio, costos de errores y criterios de respuesta con operaciones.

## Validación local

Las pruebas cubren features futuras, datos incompletos, unidades, etiquetas desconocidas, nodos movidos, eventos omitidos, calibración, purga temporal, independencia del test, bloqueos de entrenamiento, deriva, permisos, aislamiento, habilitación de fuentes e idempotencia. Las pruebas de navegador interceptan las respuestas y bloquean destinos HTTPS externos; no realizan envíos reales de coordenadas. La migración y las consultas se verificaron con un parser PostgreSQL; no se aplicaron a producción. Docker está instalado, pero su daemon local no estaba disponible para una prueba de migración en PostGIS real.

La extensión añade pruebas de features a 6/24/72 h, mezcla de etiquetas/modelos, autorización independiente, persistencia multirriesgo, falla parcial de fuentes, ventana pluvial futura y contrato del proveedor de aire. Cinco escenarios de navegador verifican el ciclo, la selección de riesgos, consentimiento independiente, entrenamiento y permisos. No se ejecutan consultas reales a proveedores ni se afirma precisión operativa sin datos locales.

Verificación local después de corregir la generación y el desplazamiento: 383 pruebas de API y ocho escenarios de navegador. Se valida el primer pronóstico sin entrenamiento, la conservación de resultados cuando falla la evaluación, la serie hora por hora y el desplazamiento hasta el final en escritorio. Chequeo de tipos y build de producción aprobados. La migración 18 está sincronizada byte a byte entre ambos directorios; la migración y las 27 consultas del servicio/router pasaron el parser PostgreSQL. Esto verifica sintaxis y contratos simulados; sigue pendiente validar prospectivamente con evidencia territorial.

## Fuentes técnicas

- [Variables horarias y pronóstico de Open-Meteo](https://open-meteo.com/en/docs).
- [Contrato de calidad del aire y resolución de CAMS vía Open-Meteo](https://open-meteo.com/en/docs/air-quality-api).
- [Validación temporal, scikit-learn](https://scikit-learn.org/stable/modules/cross_validation).
- [Calibración de probabilidades, scikit-learn](https://scikit-learn.org/stable/modules/calibration.html).

Las referencias sustentan contratos y metodología; el código no añade scikit-learn como dependencia.
