# Pipeline de telemetría rc.6

## Objetivo

Conectar el Admin Core con el Centro de Comando mediante una ejecución trazable que actualiza nodos, lecturas, detecciones satelitales, reglas y alertas.

## Modos de nodo

- `mqtt`: dispositivo físico conectado a un broker.
- `manual`: lecturas cargadas por un operador.
- `open_meteo`: nodo virtual de contexto modelado; no representa hardware instalado.

## Marcadores

Cada dispositivo guarda `marker_shape` con uno de estos valores:

- `circle`
- `square`
- `triangle`

El mapa usa esa forma, el estado del nodo y su geocerca para dibujarlo.

## Rutas

```text
GET   /pipeline/settings
PATCH /pipeline/settings
POST  /pipeline/run
GET   /pipeline/runs
POST  /pipeline/bootstrap
GET   /devices
POST  /devices
PATCH /devices/{id}
POST  /devices/{id}/readings
GET   /devices/{id}/readings
```

## Persistencia

La migración 14 incorpora configuración de telemetría en `devices`, ajustes por organización en `telemetry_pipeline_settings`, historial en `pipeline_runs` y deduplicación de `satellite_detections`.

## Actualización en producción

- La API inicia el scheduler cuando `PIPELINE_SCHEDULER_ENABLED=true`.
- Cada organización conserva el interruptor **Ejecución automática**: solo las que lo habilitan ejecutan su pipeline en el intervalo configurado.
- `NASA_FIRMS_KEY` habilita focos reales; sin la clave se publica cero detecciones, nunca fixtures de demo.
- Los servicios externos que publiquen detecciones deben enviar `X-Internal-Service-Token`; el valor debe coincidir con `INTERNAL_SERVICE_TOKEN` del API.

## Seguridad y precisión

- Todos los recursos se filtran por `org_id`.
- Las coordenadas deben pertenecer a Misiones.
- Los nodos Open-Meteo se rotulan como contexto modelado.
- Los focos FIRMS no equivalen por sí solos a incendio confirmado.
- El fallback de área quemada no se presenta como perímetro oficial.
- Las corridas y cambios administrativos quedan auditados.
