# Meteorología gratuita: NASA POWER y Open-Meteo

AG consulta históricos diarios de NASA POWER sin clave. Open-Meteo conserva el
pronóstico y las lecturas de nodos virtuales. No se modifica la fuente de los
nodos físicos MQTT ni se generan lecturas sintéticas.

## Despliegue

Publicar API y frontend con estos cambios. Aplicar la migración
`apps/api/migrations/24_weather_cache.sql` usando el runner habitual
`python -m app.migrate` antes de iniciar la API. El arranque en Render la aplica
automáticamente si `RUN_MIGRATIONS_ON_START=true`. No requiere nuevas variables.
No configurar URLs customer de Open-Meteo si no se dispone de clave comercial:
conservar `https://api.open-meteo.com/v1/forecast` para el pronóstico.
La variable de archivo Open-Meteo ya no interviene en los históricos de AG.

En AG, procesar un lote y abrir Ver serie. Cada día identifica su fuente.
Si Open-Meteo responde 429, el histórico NASA se guarda como resultado parcial;
no se producen recomendaciones basadas en pronósticos ausentes.
Los nodos virtuales todavía dependen de Open-Meteo: NASA no reemplaza datos
actuales ni garantiza resolver el 429 del servidor. Cada corrida del pipeline
consulta ahora una sola vez por lote de hasta 50 nodos en lugar de una vez por
nodo, así que el consumo del cupo deja de crecer con la cantidad de nodos.

## Cálculos y limitaciones

NASA POWER entrega datos modelados en hora solar local (LST), distinta de la
hora civil argentina usada por Open-Meteo. Son estimaciones regionales, no sensores.
Se usan T2M_MAX, T2M_MIN, RH2M, WS2M, PS, ALLSKY_SFC_SW_DWN y PRECTOTCORR.
La ET0 histórica se calcula localmente mediante FAO-56 Penman-Monteith diario,
G=0 y presión de vapor derivada de humedad relativa media (ecuación 19).
Radiación en MJ/m²/día; si NASA devuelve kWh/m²/día se convierte por 3,6.
No se sustituyen valores -999, nulos o no finitos por cero. Se omiten días incompletos.
Los acumulados incompletos se advierten y no generan recomendaciones retrospectivas
ni una etapa fenológica. NASA puede publicar los días recientes con retraso.

## Caché

PostgreSQL guarda solamente respuestas meteorológicas públicas y pausas por 429.
Claves SHA-256 incluyen parámetros y credencial sin guardar la clave en texto.
Open-Meteo: pronóstico 15 minutos; nodos actuales 15 minutos, que es cada
cuánto Open-Meteo actualiza el bloque `current` (campo `interval`). La lectura
guardada lleva la hora de la corrida; el dato de origen puede tener hasta 15
minutos, como ya ocurría antes de la caché.
Las lecturas actuales de todos los nodos virtuales de una corrida viajan en una
sola consulta con lista de coordenadas; Open-Meteo responde una entrada por
coordenada y se guarda la posición, no se emparejan por cercanía. Si devuelve
menos entradas que nodos, la corrida falla en lugar de asignar la lectura de
otra ubicación. Los nodos de una misma zona caen en la misma celda del modelo
(~11 km): la respuesta trae la coordenada de la celda, no la del nodo.
NASA: bloques mensuales completos pasados 30 días; parciales/recientes 1 hora.
Las respuestas expiradas no se sirven como actuales. La pausa del proveedor se
conserva entre reinicios. Se eliminan entradas vencidas al escribir en la caché.
Si falla la caché, se registra el problema y se consulta la fuente; la caché por sí
sola no garantiza disponibilidad ni deduplicación simultánea entre varios workers.

## Referencias

- https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- https://www.fao.org/4/x0490e/x0490e07.htm
- https://www.fao.org/4/x0490e/x0490e08.htm (ejemplo 18, ET0 3,88 mm/día)
- https://open-meteo.com/en/terms (API gratuita para uso no comercial)
