# Marco operativo de incendios forestales en Misiones

## Alcance de esta integración

EcoNexo incorpora un módulo preventivo para **focos de incendio forestal y humo**. El módulo combina señales térmicas satelitales, meteorología, calidad del aire, dispositivos IoT, reportes georreferenciados y verificación humana. Una detección automática se presenta como **señal a verificar**, no como incendio confirmado ni como comunicación oficial.

## Referencias públicas verificadas

A la fecha de esta edición no se identificó en las fuentes oficiales consultadas una norma provincial publicada con el título específico “ley de lectura de incendios por aparatos o plataformas satelitales”. Por esa razón, EcoNexo no asigna un número de ley no verificado. El diseño se alinea con el marco público disponible:

- Ley Nacional 26.815 de Manejo del Fuego y modificatorias.
- Ley provincial XVI-N°65 (antes Ley 3751), que crea e implementa el Plan Provincial de Manejo del Fuego, y Decreto 2101/00 que aprueba su plan operativo.
- Medidas provinciales de emergencia ígnea y coordinación interinstitucional.
- Plan Provincial de Manejo del Fuego y Dirección de Alerta Temprana.
- Monitoreo aéreo, identificación de columnas de humo y constatación territorial.
- Uso provincial de análisis de imágenes satelitales para orientar controles ambientales.
- Índice de Peligro de Incendios basado en FWI, junto con observaciones locales.

Fuentes oficiales de referencia:

- https://misiones.gob.ar/alerta-temprana-drones-y-respuesta-rapida-misiones-refuerza-su-esquema-de-prevencion-de-incendios/
- https://ordenamientoterritorial.misiones.gob.ar/plan-provincial-de-manejo-del-fuego/
- https://misiones.gob.ar/ante-el-alto-riesgo-de-incendios-en-toda-la-provincia-el-gobierno-de-misiones-insta-a-evitar-el-uso-del-fuego-y-extremar-las-medidas-de-prevencion/
- https://misiones.gob.ar/ecologia-refuerzan-el-control-forestal-con-operativos-en-la-zona-centro-y-sur-de-la-provincia/
- https://ecologia.misiones.gob.ar/ecologia-desplego-un-operativo-aereo-integral-para-el-monitoreo-ambiental-el-control-forestal-y-la-prevencion-de-incendios/
- https://misiones.gob.ar/ante-un-escenario-de-riesgo-extremo-de-incendios-en-misiones-el-ministerio-de-ecologia-convoco-a-una-mesa-de-coordinacion-preventiva/

## Reglas de comunicación

1. “Punto caliente” no equivale automáticamente a “incendio confirmado”.
2. Las imágenes y modelos satelitales se contrastan con cámaras, drones, sensores, brigadas, reportes o autoridad competente.
3. La ausencia de una detección satelital no garantiza ausencia de fuego: pueden existir nubes, latencia, resolución insuficiente o incendios pequeños.
4. Los mensajes generados por Alerta IA requieren revisión humana previa.
5. Ante fuego o humo visible, la plataforma prioriza el 911 como canal inmediato. En protocolos institucionales también pueden documentarse 100 (Bomberos), 103 (Defensa Civil) y 105 (Emergencia Ambiental), según la instrucción vigente de la autoridad contratante.
6. EcoNexo conserva fuente, hora, coordenadas, usuario, texto enviado y evidencia asociada para auditoría.

## Índice meteorológico

El riesgo de propagación no se deriva solo de los focos térmicos. El módulo contextualiza temperatura, humedad relativa, viento, ráfagas, lluvia y humedad del suelo. El FWI oficial o local debe incorporarse como fuente externa cuando exista un endpoint autorizado; EcoNexo no reemplaza su cálculo oficial con una aproximación propia sin calibración territorial.

## Política de datos de lanzamiento

- En `ENVIRONMENT=production`, si falta `NASA_FIRMS_KEY` o la consulta falla, EcoNexo muestra “fuente no disponible” y no reemplaza la fuente real con datos simulados.
- Los fixtures satelitales solo pueden habilitarse expresamente en desarrollo o demostración.
- La geometría territorial productiva debe sincronizarse desde GeoRef Argentina mediante `/territory/sync-georef`; el polígono empaquetado es únicamente un fallback operativo.
- Las detecciones externas a Misiones se excluyen de mapas, KPIs, alertas, snapshots e informes.

## Revisión jurídica pendiente

Antes de licenciar el módulo a un organismo público o comunicar resultados como parte oficial, un profesional jurídico y la autoridad contratante deben validar:

- normativa provincial vigente;
- decretos de emergencia aplicables;
- protocolo de escalamiento;
- responsables de validación;
- retención de evidencia;
- uso de logos y denominaciones oficiales;
- tratamiento de datos de reportes comunitarios.
