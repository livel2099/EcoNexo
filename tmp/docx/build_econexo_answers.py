from __future__ import annotations

from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(r"C:\Users\Livel\Documents\ECONEXO\ECONEXO BETAa\ECONEXO BETA")
OUT = ROOT / "output" / "docx" / "Respuestas_Simulacro_EcoNexo_INTA_Misiones.docx"
OUT.parent.mkdir(parents=True, exist_ok=True)

EMERALD = "059669"
PETROL = "164E63"
GOLD = "F4B942"
CYAN = "22D3EE"
INK = "163238"
MUTED = "5E7075"
PALE_GREEN = "EAF8F2"
PALE_GOLD = "FFF7DF"
WHITE = "FFFFFF"


SECTIONS = [
    ("Problema y propuesta de valor", [
        ("¿Qué problema concreto de Misiones busca resolver EcoNexo?", "La información ambiental relevante está dispersa y llega en tiempos distintos. EcoNexo la reúne para convertir señales meteorológicas, satelitales y territoriales en alertas priorizadas y trazables sobre incendios y cambios de cobertura. El objetivo no es reemplazar a la autoridad: es reducir el tiempo entre la señal, la verificación y la decisión."),
        ("¿Por qué decidieron comenzar en Misiones?", "Misiones combina alta biodiversidad, actividad agroforestal, áreas protegidas y comunidades rurales expuestas a incendios y cambios de uso del suelo. Esa complejidad hace que un piloto bien delimitado produzca aprendizaje técnico y territorial valioso. La provincia también permite probar coordinación entre organismos, municipios, técnicos y productores."),
        ("¿Quién es el usuario principal de la plataforma?", "El usuario principal es el operador técnico de una institución con responsabilidad territorial: ambiente, gestión del riesgo, extensión rural o municipio. También hay vistas y funciones para administradores, técnicos de campo y productores. Cada perfil accede solamente a la información y las acciones que necesita."),
        ("¿Qué decisión permite tomar EcoNexo que actualmente se toma tarde?", "Permite decidir qué señal revisar primero, a quién derivarla y dónde verificarla. En vez de esperar a reunir manualmente clima, mapa, foco térmico y reporte de campo, el operador recibe un caso contextualizado, con nivel de riesgo, confianza, ubicación, fuentes y acción sugerida."),
        ("¿EcoNexo previene eventos, los detecta o ayuda a priorizar la respuesta?", "Hace las tres cosas, con alcances diferentes. Estima condiciones de riesgo para prevención, incorpora señales de eventos activos y prioriza la respuesta mediante reglas y contexto territorial. No promete impedir un incendio ni certificar por sí solo una infracción; aporta alerta temprana y apoyo a la decisión."),
        ("¿Qué diferencia existe entre EcoNexo y un mapa ambiental convencional?", "Un mapa convencional muestra capas. EcoNexo agrega procesamiento: normaliza fuentes, aplica reglas, calcula confianza, genera alertas, asigna responsables y registra confirmaciones, descartes y acciones. El valor está en el flujo operativo y la trazabilidad, no solamente en la visualización."),
        ("¿Por qué no alcanza con consultar directamente las fuentes públicas?", "Porque cada fuente tiene formato, escala, actualización y significado diferentes. Consultarlas por separado exige tiempo y conocimiento especializado, y no deja un expediente común. EcoNexo conserva la fuente original, pero automatiza la integración y presenta una lectura operativa que puede auditarse."),
        ("¿Cuál es el principal beneficio para un organismo público?", "Contar con una bandeja única de situaciones priorizadas, evidencia de respaldo y un historial de decisiones. Eso facilita coordinar equipos, justificar inspecciones, medir tiempos de respuesta y generar informes sin perder la procedencia del dato ni la intervención humana."),
        ("¿Cómo se relaciona EcoNexo con el sector productivo y forestal?", "Puede advertir condiciones de riesgo cercanas a lotes, plantaciones e infraestructura, y ofrecer a productores un canal de reporte y seguimiento. Para el sector forestal también aporta series e índices de vegetación como contexto. Las decisiones regulatorias y productivas siguen en manos de sus responsables."),
        ("¿Qué parte del producto funciona actualmente?", "Hoy funcionan la aplicación web y su backend, autenticación y roles, mapas y geocercas, ingesta de Open-Meteo, integración configurable con NASA FIRMS y Copernicus, dispositivos, reglas, alertas, puntajes de confianza, moderación, auditoría e informes. La clasificación automática y validada de deforestación sigue siendo alcance del piloto, al igual que las métricas territoriales reales."),
    ]),
    ("Incendios rurales y forestales", [
        ("¿EcoNexo calcula riesgo de incendio o detecta focos activos?", "Ambas capacidades son complementarias. El riesgo se estima con variables meteorológicas, antecedentes y exposición; los focos activos ingresan desde alertas térmicas como NASA FIRMS y desde reportes. Una condición de riesgo no prueba un incendio, y un foco térmico necesita contexto y verificación."),
        ("¿Qué variables de Open-Meteo utiliza para calcular el riesgo?", "La configuración actual contempla temperatura, humedad relativa, precipitación, velocidad y ráfagas de viento, además de variables de suelo cuando están disponibles. En el piloto se documentará la versión exacta del indicador, sus unidades, ventanas temporales y peso en cada regla."),
        ("¿Cómo influyen la temperatura, humedad, viento y precipitaciones?", "Temperaturas altas y humedad baja favorecen el secado del combustible; el viento aumenta propagación y dificultad de control; la lluvia reciente reduce el riesgo, según intensidad y acumulado. EcoNexo no interpreta una variable aislada: las combina en ventanas temporales y con el tipo de territorio."),
        ("¿Cómo se incorporan las alertas térmicas satelitales?", "Se consultan los registros de NASA FIRMS para el área de interés, se normalizan coordenadas, hora, satélite y confianza, y se correlacionan con clima, geocercas y reportes cercanos. La alerta conserva enlace y metadatos de origen para poder revisar la señal."),
        ("¿Cuál es el tamaño mínimo de un foco que puede identificarse?", "No debe expresarse como una superficie mínima garantizada. VIIRS ofrece píxeles de aproximadamente 375 metros y MODIS de 1 kilómetro para productos de fuego activo, pero un píxel no equivale al tamaño real del fuego. La detección depende de intensidad, horario, nube, ángulo y producto; se medirá localmente la sensibilidad."),
        ("¿Cómo diferencia una quema controlada de un incendio no autorizado?", "No puede determinarlo sólo con una firma térmica. La clasificación requiere cruzar permisos o avisos de quema, fecha, polígono, responsable, condiciones meteorológicas y confirmación territorial. Si el registro oficial no está integrado, EcoNexo debe rotular el caso como ‘evento térmico por verificar’, nunca como infracción."),
        ("¿Puede establecer distintos niveles de riesgo?", "Sí. La plataforma admite niveles configurables, por ejemplo R0 a R5 o bajo, medio, alto y crítico. Cada nivel se vincula con umbrales, evidencia mínima, destinatarios y protocolo de actuación, y puede adaptarse por institución y territorio."),
        ("¿Cómo prioriza dos incendios que ocurren simultáneamente?", "Combina severidad, confianza, velocidad del viento, cercanía a población, infraestructura, áreas protegidas y activos productivos, además de la capacidad de respuesta disponible. La fórmula debe acordarse con los organismos y quedar visible para que el operador pueda revisarla o escalar manualmente."),
        ("¿Puede estimar qué zonas productivas o forestales se encuentran amenazadas?", "Sí, mediante la intersección del evento y su área potencial de influencia con geocercas, lotes, plantaciones, caminos y otras capas autorizadas. En una primera etapa es una priorización espacial; cualquier modelo de propagación más complejo debe validarse antes de presentarse como pronóstico."),
        ("¿Cómo trabaja cuando existe nubosidad?", "Los sensores ópticos como Sentinel-2 pierden utilidad bajo nubes. EcoNexo marca esa limitación, evita interpretar píxeles contaminados y prioriza fuentes complementarias: alertas térmicas cuando estén disponibles, meteorología, sensores y reportes de campo. El dato faltante reduce la confianza, no se rellena como certeza."),
        ("¿Cuánto tarda en generar una alerta después de recibir un dato válido?", "La meta operativa es generar o actualizar la alerta dentro de los cinco minutos posteriores a recibir datos válidos. Ese tiempo mide procesamiento interno. No incluye la demora propia de la fuente en observar, procesar y publicar el fenómeno."),
        ("¿Quién recibe la alerta?", "Los destinatarios se definen por organización, geocerca, nivel y horario: operador de guardia, referente municipal, Defensa Civil, ambiente u otro rol acordado. La plataforma debe evitar difusión indiscriminada y registrar quién recibió, aceptó o derivó el caso."),
        ("¿Qué información contiene el aviso?", "Incluye tipo y nivel, ubicación y hora, fuentes, confianza, variables relevantes, bienes o áreas cercanas, imagen o mapa cuando exista y acción recomendada. También indica límites de la evidencia y un enlace al expediente para confirmar, descartar o escalar."),
        ("¿Qué acción debería realizar el destinatario?", "La acción depende del protocolo: revisar evidencia, contactar al referente local, solicitar verificación, derivar a emergencia o descartar con motivo. EcoNexo propone el siguiente paso, pero la institución define quién tiene autoridad para ejecutarlo."),
        ("¿Cómo se confirma que el incendio realmente existe?", "Mediante corroboración independiente: reporte técnico o ciudadano confiable, llamada a una fuente territorial, sensor, segunda observación o inspección. La confirmación registra responsable, hora, evidencia y ubicación. Una alerta satelital sola permanece como indicio."),
        ("¿Qué ocurre cuando una alerta es descartada?", "No se elimina. Cambia de estado, se registra el motivo y queda disponible para auditoría y evaluación de falsos positivos. Esa corrección sirve para ajustar reglas, pero no modifica automáticamente el modelo sin revisión y control de versiones."),
        ("¿Cómo se registran los incendios que EcoNexo no detectó?", "Se cargan como eventos conocidos mediante actas, reportes de campo o bases históricas y luego se comparan con las alertas emitidas. Esa matriz permite contar falsos negativos, investigar por qué faltó la señal y corregir cobertura, fuentes o umbrales."),
        ("¿Qué error sería más grave: una falsa alarma o no detectar un incendio?", "Depende del nivel y del protocolo, pero en incendios de alto impacto suele ser más grave omitir un evento real. Aun así, demasiadas falsas alarmas generan fatiga y reducen confianza. Por eso se usan niveles: señales débiles van a revisión y sólo evidencia suficiente activa escalamiento urgente."),
    ]),
    ("Cobertura vegetal y deforestación", [
        ("¿Cómo determina EcoNexo que ocurrió un cambio de cobertura vegetal?", "En el piloto se compararán observaciones corregidas y enmascaradas por nube, usando índices como NDVI, NDMI o NBR, diferencias temporales y polígonos persistentes. La señal se contrasta con estacionalidad, uso previo y datos territoriales. Hoy la plataforma visualiza índices e imágenes; el clasificador validado todavía debe desarrollarse."),
        ("¿Cómo distingue bosque nativo de una plantación forestal?", "No basta el color de una imagen. Se requiere una cartografía de referencia validada, historial temporal, patrón espacial, especies o inventario cuando exista y revisión experta. EcoNexo debe mostrar la clase de la fuente y su fecha; si hay ambigüedad, la alerta queda como cobertura por verificar."),
        ("¿Cómo diferencia un desmonte de una cosecha forestal autorizada?", "Cruza el cambio observado con el tipo de cobertura, permisos, planes de manejo, catastro y calendario productivo. La cosecha puede producir una firma similar al desmonte; por eso el sistema sólo prioriza inspección hasta contar con registro administrativo y validación territorial."),
        ("¿Qué superficie mínima de cambio puede detectar?", "La resolución de Sentinel-2 llega a 10 metros en algunas bandas, pero eso no implica detectar de forma fiable un único píxel. El umbral mínimo debe definirse con ensayos por tipo de cobertura, forma del polígono, nube y error aceptable. Para el piloto proponemos medir sensibilidad por rangos de superficie, no prometer una cifra teórica."),
        ("¿Con qué frecuencia compara las imágenes?", "La misión Sentinel-2 está diseñada para una revisita de cinco días en el ecuador con la constelación nominal, pero la disponibilidad útil depende de nubes y procesamiento. EcoNexo comparará cada nueva escena válida y mantendrá ventanas semanales o mensuales según el caso de uso."),
        ("¿Cómo evita confundir cambios estacionales con pérdida de vegetación?", "Usa una línea de base multitemporal, compara el mismo período de años anteriores y exige persistencia en más de una observación cuando el riesgo lo permite. También incorpora calendario productivo, lluvia y clase de cobertura. Los cambios atípicos se revisan antes de etiquetarlos como pérdida permanente."),
        ("¿Cómo analiza propiedades pequeñas y fragmentadas?", "Trabaja por polígonos y no sólo por promedios municipales. Se evita mezclar píxeles de bordes y se informa la proporción observable del lote. En parcelas muy pequeñas, la resolución puede ser insuficiente; allí se prioriza imagen de mayor resolución o verificación de campo."),
        ("¿Puede detectar caminos o aperturas nuevas dentro del bosque?", "Potencialmente sí cuando el ancho, contraste y persistencia superan la resolución útil. Un camino angosto puede quedar por debajo de la capacidad de Sentinel-2 o confundirse con sombra. El piloto debe medir desempeño por ancho y cobertura, y rotular estos hallazgos como indicios."),
        ("¿Qué período histórico utiliza como línea de base?", "Se definirá por zona y disponibilidad, idealmente con al menos uno o dos ciclos estacionales completos y escenas comparables. Para evaluar eventos conocidos se puede ampliar la serie desde 2015, cuando comienza Sentinel-2. La versión de la línea de base queda registrada."),
        ("¿Cómo verifica que la modificación no estaba autorizada?", "La plataforma necesita integrar o consultar el registro administrativo competente: permisos, planes, vigencia y geometría. Si esa fuente no está disponible, no puede afirmar ilegalidad. Genera un caso para revisión y solicita confirmación a la autoridad."),
        ("¿Una alerta constituye una prueba o solamente indica que debe inspeccionarse el lugar?", "Constituye un indicio documentado para priorizar inspección. Puede aportar cadena de datos, imágenes, tiempos y decisiones, pero no reemplaza el procedimiento administrativo, la constatación en campo ni el dictamen de la autoridad competente."),
        ("¿Quién confirma finalmente el cambio detectado?", "La institución con competencia legal sobre el territorio y el tipo de cobertura, apoyada por técnicos de campo y registros oficiales. EcoNexo registra esa decisión, pero no se atribuye la potestad de confirmar una infracción."),
        ("¿Cómo protege la información vinculada con propiedades privadas?", "Aplica acceso por organización y rol, mínima exposición de datos personales, cifrado en tránsito, registro de auditoría y retención definida. Para vistas públicas se agregan o anonimizan datos. Los convenios deben establecer finalidad, base legal, custodio y derechos de acceso."),
        ("¿Cómo mide la precisión de la detección?", "Compara alertas con un conjunto de referencia etiquetado por técnicos y evidencia de campo. Reporta precisión, exhaustividad, F1, falsos positivos y falsos negativos, además de desempeño por municipio, tipo de cobertura, superficie y condición de nube. Hoy no existe una cifra territorial validada que deba anunciarse como real."),
        ("¿Cómo registra un cambio que el sistema no identificó?", "Se incorpora como evento de referencia con polígono, fecha, fuente y validación. Luego se reproduce la ventana de datos para identificar si falló la observación, el procesamiento o el umbral. Esos casos cuentan como falsos negativos y forman parte del informe del piloto."),
        ("¿Puede diferenciar una perturbación temporal de una pérdida permanente?", "Puede estimarlo observando persistencia y recuperación en una serie temporal. La alerta inicial debe permanecer abierta hasta una observación posterior o validación de campo. La permanencia se informa con un horizonte y nivel de confianza, no como una verdad instantánea."),
    ]),
    ("Fuentes y calidad de los datos", [
        ("¿Qué información obtiene exactamente de Open-Meteo?", "La integración consulta variables meteorológicas por coordenada y tiempo: temperatura, humedad relativa, precipitación, viento y ráfagas; puede incorporar humedad o temperatura de suelo según el modelo. Cada observación guarda unidad, modelo, hora de generación, coordenada y hora de consulta."),
        ("¿Qué precisión tiene para los diferentes microclimas de Misiones?", "No hay una única precisión provincial. Open-Meteo combina modelos con grillas distintas y el error varía por relieve, estación y variable. El piloto debe comparar pronóstico y observación con estaciones disponibles, calcular sesgo y error por zona y ajustar umbrales; hasta entonces se usa como contexto, no como medición local certificada."),
        ("¿Qué fuentes satelitales abiertas utilizará?", "Para fuego activo, NASA FIRMS con VIIRS y, como complemento, MODIS. Para cobertura e índices, Copernicus Sentinel-2 L2A. Podrán incorporarse otras fuentes públicas si aportan cobertura, radar o validación, siempre documentando licencia, resolución y latencia."),
        ("¿Cuál es la resolución espacial de cada fuente?", "VIIRS publica detecciones de fuego activo con píxel aproximado de 375 m y MODIS de 1 km. Sentinel-2 tiene bandas de 10, 20 y 60 m. Esas cifras describen el producto, no la precisión final de una alerta ni el tamaño exacto del fenómeno."),
        ("¿Cuál es su frecuencia de actualización?", "FIRMS en tiempo casi real suele publicar observaciones dentro de unas horas; Sentinel-2 tiene revisita nominal de cinco días, condicionada por nubes y disponibilidad; Open-Meteo actualiza según el modelo. EcoNexo consulta cada fuente en ciclos configurables y muestra la antigüedad real del dato."),
        ("¿Qué latencia existe entre el evento y la disponibilidad del dato?", "Varía por fuente. FIRMS indica una latencia casi real que suele ser inferior a tres horas, mientras que una escena óptica depende de la pasada, el procesamiento y las nubes. La plataforma separa tres tiempos: observación, publicación por la fuente y procesamiento interno."),
        ("¿Qué capas y registros públicos se integrarán?", "Límites administrativos, áreas protegidas, cobertura o bosque nativo, hidrografía, caminos, centros poblados, infraestructura sensible y registros de permisos cuando exista acceso legal y técnico. El inventario final se acuerda con las instituciones y registra custodio, versión y fecha."),
        ("¿Cómo se cruzan datos con resoluciones diferentes?", "Todos se llevan a una referencia espacial común y se relacionan mediante puntos, celdas o polígonos, sin inventar detalle. Se conserva la geometría original, se documenta cualquier remuestreo y la confianza queda limitada por la fuente más débil relevante."),
        ("¿Cómo se identifican datos incompletos o desactualizados?", "Cada registro lleva hora de observación, recepción, fuente y estado de calidad. Reglas de frescura y campos obligatorios bloquean o degradan una evaluación. El usuario ve si una capa está vencida, parcial o no disponible."),
        ("¿Qué sucede cuando dos fuentes ofrecen resultados contradictorios?", "No se oculta la discrepancia. La alerta muestra ambas señales, reduce o recalcula la confianza y puede exigir revisión humana. Las reglas priorizan evidencia independiente y reciente, pero la decisión y su justificación quedan registradas."),
        ("¿Cómo se registra la procedencia de cada dato?", "Con metadatos de linaje: proveedor, producto, URL o identificador, hora de observación y recepción, parámetros de consulta, versión del procesamiento y transformaciones aplicadas. Así un tercero puede reconstruir por qué se generó una alerta."),
        ("¿Qué ocurre si Open-Meteo o una fuente satelital deja de funcionar?", "Se aplican reintentos controlados, monitoreo y estado degradado. La plataforma conserva el último dato con su antigüedad visible, desactiva reglas que requieren la fuente y evita presentar resultados incompletos como actuales. En producción se suman proveedor alternativo, colas y alertas operativas."),
        ("¿Las licencias permiten utilizar los datos dentro de un servicio comercial?", "Hay que separar datos y servicio de acceso. Open-Meteo publica datos bajo CC BY 4.0, pero su API gratuita alojada es para uso no comercial; un servicio comercial debe contratar endpoint de cliente o autoalojar conforme a sus términos. Copernicus admite usos públicos y comerciales; NASA exige respetar atribución y condiciones del producto."),
        ("¿Cómo se incorporan los reportes de técnicos y ciudadanos?", "Mediante formularios con tipo, descripción, ubicación, hora, evidencia opcional y consentimiento. Los reportes ingresan pendientes de moderación, se correlacionan con señales cercanas y adquieren mayor peso cuando el autor o un técnico los valida."),
        ("¿Cómo se evita que un reporte falso genere una alerta?", "Un reporte aislado no debería activar una alarma crítica. Se valida ubicación y formato, se limita abuso, se modera contenido y se busca corroboración temporal y espacial. La reputación del canal y la evidencia influyen en confianza, pero nunca sustituyen la revisión en casos sensibles."),
        ("¿Qué formatos utilizarán para interoperabilidad institucional?", "API JSON para integración operativa; GeoJSON para geometrías; CSV para análisis tabular; PDF para informes; y, cuando el organismo lo requiera, servicios OGC como WMS/WFS o paquetes geográficos. Cada intercambio debe incluir esquema, versión, zona horaria y diccionario de datos."),
    ]),
    ("Motor de reglas e inteligencia artificial", [
        ("¿EcoNexo utiliza actualmente inteligencia artificial o un motor de reglas?", "El núcleo operativo actual es un motor de reglas explicable, complementado por correlación y puntajes de confianza. Existe un componente experimental de anomalías, pero no corresponde presentarlo como IA territorial validada en producción. El piloto debe comparar cualquier modelo con una línea base de reglas."),
        ("¿Qué componente inteligente ya está funcionando?", "Funcionan reglas configurables que combinan telemetría, clima, focos, reportes y geocercas; también la priorización por confianza y el contexto ambiental. La inteligencia actual está en la correlación reproducible y explicable, no en una clasificación autónoma infalible."),
        ("¿Cómo se establece el comportamiento normal de una zona?", "Con una línea de base por estación, horario y tipo de territorio, utilizando series históricas válidas. Se calculan rangos esperables y cambios relevantes, y los técnicos revisan si reflejan la realidad local. La línea de base se versiona y no se mezcla entre zonas incompatibles."),
        ("¿Quién define los umbrales de alerta?", "El equipo técnico de EcoNexo propone valores iniciales; la institución competente y especialistas territoriales los validan. Los cambios requieren autor, motivo, fecha y prueba retrospectiva. Ningún umbral crítico debería modificarse sin control de versiones."),
        ("¿Los mismos umbrales sirven para toda la provincia?", "No necesariamente. Relieve, cobertura, estacionalidad, exposición y capacidad de respuesta cambian entre zonas. Se parte de una plantilla provincial y se calibran perfiles por región o geocerca, evitando sobreajuste cuando aún hay pocos datos."),
        ("¿Cómo se calcula el puntaje de confianza?", "Combina calidad y frescura de las fuentes, cantidad de evidencias independientes, concordancia espacial y temporal, cobertura disponible y antecedentes de la regla. La fórmula debe ser pública para los validadores y calibrarse con eventos etiquetados; no es una probabilidad legal de que exista una infracción."),
        ("¿Qué sucede cuando una alerta tiene poca confianza?", "Se envía a una cola de revisión, se solicita evidencia adicional o se mantiene en observación. No se difunde como confirmada ni activa acciones irreversibles. El umbral para escalar depende del impacto potencial y del costo de cada error."),
        ("¿El usuario puede saber por qué fue generada?", "Sí. La ficha muestra qué regla se activó, variables y umbrales, fuentes, horarios, coincidencias geográficas y cambios de confianza. La explicación debe ser legible y también conservar los datos técnicos para auditoría."),
        ("¿Un operador puede confirmarla, descartarla o escalarla?", "Sí, según su rol. Cada acción exige estado, comentario o motivo y puede adjuntar evidencia. Las transiciones permitidas se definen en el protocolo para evitar cierres o escaladas sin autoridad."),
        ("¿Queda registrada cada intervención humana?", "Sí. El registro de auditoría conserva actor, organización, fecha, acción, recurso afectado y metadatos relevantes. En producción se deben fijar retención, acceso a auditoría y mecanismos para proteger la integridad del historial."),
        ("¿Cómo se utilizan las correcciones para mejorar el sistema?", "Se convierten en etiquetas para evaluar reglas y modelos por versión. Primero se revisa la calidad de la corrección; después se ajustan umbrales o se reentrena en un entorno controlado. Todo cambio se prueba retrospectivamente antes de publicarse."),
        ("¿Qué métricas utilizarán para evaluar precisión?", "Precisión o valor predictivo positivo, exhaustividad o sensibilidad, F1, tasa de falsas alarmas y omisiones. También tiempo a alerta, tiempo a confirmación, cobertura territorial y desempeño por nivel. En cobertura vegetal se agregan métricas por superficie y solapamiento de polígonos."),
        ("¿Cómo medirán falsos positivos y falsos negativos?", "Se construye una tabla de contingencia comparando alertas con eventos confirmados en una ventana espacial y temporal definida. Los falsos negativos requieren un registro independiente de eventos, no sólo revisar lo detectado. Los criterios de coincidencia se fijan antes de evaluar."),
        ("¿Cómo evitarán que el sistema presente una predicción como una certeza?", "Mediante lenguaje de riesgo, confianza visible, estados como ‘por verificar’ y una separación clara entre señal, validación y decisión oficial. La interfaz no debe usar ‘confirmado’ sin una acción humana autorizada y evidencia asociada."),
        ("¿Qué evidencia tienen actualmente de que la metodología funciona?", "Existe evidencia de funcionamiento técnico del flujo: ingesta, reglas, alertas, revisión, auditoría e informes. Aún falta evidencia de desempeño territorial con verdad de campo en Misiones. Precisamente el piloto debe producir esa medición y permitir aceptar, corregir o descartar hipótesis."),
    ]),
    ("Procesamiento en cinco minutos", [
        ("Cuando hablan de cinco minutos, ¿desde qué momento se mide?", "Desde que EcoNexo recibe un conjunto de datos válido y suficiente para evaluar la regla hasta que crea o actualiza la alerta y la deja disponible para el canal configurado. Los sellos de tiempo de recepción y emisión permiten auditarlo."),
        ("¿Es tiempo de detección del fenómeno o tiempo de procesamiento?", "Es tiempo de procesamiento interno. La detección extremo a extremo incluye la demora del satélite, el proveedor, la red y la frecuencia de consulta, por lo que puede ser mucho mayor. Ambas métricas se informan por separado."),
        ("¿Cómo pueden garantizarlo si algunas fuentes tardan en actualizarse?", "No se garantiza la observación del evento en cinco minutos. Se compromete un objetivo de servicio desde la recepción del dato. Para reducir demoras externas se monitorean fuentes, se consultan en intervalos adecuados y se incorporan canales más rápidos como sensores o reportes."),
        ("¿Qué ocurre si los datos llegan incompletos?", "El evento queda pendiente o se evalúa con una regla degradada explícita. No comienza a contarse el objetivo como si el paquete fuera válido, y tampoco se oculta el retraso: se registra qué campo o fuente faltó y cuándo se completó."),
        ("¿Qué porcentaje de alertas esperan procesar dentro de ese tiempo?", "Como meta inicial proponemos al menos 95 % de los casos válidos en menos de cinco minutos, medido en ambiente piloto bajo carga acordada. El percentil 95 y 99, los rechazos y las excepciones deben publicarse; no se debe afirmar cumplimiento antes de medirlo."),
    ]),
    ("Arquitectura y Render", [
        ("¿Cómo es el flujo desde la recepción del dato hasta la alerta?", "Conector de fuente → validación y normalización → almacenamiento geográfico e histórico → correlación por tiempo y geocerca → motor de reglas y confianza → alerta → notificación y revisión humana → auditoría e informe. Cada etapa conserva estado y tiempos."),
        ("¿Dónde se almacenan los datos geográficos e históricos?", "En PostgreSQL con PostGIS para entidades, geometrías, alertas y trazabilidad. Los archivos grandes o imágenes deben ir a almacenamiento de objetos en producción, conservando en la base referencias, hashes y metadatos. El sistema no debe depender del disco efímero del servidor."),
        ("¿Qué componentes están desarrollados en Python?", "El backend principal utiliza FastAPI en Python, junto con lógica de integración, procesamiento ambiental y servicios satelitales. La interfaz web está desarrollada con Next.js/TypeScript. La separación permite escalar ingesta, API y procesamiento de forma independiente."),
        ("¿Cómo funciona el motor de reglas?", "Evalúa condiciones configuradas sobre datos normalizados, por ejemplo foco térmico más viento y proximidad a una geocerca. Si se cumplen, crea o eleva una alerta idempotente, registra la versión de la regla y explica qué condiciones activaron el resultado."),
        ("¿Cómo se generan los mapas y reportes?", "Los mapas consumen geometrías y capas desde la API y las representan por nivel, fuente y estado. Los informes consolidan indicadores, alertas, tiempos, evidencia y recomendaciones; pueden imprimirse o guardarse como PDF y compartirse mediante enlace revocable."),
        ("¿Qué parte del sistema está desplegada en Render?", "El repositorio incluye blueprints para la aplicación web, API y PostgreSQL, además de variables para fuentes externas. El estado real de cada integración depende de secretos y servicios activos en la cuenta. En una demostración se debe mostrar el panel de salud y distinguir conexión real de datos de ejemplo."),
        ("¿Render puede soportar un servicio provincial?", "Sí como plataforma, con instancias pagas, base administrada, monitoreo, copias, más de una instancia y pruebas de carga. El nivel gratuito es sólo para demostración: se suspende por inactividad, no escala, su base gratuita expira y no incluye copias. La producción requiere dimensionamiento y acuerdo de nivel de servicio."),
        ("¿Cómo escalará la plataforma si aumenta la cantidad de usuarios?", "Separando API, web y trabajos de ingesta; usando procesos en segundo plano y cola; índices geoespaciales, caché y paginación; y escalado horizontal de servicios sin estado. La capacidad se valida con pruebas de carga y observabilidad antes de ampliar cobertura."),
        ("¿Qué ocurre ante una caída del servicio?", "Los conectores reintentan sin duplicar eventos, la cola conserva trabajos y el monitoreo notifica al responsable. En producción se ejecutan varias instancias y un plan de recuperación. Al restablecerse, se procesa el atraso indicando que la alerta fue tardía."),
        ("¿Cómo se realizan las copias de seguridad?", "La base de producción debe usar copias automáticas y recuperación a un punto en el tiempo, más exportaciones verificadas fuera del servicio. Los archivos se almacenan con versionado. Se prueban restauraciones periódicas; una copia no validada no se considera estrategia de recuperación."),
        ("¿Qué controles de acceso tendrá cada institución?", "Organizaciones separadas, roles de administrador, operador y consulta, y permisos sobre geocercas, fuentes y acciones. La API valida el rol actual en cada operación. Para convenios interinstitucionales se pueden crear vistas compartidas sin exponer datos ajenos."),
        ("¿Cómo se protege la información sensible?", "TLS, contraseñas con hash fuerte, tokens con expiración, secretos fuera del frontend, mínimo privilegio, segregación por organización, auditoría y políticas de retención. En producción se agregan rotación de secretos, análisis de vulnerabilidades, copias cifradas y respuesta a incidentes."),
        ("¿Existe un registro de auditoría?", "Sí. Las operaciones sensibles generan eventos con actor, fecha, recurso y detalle. Para uso institucional debe definirse retención, exportación, revisión periódica y protección contra alteración, y sincronizar los relojes de todos los servicios."),
        ("¿EcoNexo cuenta con una API para integrarse con otros sistemas?", "Sí, el backend expone una API para autenticación, dispositivos, zonas, fuentes, alertas, reportes, administración e informes. Para integraciones externas se deben publicar contrato OpenAPI, versionado, límites, autenticación de servicio y entorno de pruebas."),
        ("¿Puede exportar alertas y reportes en PDF, CSV y formatos geográficos?", "Hoy los informes pueden imprimirse o guardarse como PDF y la plataforma maneja datos por API. La exportación institucional completa a CSV y GeoJSON debe verificarse endpoint por endpoint y cerrarse como entregable del piloto antes de prometer todos los formatos."),
        ("¿Cómo funcionará para usuarios rurales con conectividad limitada?", "Con interfaz liviana y adaptable, mensajes resumidos, caché local y carga diferida de evidencias. El canal puede complementarse con SMS, mensajería o sincronización posterior según disponibilidad. El piloto debe medir ancho de banda, latencia y facilidad de uso en campo."),
    ]),
    ("Validación del piloto", [
        ("¿En qué municipio o área de Misiones comenzará?", "Proponemos seleccionar con INTA un área acotada del norte de Misiones —por ejemplo San Antonio y General Manuel Belgrano— donde ya hay foco forestal y configuración territorial en la plataforma. La ubicación definitiva debe depender de referentes disponibles, casos históricos y permisos de datos."),
        ("¿Por qué eligieron ese territorio?", "Porque combina actividad forestal, interfaz rural-boscosa, necesidad de recorridas y actores con conocimiento local. También permite limitar el alcance para obtener evidencia útil en ocho semanas. La selección debe formalizarse con una matriz de riesgo, datos y capacidad de validación."),
        ("¿Qué desarrollarán durante las ocho semanas?", "Semana 1–2: alcance, datos, protocolo y línea base. 3–4: integración y calibración de reglas. 5–6: operación asistida y verificación. 7: análisis de errores y ajustes. 8: informe, demostración, transferencia y decisión de continuidad. No se promete una solución provincial completa en ese plazo."),
        ("¿Los dos casos de uso se validarán simultáneamente?", "Pueden avanzar en paralelo, pero con métricas y responsables separados. Si la capacidad territorial es limitada, se prioriza incendios como flujo operativo y cobertura vegetal como estudio controlado. El éxito de uno no debe ocultar fallas del otro."),
        ("¿Cuántas alertas necesitan analizar para evaluar el sistema?", "No conviene fijar un número arbitrario sin conocer prevalencia. Antes del piloto se calcula el tamaño muestral por caso de uso, error aceptable y frecuencia esperada; si hay pocos eventos reales, se complementa con retrospectiva histórica y casos negativos muestreados. El informe debe incluir intervalos de confianza."),
        ("¿Quién realizará la verificación territorial?", "Técnicos designados por INTA y organismos competentes, con participación municipal o de productores cuando corresponda. EcoNexo administra el flujo y evidencia, pero no se auto-valida. Los roles y tiempos deben quedar en un protocolo firmado."),
        ("¿Qué protocolo se utilizará?", "Una ficha previa con identificador, ubicación, hora, evidencia y nivel; revisión remota; visita o contacto territorial cuando aplique; resultado normalizado; anexos; y cierre por responsable autorizado. Debe definir seguridad de campo, privacidad, criterios de coincidencia y manejo de desacuerdos."),
        ("¿Habrá validadores técnicos independientes?", "Es recomendable. Al menos una muestra debería ser revisada por especialistas que no hayan configurado la regla, idealmente con etiquetas ocultas respecto de la predicción inicial. Esto reduce sesgo y hace más creíble el resultado."),
        ("¿Utilizarán eventos históricos para probar la plataforma?", "Sí. Permiten ejecutar retrospectivamente reglas y cobertura sin esperar nuevos eventos. Se separará ese resultado de la operación prospectiva, porque conocer de antemano el caso puede sesgar umbrales. Las fechas de corte y versiones quedan congeladas antes de evaluar."),
        ("¿Cuáles son las métricas de éxito?", "Desempeño: precisión, sensibilidad y falsas alarmas. Operación: al menos 95 % de datos válidos procesados en cinco minutos y reducción del tiempo a revisión. Adopción: uso por técnicos y calidad de registro. Gobernanza: trazabilidad completa. Como metas iniciales del producto se propone 85 % de precisión y 40 % de mejora en respuesta, sujetas a validación."),
        ("¿Qué precisión mínima consideran aceptable?", "Proponemos 85 % como objetivo inicial de precisión para alertas que llegan a operadores, acompañado por un piso de sensibilidad acordado. No debe aceptarse una cifra aislada: un sistema puede parecer preciso omitiendo eventos. Los umbrales se deciden según costo de error y nivel de alerta."),
        ("¿Qué mejora esperan obtener en el tiempo de respuesta?", "La hipótesis es reducir al menos 40 % el tiempo desde la disponibilidad de la señal hasta su revisión o derivación, comparado con el flujo actual documentado. Primero se medirá la línea base real; si no existe, se instrumentará durante las primeras semanas."),
        ("¿Cuál sería el número máximo tolerable de falsas alertas?", "Debe expresarse como tasa y carga operativa, no como número absoluto. Proponemos acordar un máximo por nivel y por operador, y medir cuántas requieren revisión innecesaria. Una alerta crítica falsa pesa más que una señal de observación; los límites serán distintos."),
        ("¿Qué criterio utilizarán para declarar que el piloto no funcionó?", "Si no alcanza métricas mínimas preacordadas, no produce evidencia trazable, genera una carga de falsas alarmas inaceptable o no puede operar con los datos disponibles. Un resultado negativo documentado también es útil: debe indicar si falla la fuente, el método, el proceso o la adopción."),
        ("¿Qué pueden mostrar funcionando en una demostración en vivo?", "Ingreso con roles, tablero y mapa, geocercas, estado de fuentes, consulta meteorológica, ejecución del pipeline, foco FIRMS si la clave está activa, imagen o índice Copernicus si hay credenciales, regla, alerta, confirmación o descarte, auditoría e informe. Antes de la reunión se debe ensayar también un modo de contingencia con datos claramente rotulados."),
    ]),
    ("Relación con el INTA", [
        ("¿Qué esperan concretamente del INTA Misiones?", "Co-diseño del protocolo, conocimiento territorial, acceso legítimo a datos y casos de referencia, técnicos para validar una muestra y evaluación independiente de utilidad. No buscamos sólo un aval institucional, sino una prueba crítica que permita mejorar o descartar supuestos."),
        ("¿Qué beneficio recibirían sus técnicos?", "Una bandeja común que reduce búsquedas manuales, reúne contexto antes de una recorrida y deja trazabilidad reutilizable para informes e investigación. También obtienen reglas y mapas adaptados a su territorio, sin perder la decisión técnica."),
        ("¿Cómo ayudaría EcoNexo a productores agropecuarios y forestales?", "Con avisos tempranos contextualizados, priorización de lotes expuestos, canal de reporte y seguimiento, y evidencia para planificar recorridas y prevención. La información debe ser comprensible y no sustituir recomendaciones profesionales ni canales de emergencia."),
        ("¿Cómo se integraría con el trabajo de extensión rural?", "El extensionista puede registrar observaciones desde campo, revisar alertas de su área y devolver validaciones. EcoNexo organiza la evidencia antes y después de la visita; INTA conserva la relación con el productor y el criterio técnico."),
        ("¿Qué conocimiento territorial necesitan del INTA?", "Calendarios productivos, tipos de cobertura y manejo, zonas críticas, prácticas de quema, accesibilidad, microclimas, redes de referentes y causas frecuentes de falsas señales. Ese conocimiento permite calibrar reglas que una fuente remota no puede aportar."),
        ("¿El INTA participaría como validador, usuario o socio técnico?", "La propuesta es que sea socio técnico y validador, y que algunos equipos actúen como usuarios piloto. Cada rol debe separarse: quien co-diseña no debería ser el único que evalúa. El convenio definirá alcance, tiempos y uso de resultados."),
        ("¿Cómo se evitaría duplicar herramientas institucionales existentes?", "Primero se releva el flujo y los sistemas actuales. EcoNexo se integra por API o exportación y cubre brechas de correlación, priorización y auditoría. Si una herramienta existente ya resuelve mejor una función, se la conserva como fuente o canal."),
        ("¿Los técnicos podrían agregar observaciones y corregir alertas?", "Sí. Pueden adjuntar evidencia, confirmar, descartar, reclasificar o escalar según permisos. Cada corrección conserva autor y motivo y alimenta la evaluación, no un aprendizaje automático opaco."),
        ("¿Quién sería propietario de los datos producidos conjuntamente?", "Debe resolverse por convenio antes del piloto. Como principio, cada institución conserva sus datos de origen; los datos derivados y conjuntos tienen reglas de copropiedad o licencia, acceso, retención y publicación. EcoNexo actúa como encargado o proveedor según el acuerdo, no presume propiedad."),
        ("¿Los resultados podrían utilizarse para investigaciones y publicaciones?", "Sí, con un plan de datos, aprobación institucional, anonimización cuando corresponda y reglas de autoría. Se deben publicar metodología, versión y limitaciones, y evitar exponer información sensible o evidencia administrativa en curso."),
        ("¿Cómo capacitarían a los técnicos?", "Con sesiones breves por rol, ejercicios sobre casos reales, manual operativo y una guía de interpretación de confianza y límites. Se incluye acompañamiento durante el piloto y evaluación práctica. La capacitación también recoge problemas de usabilidad para corregir la herramienta."),
        ("¿Por qué el INTA debería participar en vez de desarrollar una solución propia?", "Porque puede evaluar una base ya implementada y concentrar su esfuerzo en conocimiento territorial y validación, con menor tiempo inicial. La propuesta debe garantizar interoperabilidad, acceso a datos, documentación y una salida ordenada para evitar dependencia. Si el piloto no aporta valor frente a una solución propia, debe quedar demostrado."),
    ]),
    ("Instituciones y marco ambiental", [
        ("¿Cómo contribuye EcoNexo al cumplimiento de la Ley de Escudo Ambiental?", "Contribuye con monitoreo, priorización, evidencia y trazabilidad para políticas de protección, pero no reemplaza controles ni procedimientos legales. Antes de la presentación debe confirmarse el nombre y número exacto de la norma: no se identificó en el Digesto provincial una ley consolidada bajo la denominación literal ‘Ley de Escudo Ambiental’."),
        ("¿Qué instituciones deberían integrarse a la plataforma?", "Ministerio de Ecología, Defensa Civil, municipios, guardaparques, INTA y, según el caso, bomberos, fuerzas, organismos de producción y catastro. La integración debe ser gradual, con un responsable de datos y un protocolo por caso de uso."),
        ("¿Cómo se distribuyen las responsabilidades entre Ecología, Defensa Civil, guardaparques y municipios?", "EcoNexo no las redefine. El protocolo debe mapear quién monitorea, quién recibe, quién verifica, quién coordina emergencia y quién determina una infracción. Un caso puede pasar entre instituciones, pero cada transferencia conserva responsable y hora."),
        ("¿Puede EcoNexo generar evidencia para priorizar inspecciones?", "Sí: ubicación, tiempo, fuentes, imágenes, cambios, confianza y antecedentes permiten ordenar inspecciones. Esa evidencia es apoyo administrativo y técnico; su admisibilidad y peso los determina la autoridad conforme a su procedimiento."),
        ("¿Cómo se garantiza la neutralidad de las alertas?", "Con reglas publicadas y versionadas, mismas condiciones para casos equivalentes, procedencia visible, revisión de sesgos por territorio y posibilidad de auditoría. Los conflictos de interés se declaran y las decisiones humanas requieren motivo."),
        ("¿Qué institución confirma oficialmente una posible infracción?", "La autoridad competente según materia y jurisdicción, no EcoNexo. Para bosque, área protegida, quema o emergencia pueden intervenir organismos distintos. El convenio debe incluir una matriz legal de competencia revisada por asesoría jurídica."),
        ("¿Cómo se documenta todo el proceso desde la detección hasta la actuación?", "Cada caso recibe un identificador y conserva fuentes, regla, confianza, mapa, notificaciones, cambios de estado, responsables, evidencias y cierre. Los eventos forman una línea de tiempo exportable y el informe diferencia hechos observados, inferencias y decisiones oficiales."),
    ]),
    ("Modelo comercial", [
        ("Si los datos son gratuitos, ¿por qué alguien pagaría por EcoNexo?", "Se paga por transformar fuentes dispersas en un servicio operativo: integración, limpieza, correlación, geocercas, reglas, alertas, soporte, seguridad, auditoría, disponibilidad y adaptación institucional. El dato puede ser abierto; el costo evitado está en tiempo, coordinación y decisiones tardías."),
        ("¿Qué valor agrega la plataforma sobre esas fuentes?", "Una única lectura contextualizada, explicable y accionable. EcoNexo conserva el origen, combina señales, prioriza, asigna responsabilidades y mide el resultado. También reduce el trabajo de mantener conectores y formatos diferentes."),
        ("¿Quién sería el primer cliente?", "La mejor entrada es una institución o consorcio con territorio acotado, responsable operativo y capacidad de validación: un municipio, organismo provincial o programa con INTA. No se debe vender cobertura provincial antes de demostrar valor en el piloto."),
        ("¿Qué incluye el precio del piloto?", "Descubrimiento y protocolo, configuración territorial, integraciones acordadas, despliegue, capacitación, soporte de ocho semanas, medición, informe y transferencia. Deben separarse costos de datos o infraestructura de terceros, equipamiento, trabajo de campo y desarrollos fuera de alcance."),
        ("¿Cómo funcionaría el modelo SaaS?", "Suscripción por organización, territorio, usuarios o volumen de procesamiento, con niveles de soporte e integraciones. El contrato define disponibilidad, propiedad de datos, seguridad, límites de uso y salida. Puede existir un nivel gratuito de acceso o demostración sin comprometer el servicio institucional."),
        ("¿Cómo se justifican los USD 200.000 de financiamiento inicial?", "No como una cifra global sin desglose. Se propone asignar hitos: producto e integraciones, infraestructura y seguridad, validación territorial, equipo y soporte, asuntos legales y contingencia. Cada tramo se libera contra entregables y métricas; el presupuesto debe incluir meses de ejecución, perfiles, costos unitarios y caja posterior al piloto."),
        ("¿Qué parte del producto puede escalar a otras provincias?", "La arquitectura, conectores, autenticación, motor de reglas, auditoría, reportes y metodología de piloto. También la mayoría de fuentes nacionales o globales. La expansión reutiliza el núcleo, pero no debe copiar sin calibración el modelo territorial."),
        ("¿Qué componentes deben adaptarse a cada territorio?", "Capas oficiales, competencias, contactos, umbrales, calendarios, tipos de cobertura, idioma operativo, canales de aviso y protocolo de verificación. También la línea base y las métricas según prevalencia y capacidad local."),
        ("¿Quién mantiene el sistema después del piloto?", "EcoNexo puede operar software, infraestructura, conectores y soporte bajo contrato; la institución mantiene responsables, permisos, datos oficiales y validación. El acuerdo incluye actualizaciones, incidentes, niveles de servicio, seguridad y gobierno de cambios."),
        ("¿Qué ocurre si el cliente no continúa contratando el servicio?", "Se ejecuta un plan de salida: exportación documentada de datos y auditoría, revocación de accesos, período de transición y eliminación o conservación según contrato. Los formatos abiertos y la documentación reducen dependencia; la continuidad de fuentes o componentes propios se acuerda por licencia."),
    ]),
]


CRITICAL = [
    ("¿Qué parte de EcoNexo funciona hoy?", "Hoy podemos demostrar la plataforma web y backend, usuarios y roles, mapas y geocercas, datos meteorológicos, integraciones configurables con FIRMS y Copernicus, dispositivos, reglas, alertas, confianza, revisión humana, auditoría e informes. No presentamos todavía como validada la clasificación automática de desmontes ni una precisión territorial real. Esas son hipótesis del piloto."),
    ("¿Qué precisión real tiene?", "Todavía no existe una cifra de precisión validada en territorio que podamos defender. Sí podemos medir funcionamiento técnico. El piloto construirá una verdad de campo independiente y reportará precisión, sensibilidad, F1 y errores por zona y condición. La meta inicial de 85 % es un objetivo, no un resultado alcanzado."),
    ("¿Cómo diferencia una quema autorizada de un incendio?", "Una firma térmica no permite saberlo por sí sola. Se cruza con permiso o aviso de quema, polígono, horario, responsable, condiciones meteorológicas y confirmación local. Sin registro oficial integrado, EcoNexo informa ‘evento térmico por verificar’ y deriva; la autoridad decide su condición."),
    ("¿Cómo distingue una cosecha forestal de un desmonte?", "La imagen puede mostrar pérdidas similares. Se necesita clase de cobertura validada, serie temporal, patrón del lote, plan o permiso, calendario productivo y revisión de campo. EcoNexo prioriza el caso y documenta evidencia, pero no declara ilegalidad automáticamente."),
    ("¿Cómo valida las alertas territorialmente?", "Con un protocolo acordado: evidencia remota, responsable, contacto o visita, ficha normalizada, anexos y cierre. Técnicos de INTA y organismos competentes validarían una muestra, idealmente con revisión independiente. Las confirmaciones y descartes quedan auditados y alimentan las métricas."),
    ("¿Qué significa exactamente ‘cinco minutos’?", "Es el tiempo de procesamiento interno desde que recibimos datos válidos hasta que la alerta queda generada o actualizada. No es el tiempo desde que empieza el fenómeno: la observación depende de la pasada del satélite y la actualización de cada fuente. Informaremos ambas latencias por separado."),
    ("¿Por qué pagar si las fuentes son gratuitas?", "Porque el servicio integra, limpia y correlaciona esas fuentes, agrega contexto territorial, reglas, usuarios, alertas, auditoría, soporte y disponibilidad. Además, algunos accesos gratuitos tienen restricciones comerciales. El cliente paga por un flujo de decisión mantenido y medible, no por revender datos abiertos."),
    ("¿Cómo justifica los USD 200.000?", "Con un presupuesto por hitos y no con una cifra genérica: producto e integraciones, seguridad e infraestructura, validación de campo, equipo y soporte, legal y contingencia. Cada desembolso debe vincularse a entregables, métricas y meses de caja. La versión final necesita costos unitarios y cotizaciones."),
    ("¿Por qué el INTA debería participar?", "Porque puede evaluar una base funcional sin empezar de cero y aportar lo que EcoNexo no puede inventar: conocimiento territorial, protocolo y validación independiente. A cambio obtiene una herramienta adaptable, datos exportables y evidencia para su trabajo. La cooperación debe evitar dependencia y duplicación."),
    ("¿Qué pueden demostrar en vivo hoy?", "Ingreso, roles, tablero, mapa y geocercas; estado de fuentes; consulta Open-Meteo; ejecución del pipeline; FIRMS y Copernicus si las credenciales están activas; creación de una regla y alerta; confirmación o descarte; auditoría e informe. También llevaremos un caso de contingencia claramente marcado si una API externa falla."),
]


SOURCES = [
    ("Open-Meteo — documentación de la API", "https://open-meteo.com/en/docs"),
    ("Open-Meteo — licencias", "https://open-meteo.com/en/license"),
    ("Open-Meteo — términos y planes comerciales", "https://open-meteo.com/en/terms"),
    ("NASA FIRMS — descripción de focos VIIRS", "https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html"),
    ("NASA FIRMS — síntesis de productos y latencia", "https://firms.modaps.eosdis.nasa.gov/content/posters/FIRMS_USFS_One_Pager_2022PrintRev.pdf"),
    ("Copernicus Data Space — Sentinel-2", "https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2"),
    ("ESA — Sentinel-2, datos técnicos", "https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2/Facts_and_figures"),
    ("Render — límites de instancias gratuitas", "https://render.com/docs/free"),
    ("Render — escalado", "https://render.com/docs/scaling"),
    ("Render — recuperación y copias de PostgreSQL", "https://render.com/docs/postgresql-backups"),
    ("Digesto Jurídico de Misiones — Rama XVI", "https://digestomisiones.gob.ar/ramas.php"),
]


def shade(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=120, start=160, bottom=120, end=160):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("EcoNexo · INTA Misiones  |  ")
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor.from_string(MUTED)
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr)
    run._r.append(fld_char2)


def keep_with_next(paragraph, value=True):
    p_pr = paragraph._p.get_or_add_pPr()
    tag = p_pr.find(qn("w:keepNext"))
    if tag is None:
        tag = OxmlElement("w:keepNext")
        p_pr.append(tag)
    tag.set(qn("w:val"), "1" if value else "0")


def set_cell_text(cell, text, color=INK, bold=False, size=9.5):
    cell.text = ""
    p = cell.paragraphs[0]
    r = p.add_run(text)
    r.bold = bold
    r.font.name = "Calibri"
    r.font.size = Pt(size)
    r.font.color.rgb = RGBColor.from_string(color)
    p.paragraph_format.space_after = Pt(0)
    return p


def add_callout(doc, title, body, fill=PALE_GREEN, accent=EMERALD):
    table = doc.add_table(rows=1, cols=1)
    table.autofit = True
    cell = table.cell(0, 0)
    shade(cell, fill)
    set_cell_margins(cell, 150, 200, 150, 200)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(title)
    r.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor.from_string(accent)
    p2 = cell.add_paragraph()
    p2.paragraph_format.space_after = Pt(0)
    p2.paragraph_format.line_spacing = 1.15
    r2 = p2.add_run(body)
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = RGBColor.from_string(INK)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_qa(doc, number, question, answer):
    p = doc.add_paragraph()
    keep_with_next(p)
    p.paragraph_format.space_before = Pt(7)
    p.paragraph_format.space_after = Pt(2)
    r0 = p.add_run(f"{number:03d}  ")
    r0.bold = True
    r0.font.color.rgb = RGBColor.from_string(EMERALD)
    r1 = p.add_run(question)
    r1.bold = True
    r1.font.color.rgb = RGBColor.from_string(PETROL)
    a = doc.add_paragraph(answer)
    a.style = doc.styles["Body Text"]
    a.paragraph_format.keep_together = True


def configure_document(doc):
    section = doc.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)
    section.header_distance = Inches(0.32)
    section.footer_distance = Inches(0.32)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.15

    body = styles["Body Text"]
    body.font.name = "Calibri"
    body.font.size = Pt(10)
    body.font.color.rgb = RGBColor.from_string(INK)
    body.paragraph_format.space_after = Pt(4)
    body.paragraph_format.line_spacing = 1.14

    h1 = styles["Heading 1"]
    h1.font.name = "Calibri"
    h1.font.size = Pt(17)
    h1.font.bold = True
    h1.font.color.rgb = RGBColor.from_string(PETROL)
    h1.paragraph_format.space_before = Pt(9)
    h1.paragraph_format.space_after = Pt(7)
    h1.paragraph_format.keep_with_next = True

    h2 = styles["Heading 2"]
    h2.font.name = "Calibri"
    h2.font.size = Pt(13)
    h2.font.bold = True
    h2.font.color.rgb = RGBColor.from_string(EMERALD)
    h2.paragraph_format.space_before = Pt(8)
    h2.paragraph_format.space_after = Pt(5)
    h2.paragraph_format.keep_with_next = True

    header = section.header.paragraphs[0]
    header.text = "ECONEXO  /  GUÍA DE RESPUESTAS TÉCNICAS"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = header.runs[0]
    hr.bold = True
    hr.font.size = Pt(7.5)
    hr.font.color.rgb = RGBColor.from_string(EMERALD)
    add_page_number(section.footer.paragraphs[0])


def build():
    doc = Document()
    configure_document(doc)
    props = doc.core_properties
    props.title = "Respuestas al simulacro técnico EcoNexo ante INTA Misiones"
    props.subject = "Incendios, cobertura vegetal, arquitectura, validación y modelo comercial"
    props.author = "EcoNexo"
    props.keywords = "EcoNexo, INTA, Misiones, incendios, cobertura vegetal"

    # Cover
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(52)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run("ECO")
    r.bold = True; r.font.size = Pt(34); r.font.color.rgb = RGBColor.from_string(PETROL)
    r = p.add_run("NEXO")
    r.bold = True; r.font.size = Pt(34); r.font.color.rgb = RGBColor.from_string(EMERALD)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run("RESPUESTAS AL SIMULACRO TÉCNICO")
    r.bold = True; r.font.size = Pt(23); r.font.color.rgb = RGBColor.from_string(PETROL)

    p = doc.add_paragraph("Preparación para la presentación ante INTA Misiones")
    p.paragraph_format.space_after = Pt(20)
    p.runs[0].font.size = Pt(14)
    p.runs[0].font.color.rgb = RGBColor.from_string(EMERALD)

    table = doc.add_table(rows=3, cols=2)
    table.columns[0].width = Inches(1.35)
    table.columns[1].width = Inches(5.3)
    labels = [("ALCANCE", "140 preguntas + 10 respuestas críticas"), ("ENFOQUE", "Respuesta oral, técnica, honesta y verificable"), ("FECHA", "Agosto de 2026 · Misiones, Argentina")]
    for i, (label, value) in enumerate(labels):
        c0, c1 = table.rows[i].cells
        shade(c0, PETROL); shade(c1, PALE_GREEN)
        set_cell_margins(c0); set_cell_margins(c1)
        set_cell_text(c0, label, WHITE, True, 8.5)
        set_cell_text(c1, value, INK, i == 0, 9.5)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(34)
    r = p.add_run("DETECTAR ANTES. DECIDIR MEJOR. ACTUAR A TIEMPO.")
    r.bold = True; r.font.size = Pt(10); r.font.color.rgb = RGBColor.from_string(GOLD)

    doc.add_page_break()

    doc.add_heading("Cómo usar esta guía", level=1)
    add_callout(doc, "REGLA DE ORO", "Cada respuesta debe durar menos de un minuto: empezar por el alcance real, explicar el método, reconocer el límite y cerrar con la forma de validarlo.", PALE_GOLD, PETROL)
    for text in [
        "HOY significa que la función existe en el producto y puede demostrarse con las credenciales y servicios correspondientes.",
        "PILOTO significa que existe una hipótesis o componente que debe calibrarse y medirse con evidencia territorial independiente.",
        "META significa un objetivo de desempeño; no debe presentarse como resultado alcanzado hasta publicar la medición.",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(text)

    add_callout(doc, "LÍMITE LEGAL", "EcoNexo es una herramienta de monitoreo y apoyo a la decisión. Una alerta no prueba por sí sola una infracción. La autoridad competente confirma los hechos y aplica el procedimiento correspondiente.", PALE_GREEN, EMERALD)
    add_callout(doc, "REFERENCIA NORMATIVA A CONFIRMAR", "No se identificó en el Digesto Jurídico de Misiones una norma consolidada bajo el nombre literal ‘Ley de Escudo Ambiental’. Antes de exponer, confirmar con Ecología o asesoría jurídica el nombre oficial, número y artículos aplicables.", PALE_GOLD, PETROL)

    doc.add_page_break()
    doc.add_heading("Las 10 respuestas críticas", level=1)
    p = doc.add_paragraph("Estas versiones están redactadas para responder de forma directa ante una evaluación técnica.")
    p.runs[0].italic = True
    for i, (q, a) in enumerate(CRITICAL, 1):
        add_qa(doc, i, q, a)

    number = 1
    for section_index, (title, items) in enumerate(SECTIONS, 1):
        doc.add_page_break()
        doc.add_heading(f"{section_index:02d}  {title}", level=1)
        for q, a in items:
            add_qa(doc, number, q, a)
            number += 1

    assert number == 141, f"Expected 140 questions, got {number - 1}"

    doc.add_page_break()
    doc.add_heading("Guion de demostración en vivo", level=1)
    demo_steps = [
        ("1", "Ingresar", "Mostrar autenticación, organización y rol."),
        ("2", "Revisar fuentes", "Confirmar qué servicios están conectados y cuáles están en modo contingencia."),
        ("3", "Ubicar el territorio", "Abrir mapa, geocerca y activos expuestos."),
        ("4", "Recibir o ejecutar datos", "Consultar Open-Meteo y ejecutar el pipeline; usar FIRMS/Copernicus sólo si están configurados."),
        ("5", "Activar una regla", "Mostrar condición, umbral, evidencia y explicación."),
        ("6", "Gestionar la alerta", "Confirmar, descartar o escalar con comentario."),
        ("7", "Auditar", "Mostrar actor, hora y cambios de estado."),
        ("8", "Informar", "Generar un informe y explicar sus límites."),
    ]
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for cell, text in zip(hdr.cells, ("PASO", "ACCIÓN", "EVIDENCIA")):
        shade(cell, PETROL); set_cell_margins(cell); set_cell_text(cell, text, WHITE, True, 8.5)
    for step, action, evidence in demo_steps:
        cells = table.add_row().cells
        cells[0].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        shade(cells[0], PALE_GREEN)
        set_cell_text(cells[0], step, EMERALD, True, 10)
        set_cell_text(cells[1], action, PETROL, True, 9.5)
        set_cell_text(cells[2], evidence, INK, False, 9.2)
        for cell in cells: set_cell_margins(cell)
    add_callout(doc, "CONTINGENCIA", "Preparar un caso reproducible con datos claramente rotulados como históricos o de demostración. Si una API externa falla, mostrar el estado degradado y explicar cómo el sistema evita publicar datos ficticios como reales.", PALE_GOLD, PETROL)

    doc.add_page_break()
    doc.add_heading("Fuentes técnicas verificadas", level=1)
    p = doc.add_paragraph("Consulta realizada en agosto de 2026. Las condiciones de servicio y licencias deben revisarse antes de contratar o publicar.")
    p.runs[0].italic = True
    for title, url in SOURCES:
        p = doc.add_paragraph(style="List Bullet")
        r = p.add_run(f"{title}: ")
        r.bold = True
        p.add_run(url)

    doc.add_heading("Nota de uso", level=2)
    doc.add_paragraph("Este documento prepara respuestas técnicas y comerciales. No constituye dictamen legal, pericia ambiental ni certificación de desempeño. Toda cifra de precisión, tiempo o impacto debe acompañarse con protocolo, muestra, período, versión del sistema y responsable de validación.")

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
