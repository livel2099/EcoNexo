# Observatorio SpaceAI: telemetría IoT + Open-Meteo + CAMS + GloFAS + FIRMS

Versión de implementación: **SpaceAI 1.0 · Matriz técnica 2026-06-03 · EcoNexo HTI 0.3**
Última actualización: **5 de agosto de 2026**

## 1. Propósito

El Observatorio de EcoNexo combina información de distinta naturaleza sin confundirla:

1. **Telemetría física** de los dispositivos registrados en EcoNexo.
2. **Contexto meteorológico modelado** para la coordenada exacta del nodo mediante Open-Meteo Forecast.
3. **Calidad del aire modelada** mediante Copernicus CAMS expuesto por Open-Meteo Air Quality.
4. **Contexto hidrológico modelado** mediante GloFAS expuesto por Open-Meteo Flood.
5. **Focos térmicos observados por satélite** mediante NASA FIRMS, ingeridos por el servicio satelital de EcoNexo.
6. **Evidencia ciudadana y alertas operativas** persistidas por la API.

El resultado es una lectura de apoyo para priorización territorial y alerta temprana. No es una estación regulatoria, un diagnóstico médico ni una declaración oficial de emergencia.

Documento técnico de referencia incluido en el repositorio:

- `docs/reference/SpaceAI_indicadores_amenaza_ambiental_salud_publica_v1.docx`

## 2. Flujo de datos por dispositivo

```text
Dispositivo seleccionado
        │
        ├─ /devices/{id}/readings ──► temp · humidity · pm25 · nivel
        │                                telemetría física
        │
        ├─ lat/lon ──► Open-Meteo Forecast
        │               temperatura · humedad · lluvia · viento · suelo · VPD · ET0
        │
        ├─ lat/lon ──► Open-Meteo Air Quality / CAMS
        │               PM2.5 · PM10 · CO · NO2 · SO2 · O3 · AOD · polvo · UV · AQI
        │
        ├─ lat/lon ──► Open-Meteo Flood / GloFAS
        │               caudal actual · media · máximo · percentil 75
        │
        └─ radio operativo ──► NASA FIRMS
                                focos 48 h · confianza · FRP · distancia
                                         │
                                         ▼
                           SpaceAI Health Threat Index
                                         │
                          alertas · snapshots · informes
```

La pantalla **Gemelo digital del nodo** compara la última lectura física con el valor externo de modelo. La diferencia se presenta como control de coherencia y nunca como calibración automática.

## 3. Variables ingeridas

### 3.1 Open-Meteo Forecast

| Familia | Variables utilizadas | Uso EcoNexo |
|---|---|---|
| Actual | temperatura, humedad relativa, temperatura aparente, precipitación, nubosidad, visibilidad | estado actual y estrés térmico |
| Viento | velocidad, dirección y ráfagas | propagación de incendio y operación de campo |
| Suelo | humedad superficial 0-1 cm | proxy de sequedad superficial |
| Balance atmosférico | déficit de presión de vapor (VPD), ET0 FAO | balance de humedad y demanda evaporativa |
| Horaria | 7 días previos + pronóstico | persistencia, PM2.5/lluvia 24 h y línea IA 12 h |
| Diaria | temperatura, lluvia, probabilidad, ráfagas, ET0 | acumulados de 7 días y tendencia |

Referencia oficial: <https://open-meteo.com/en/docs>

### 3.2 Open-Meteo Air Quality / Copernicus CAMS

| Variable | Unidad esperada | Uso EcoNexo |
|---|---:|---|
| PM2.5 | µg/m³ | promedio móvil/ventana 24 h y excedencia OMS |
| PM10 | µg/m³ | contexto respiratorio |
| CO, NO2, SO2, O3 | unidades provistas por la API | contexto atmosférico y evidencia secundaria |
| US AQI | índice | comunicación categórica, no porcentaje lineal |
| Índice UV | índice | escala específica de radiación |
| AOD y polvo | índice / concentración | evidencia de aerosol y humo potencial |

Referencia oficial: <https://open-meteo.com/en/docs/air-quality-api>

### 3.3 Open-Meteo Flood / GloFAS

EcoNexo utiliza series de caudal modelado para construir un **proxy de presión hídrica**:

- `river_discharge`
- `river_discharge_mean`
- `river_discharge_max`
- `river_discharge_p75`
- 30 días previos y 14 días de pronóstico

El índice compara el caudal actual y máximo previsto contra una mediana local de la serie y el percentil 75. No equivale al SPI oficial ni reemplaza avisos de autoridad hídrica, estaciones limnimétricas o antecedentes de inundación.

Referencia oficial: <https://open-meteo.com/en/docs/flood-api>

### 3.4 NASA FIRMS

Los focos de incendio **no se infieren desde Open-Meteo**. Provienen de detecciones térmicas de NASA FIRMS ingeridas por `services/satellite` y expuestas por `/satellite/detections`.

El observatorio resume:

- cantidad de focos en 48 h dentro del radio operativo;
- focos de alta confianza;
- FRP máximo;
- distancia al foco más cercano.

Referencia oficial: <https://firms.modaps.eosdis.nasa.gov/api/>

## 4. Índices SpaceAI implementados

### 4.1 Calidad del aire

- Base continua: PM2.5 24 h / 15 µg/m³.
- Base categórica complementaria: US AQI.
- Escalamiento por persistencia y confiabilidad de fuente.
- Recomendación: contrastar con sensor calibrado o estación regulatoria antes de comunicación pública.

### 4.2 Estrés térmico

- Índice de calor derivado de temperatura y humedad.
- Temperatura de bulbo húmedo como señal fisiológica complementaria.
- Categorías específicas; no se interpreta como porcentaje lineal.

### 4.3 Balance de humedad

Combina:

- humedad relativa;
- humedad superficial del suelo;
- lluvia reciente y prevista;
- VPD;
- evapotranspiración de referencia.

Sirve para observar sequedad o saturación ambiental. No es un índice clínico de moho ni una medición interior.

### 4.4 Incendio y humo

Combina:

- focos FIRMS;
- distancia, confianza y FRP;
- ráfagas;
- humedad relativa;
- humedad superficial del suelo;
- PM2.5, AOD y polvo.

Un foco térmico cercano puede elevar el dominio a R4/R5 según co-exposición y confianza. La validación de campo sigue siendo obligatoria.

### 4.5 Riesgo hídrico

Combina:

- precipitación 24 h;
- acumulados recientes y previstos;
- caudal actual/modelado;
- relación contra referencia histórica de la consulta;
- percentil 75 y máximo previsto.

Es un índice operativo preliminar, diseñado para calibrarse con climatología, estaciones y zonas inundables locales.

### 4.6 Radiación UV

Usa categorías específicas:

- 0-2: bajo;
- 3-7: requiere protección;
- 8-10: muy alto;
- 11 o más: extremo.

### 4.7 Aptitud eco-climática vectorial

Índice compuesto limitado a R3 sin evidencia entomológica o epidemiológica. Considera:

- temperatura en rango de aptitud aproximado;
- humedad relativa sostenida;
- lluvia reciente y prevista;
- persistencia ambiental.

Debe cruzarse con ovitrampas, índice larvario y casos humanos antes de escalar a alerta epidemiológica.

## 5. Escala R0-R5

Para indicadores continuos se aplica la matriz de excedencia relativa del documento técnico:

| Nivel | Regla | Lectura operacional |
|---|---|---|
| R0 | <80% | basal |
| R1 | 80-99% | vigilancia |
| R2 | 100-149% | alerta |
| R3 | 150-199% | amenaza alta |
| R4 | ≥200% | crítico operativo |
| R5 | regla específica | emergencia / escalamiento inmediato |

AQI, UV, calor, caudal, IDLH y otros indicadores no lineales usan sus categorías específicas.

## 6. Health Threat Index (HTI)

Cada dominio produce un score de severidad; la persistencia y la confiabilidad se integran después en el compuesto:

```text
Score_i = severidad ambiental normalizada (0-100)
```

La implementación agrega pesos por dominio y co-exposición:

```text
HTI = Σ(peso_i × score_i × persistencia_i × confianza_i) / Σ(peso_i)
```

Pesos actuales:

| Dominio | Peso |
|---|---:|
| Aire | 0,21 |
| Incendio/humo | 0,19 |
| Calor | 0,16 |
| Hídrico | 0,16 |
| Humedad | 0,11 |
| Vectorial | 0,10 |
| UV | 0,07 |

Estos pesos son parámetros de producto, no coeficientes clínicos validados. Deben calibrarse con incidentes reales y análisis retrospectivo.

Desde HTI 0.3, el nivel general se deriva exclusivamente del resultado compuesto. Un dominio R4/R5 conserva su alerta crítica específica, pero ya no fija por sí solo el HTI global en el piso exacto de 75; esto evita que, por ejemplo, radiación UV alta convierta automáticamente toda la situación ambiental en crítica.

## 7. Persistencia, caché y resiliencia

- Open-Meteo se consulta en paralelo por fuente.
- La caché del navegador se segmenta por coordenada y fuentes habilitadas.
- TTL configurable entre 2 y 180 minutos desde Admin.
- Si una fuente falla y existe caché, el observatorio la marca como lectura anterior.
- Si no existe dato, la UI muestra “no disponible”; no inventa valores.
- El snapshot persiste exactamente las observaciones, índices, fuentes y limitaciones usadas al decidir.

## 8. Variables de entorno

```env
NEXT_PUBLIC_OPEN_METEO_FORECAST_URL=https://api.open-meteo.com/v1/forecast
NEXT_PUBLIC_OPEN_METEO_AIR_URL=https://air-quality-api.open-meteo.com/v1/air-quality
NEXT_PUBLIC_OPEN_METEO_FLOOD_URL=https://flood-api.open-meteo.com/v1/flood
NASA_FIRMS_KEY=
```

Las URLs Open-Meteo son públicas. No colocar secretos en variables `NEXT_PUBLIC_*`. Para producción con cuotas, auditoría o control de egress, interponer un backend/Worker con caché y rate limiting.

## 9. Flujo operativo recomendado

1. Seleccionar nodo físico.
2. Revisar estado, batería, RSSI y antigüedad de telemetría.
3. Comparar lectura IoT y modelo por coordenada.
4. Revisar dominios R2 o superiores y evidencia.
5. Confirmar focos/avisos con fuente secundaria o inspección de campo.
6. Guardar snapshot sin activar alertas.
7. Validar por operador.
8. Activar señales internas o crear regla/geocerca.
9. Generar boletín o parte oficial con el snapshot congelado.
10. Registrar decisión y responsable en bitácora.

## 10. Limitaciones obligatorias

- Open-Meteo/CAMS/GloFAS aportan contexto modelado, no “datos del dispositivo”.
- NASA FIRMS detecta anomalías térmicas, no confirma por sí sola un incendio activo en superficie.
- Un valor ambiental alto no implica automáticamente exposición humana alta.
- Los umbrales internacionales no reemplazan normativa argentina o provincial.
- La métrica de 200% es una convención operacional, no una duplicación del riesgo clínico.
- Los informes deben conservar fecha, coordenada, fuente, metodología y limitaciones.
