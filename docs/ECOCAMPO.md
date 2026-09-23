# EcoCampo

EcoCampo es un módulo independiente (`ecocampo`), con navegación y autorización propias. EcoNexo AG conserva su nombre y el módulo `agro`. Ambos comparten los lotes existentes, sin duplicar datos. El plan `agro_productor` ahora cuesta **USD 400 por mes** (precio mínimo y máximo iguales). No activa ni cobra suscripciones automáticamente. Los planes que ya incluían agro mantienen EcoNexo AG. El plan Productor incluye ambos módulos; EcoCampo también puede habilitarse expresamente por organización.

## Uso

1. Abrir Dashboard > EcoCampo y crear un lote con cultivo o «Pastizal / uso ganadero».
2. EcoCampo selecciona automáticamente el primer lote. Las secciones Evaluación de aptitud, Presupuesto forrajero, Monitoreo NDVI e Historial están visibles desde el inicio. En Monitoreo satelital, pegar su geometría GeoJSON Polygon, coordenadas WGS84 longitud/latitud y anillo cerrado. Solo un anillo, 4–500 vértices, máximo 0,2 grados por lado. PostGIS verifica validez y superficie.
3. Consultar los últimos 30 días. Se guardan geometría, serie y procedencia; hay caché de una hora por organización/lote/polígono. «Usar observación» copia fecha, NDVI y cobertura al formulario de evaluación.
4. En Evaluación de aptitud, completar referencia estacional comparable y evidencia de suelo, agua, erosión, anegamiento, exposición a plaguicidas y forraje. Dejar desconocidos como «Sin verificar». Usar «Procesar evaluación y guardar». En Presupuesto forrajero, ingresar las mediciones y usar «Calcular y guardar presupuesto».
5. Consultar historial. Cada resultado guarda versión del método, superficie, cultivo y fecha de evaluación. Es una evaluación histórica: actualizar evidencia antes de usarla para nuevas decisiones.

Los lotes agrícolas conservan fenología, balance hídrico, pronóstico y alertas existentes. Los pastizales usan NDVI y presupuesto forrajero; no se les aplican coeficientes de fenología de un cultivo arbitrario.

## Método y alcance

- NDVI Sentinel-2 L2A mediante Copernicus Statistical API, B08/B04, máscara SCL 4/5/6. Excluye nubes, sombras y nieve; mantiene agua para no ocultar superficies sin vegetación. Grilla 0,0001 grados; cobertura válida conservadora sobre la grilla solicitada, no equivale a la fracción exacta del polígono irregular.
- NDVI relativo a referencia aportada por el usuario: no se construye automáticamente una climatología. Filtros operativos: antigüedad máxima 30 días, cobertura mínima 70%, diferencia ±0,15. Son criterios internos NO calibrados por región ni normas OMS/CONICET.
- NDVI no es rendimiento ni calidad de forraje. El módulo no inventa toneladas/ha ni recomienda carga ganadera basándose solo en vegetación verde.
- Presupuesto forrajero = superficie × materia seca medida × aprovechamiento / demanda diaria por animal / días. No contempla crecimiento futuro, reservas ni suplementos. Requiere especies aprovechables verificadas; admite cero forraje y evita división por cero.
- Aptitud preliminar: datos insuficientes, condicionado por riesgos, o potencial favorable con evidencia completa. No certifica aptitud legal, rentabilidad, inocuidad ni sanidad animal. Los factores de campo son declarados, no análisis de laboratorio automáticos.
- No hay refresco satelital programado: el usuario consulta desde el lote. No se han agregado cobros automáticos.

## Fuentes

- CONICET, estimación remota de productividad de pastizales NEA: https://bicyt.conicet.gov.ar/fichas/produccion/12086803
- INTA, modelos de productividad, disponibilidad y calidad de forraje: https://repositorio.inta.gob.ar/handle/20.500.12123/5834
- OMS/FAO, gestión de plaguicidas (marco sanitario; no fuente de rendimiento agrícola): https://www.who.int/publications/b/57151
- Copernicus Statistical API: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Statistical/Examples.html

## Puesta en marcha

Aplicar las migraciones del API con `python -m app.migrate` desde `apps/api`, incluidas `25_ecocampo.sql` y `26_ecocampo_independent_module.sql`, y desplegar API y web juntos. El arranque Render ya usa ese ejecutor. No ejecutar solo la migración 25 en una base sin las migraciones anteriores.

Configurar `COPERNICUS_CLIENT_ID` y `COPERNICUS_CLIENT_SECRET` de CDSE en el servidor (nunca en el frontend). Se usa el cliente OAuth existente. Sin credenciales o cuota disponible, el endpoint responde 503 y no genera datos falsos; sigue disponible la carga de evidencia externa.

API: GET/POST `/ecocampo/lots` para lotes; GET/POST `/ecocampo/lots/{id}/assessments` para evaluaciones; GET/POST `/ecocampo/lots/{id}/ndvi` para estadísticas. Requieren licencia activa y módulo ecocampo. Las rutas antiguas se conservan como alias con el mismo control de acceso. Solo admin/operador escriben; las lecturas y escrituras verifican organización del lote.

## Validación

`python -m pytest tests/test_ecocampo.py tests/test_agro.py tests/test_subscriptions_and_notifications.py`

`npm run typecheck` y `npm run build` desde `apps/web`.

Las pruebas del proveedor usan HTTP simulado. La migración PostGIS y una consulta Copernicus real deben verificarse en el entorno conectado antes de dar por validada la operación productiva.
Prueba de interfaz: `npx playwright test --config playwright.ecocampo.config.ts`. Usa una API simulada y verifica navegación separada, selección automática, guardado de evaluación, presupuesto e historial. Opcionalmente `E2E_BROWSER_CHANNEL=msedge` usa Edge instalado.
