# Corrección de nodos y red inicial · 2026-09-09

## Causas confirmadas en el código

- `routers/pipeline.py` declaraba una ruta `get_settings` que reemplazaba el import homónimo de configuración. Al armar la respuesta de GET/PATCH `/pipeline/settings` se intentaba leer `nasa_firms_key` de una coroutine y se producía un error 500.
- POST `/devices` descartaba `telemetry_mode`, `marker_shape`, `zone_id`, `pipeline_enabled` y `telemetry_config`. Los nodos virtuales se guardaban con el valor por defecto MQTT; ejecutar el pipeline no les consultaba Open-Meteo.
- GET `/devices` tampoco devolvía esos campos ni las últimas lecturas. Los valores por defecto del esquema ocultaban la configuración almacenada.
- El panel esperaba tres consultas con `Promise.all`. Si fallaba configuración, también descartaba la lista de nodos que había respondido correctamente.
- El navegador interrumpía `/pipeline/run` a los 30 segundos, aunque la ejecución espera proveedores externos por cada nodo. Estas operaciones ahora tienen 180 segundos; no se reintentan automáticamente solicitudes de creación.

## Cambios

El alta conserva todos los campos y no ejecuta Argon2 sobre el loop de la API. Los identificadores repetidos devuelven 409. Las referencias a zonas y tipos se validan dentro de la organización y se aplica el límite de dispositivos de la licencia. Se implementa PATCH para corregir fuente, zona y configuración de nodos existentes.

El panel conserva respuestas parciales, muestra el fallo del proveedor cuando una ejecución es parcial y vuelve a consultar la lista tras un fallo del bootstrap. Si la red se creó pero la ejecución falló, indica que debe reintentarse el pipeline, no crear otra red.

Las ejecuciones se cierran como fallidas si falla la consulta inicial de dispositivos. Los nodos virtuales también se consideran offline cuando sus lecturas caducan durante una ejecución del pipeline.

## Aplicación en el servidor

Esta corrección local no modifica la base publicada ni despliega servicios.

1. Publicar backend y frontend con estos cambios.
2. Aplicar `23_repair_virtual_device_modes.sql` con el ejecutor habitual (`python -m app.migrate` desde `apps/api` en el entorno del servidor). Si el servicio usa `render-start.sh` con `RUN_MIGRATIONS_ON_START=true`, se aplica al arrancar.
3. Verificar GET `/pipeline/settings` y GET `/devices` con una sesión autorizada. Los nodos virtuales deben devolver `telemetry_mode=open_meteo`.
4. Ejecutar el pipeline una vez sobre la red existente. Verificar nuevas lecturas, `last_seen`, `last_pipeline_status=ok` y estado online. Un proveedor sin respuesta debe producir una ejecución parcial y un detalle de error; no se fabrican lecturas.
5. Si se requieren actualizaciones continuas, activar la ejecución automática en la política del pipeline y comprobar que el scheduler esté habilitado en el backend.

La migración repara solamente nodos MQTT sin lecturas, sin `last_seen`, con configuración vacía y con las etiquetas específicas de los dos flujos virtuales afectados. No los pone online ni infiere una zona perdida. Para nodos que no cumplan esos criterios, revisar individualmente su fuente desde el panel. No recrear nodos existentes.

## Verificación local

- Regresiones HTTP con FastAPI y base/proveedor simulados: alta y lectura virtual, identificadores duplicados, aislamiento de organizaciones, PATCH de fuente, GET/PATCH de configuración, bootstrap, persistencia antes de estado online y cierre de ejecuciones fallidas.
- Pruebas existentes relacionadas de contratos de telemetría, territorio, suscripciones, seguridad y compilación de módulos.
- Compilación de producción del frontend.

La migración y el recorrido contra la base y proveedores del servidor publicado requieren verificación después del despliegue. Los errores concretos de conexión de Render no se atribuyen al código sin sus registros de ejecución.
