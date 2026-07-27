# Copernicus y sanidad forestal del norte de Misiones

## 1. Por qué la capa Copernicus aparecía deshabilitada

EcoNexo no puede usar una URL WMS universal. Sentinel Hub requiere una configuración propia dentro de Copernicus Data Space y entrega un `INSTANCE_ID`. La URL resultante tiene este formato:

```text
https://sh.dataspace.copernicus.eu/ogc/wms/INSTANCE_ID
```

Desde la versión 1.0.0-rc.2 la URL y los nombres de capas se guardan por organización en PostgreSQL. Ya no es obligatorio recompilar el frontend ni publicar una variable `NEXT_PUBLIC_COPERNICUS_WMS_URL`.

### Configuración

1. Crear una configuración Sentinel Hub en Copernicus Data Space.
2. Definir las capas de interés, por ejemplo color natural, NDVI, humedad y área quemada.
3. En EcoNexo abrir `Admin Core > Fuentes SpaceAI`.
4. Pegar la URL WMS completa.
5. Pulsar `Probar GetCapabilities`.
6. Copiar los nombres exactos informados por la instancia en los cuatro campos de capa.
7. Activar `Copernicus Sentinel-2 WMS` y guardar.

La API limita la prueba al dominio oficial `sh.dataspace.copernicus.eu` para evitar solicitudes SSRF a destinos arbitrarios.

## 2. San Antonio y radar meteorológico

No se presenta un radar como detector directo de plagas. EcoNexo incorpora como referencia regional el radar meteorológico de Bernardo de Irigoyen, cuya localidad se encuentra aproximadamente a 27 km del punto de referencia de San Antonio. EcoNexo no presenta esas coordenadas como posición exacta de la antena. El radar aporta contexto de lluvia, tormentas, movimiento de partículas y condiciones para programar recorridas.

Una señal radar no identifica por sí sola una especie, una infestación ni el daño de un lote. La vigilancia fitosanitaria debe combinar:

- recorridas de campo;
- fotografías georreferenciadas;
- trampas y capturas;
- especie forestal, edad y superficie afectada;
- síntomas observados;
- muestras con trazabilidad;
- revisión por referentes fitosanitarios o laboratorio;
- integración con SENASA/SINAVIMO cuando corresponda.

## 3. Lectura preventiva

El módulo calcula tres indicadores de priorización, sin valor diagnóstico:

- ambiente cálido y húmedo;
- estrés de la forestación;
- ventana meteorológica compatible con vuelo o dispersión.

Los resultados solamente indican dónde conviene reforzar observación. No reemplazan identificación taxonómica, análisis de laboratorio ni una declaración oficial de presencia de plaga.
