# Fuentes geoespaciales de la demo EcoNexo

## Flujo de datos

La demo combina tres tipos de información que deben interpretarse por separado:

1. **Open‑Meteo Forecast API** aporta temperatura, humedad, precipitación, viento, nubosidad y humedad superficial del suelo para el centro operacional.
2. **Copernicus CAMS**, expuesto por Open‑Meteo Air Quality API, aporta material particulado, gases, aerosol óptico, polvo e índice UV.
3. **Copernicus Sentinel‑2**, expuesto mediante Sentinel Hub WMS, aporta imágenes reales y productos visuales sobre el mapa.

Los puntos de nodos, reportes, detecciones y alertas pertenecen al dataset operativo de EcoNexo. El frontend no los presenta como observaciones Copernicus.

## Capas disponibles

| Capa | Uso en la interfaz | Lectura recomendada |
|---|---|---|
| `TRUE_COLOR` | Contexto territorial | Composición visual en color natural |
| `NDVI` | Vigor vegetal | Contraste relativo de vegetación |
| `MOISTURE_INDEX` | Humedad de cobertura | Señal visual de humedad relativa |
| `NBR_RAW` | Inspección de áreas quemadas | Índice base para contraste de cicatrices |

Las capas se habilitan desde zoom 9. La interfaz muestra el estado de carga y no reemplaza una imagen ausente con datos ficticios.

## Actualización y resiliencia

- Open‑Meteo y CAMS se consultan en paralelo.
- La respuesta se conserva 10 minutos en `localStorage`.
- La actualización automática ocurre cada 15 minutos.
- Si una consulta falla y existe una lectura anterior, se muestra como **caché**.
- Si no existe lectura previa, la interfaz declara la fuente sin enlace.
- El WMS utiliza un intervalo móvil del último año y un límite de nubosidad del 80% para encontrar una escena disponible sin fingir actualidad instantánea.

## Límites metodológicos

- Los datos meteorológicos y CAMS describen contexto modelado; no son una confirmación de incendio, contaminación puntual o daño ambiental.
- Sentinel‑2 no es un flujo de video en vivo. “En vivo” en la interfaz indica una conexión activa al servicio, no una captura en tiempo real.
- NDVI, humedad y NBR son capas de apoyo visual. Una decisión operativa requiere correlación con fecha de adquisición, cobertura nubosa, sensores, reportes y validación humana.
- La detección de focos de la demo sigue siendo un dataset operacional separado; el mapa WMS no genera automáticamente esas detecciones.

## Seguridad

La URL WMS reutilizada de SAVIA es pública y no contiene credenciales. No se copiaron client secrets, tokens ni datos privados del proyecto. Para una instancia privada, la autenticación debe resolverse en un Worker o backend y nunca exponerse como variable `NEXT_PUBLIC_*`.

## Atribución

- [Open‑Meteo Forecast API](https://open-meteo.com/en/docs)
- [Open‑Meteo Air Quality API y Copernicus CAMS](https://open-meteo.com/en/docs/air-quality-api)
- [Copernicus Data Space Ecosystem — OGC API](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/OGC.html)
- [OpenStreetMap](https://www.openstreetmap.org/copyright)
- [CARTO basemaps](https://carto.com/attributions)
