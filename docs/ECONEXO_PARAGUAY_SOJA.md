# Econexo Paraguay Soja

Apartado independiente en Dashboard > Econexo Paraguay. Cultivo fijo soja. Mapa base OpenStreetMap con límite orientativo Natural Earth 1:10m (dominio público), coordenadas editables y polígono del lote. No utiliza el recorte de Misiones ni mezcla sus indicadores en esta vista.

## Evaluación e informes

Evidencia declarada de pH, temperatura de suelo, nutrición, drenaje, agua, compactación, erosión, calidad de semilla, inoculación y sanidad. La variedad, grupo de madurez, fecha y etapa requieren validación local. Rangos bibliográficos orientativos y filtros operativos sin calibración por región. No estima rendimiento ni indica dosis. Falta de evidencia y fallas del pronóstico quedan visibles. Un pronóstico de 7 días no certifica aptitud de toda la campaña.

Pronóstico real Open-Meteo con America/Asuncion. Informe consultable, exportable a HTML imprimible (el navegador permite guardar PDF), y guardado por organización con evidencia, método y pronóstico originales. Usuarios con módulo agro y licencia activa consultan; solo admin/operador guardan. Historial limitado a 30 informes recientes.

## Satélite

Sentinel-2 L2A mediante Copernicus Process API, color natural, NDVI e índice de humedad. Consulta independiente por polígono de hasta 0,2 grados por lado y vértices dentro del límite orientativo de Paraguay. Estadísticas NDVI reutilizan el proveedor de EcoCampo. No se infiere rendimiento de NDVI. El límite de baja resolución puede rechazar lotes próximos a fronteras; confirmar coordenadas y reemplazar por una cartografía más precisa antes de uso catastral.

Se requiere OAuth Copernicus CDSE configurado en el servidor y cuota disponible. Las imágenes son composiciones de menor nubosidad de los últimos 30 días, no una toma en vivo; no se certifica despeje ni fecha única de adquisición. La pantalla informa errores sin reemplazar imágenes por simulaciones. Consulta manual, sin vigilancia programada.

## Despliegue

Aplicar `python -m app.migrate` incluyendo `28_paraguay_soy.sql`, y desplegar web/API juntas. No se modificaron credenciales ni producción. Los límites se incluyen en `apps/api/app/data/paraguay.geojson` y `apps/web/public/paraguay.geojson`, derivados de Natural Earth `ne_10m_admin_0_countries.geojson`: https://github.com/nvkelso/natural-earth-vector.

Verificar base PostgreSQL, generación de informe guardado y una consulta Copernicus real en el entorno conectado. Las pruebas locales con proveedores simulados no validan credenciales ni infraestructura productiva.

Fuentes agronómicas: FAO Ecocrop (Glycine max), https://ecocrop.apps.fao.org/ecocrop/srv/en/cropView?id=1150 y el material de protección vegetal del IPTA, https://www.ipta.gov.py/portada/informaciones/informacion-al-productor/soja/proteccion-vegetal/. Los umbrales de 20 °C suelo, 34 °C máxima, 2 °C mínima y 30 días de evidencia son filtros operativos iniciales; no constituyen normas paraguayas ni probabilidades calibradas.

