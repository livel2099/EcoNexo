# Módulo Focos de incendio forestal y humo

## Producto independiente

El módulo se comercializa y habilita como licencia separada de la plataforma principal. Cada organización tiene un `organization_modules` con estado `trial`, `active`, `suspended` o `expired`.

## Público destinatario

- municipios;
- brigadas y equipos operativos;
- organizaciones ambientales;
- empresas forestales;
- laboratorios y unidades técnicas;
- medios de comunicación;
- observatorios territoriales.

## Principio de comunicación

La interfaz usa dos capas:

1. **Lectura para todo público:** qué se ve, qué significa y qué hacer.
2. **Respaldo técnico:** señal térmica, distancia, confianza, FRP, viento, humedad, PM2.5, AQI, fuentes y hora.

Una señal térmica satelital no se muestra como incendio confirmado. La confirmación puede surgir de cámaras, sensores de humo, brigadas, reportes o una comunicación oficial.

## Fuentes

- detecciones satelitales persistidas por EcoNexo, incluyendo NASA FIRMS cuando hay clave;
- meteorología y humedad de Open-Meteo;
- calidad del aire de CAMS/Open-Meteo;
- nodos IoT;
- reportes georreferenciados;
- alertas y geocercas de la organización.

## Comunicación

Los mensajes para WhatsApp y Telegram son borradores. Antes de abrir el canal se registra:

- usuario;
- organización;
- módulo;
- canal;
- audiencia;
- texto;
- snapshot o alerta asociados;
- fecha.

No existe autopublicación por defecto.

## Marco operativo de Misiones

El diseño acompaña una lógica de detección temprana, vigilancia reforzada, monitoreo diferencial y respuesta rápida. La plataforma no se presenta como sistema oficial de la Provincia ni sustituye a las autoridades, Bomberos, Policía o 911.


La referencia legal-operativa y sus límites se documentan en [MISIONES_FIRE_POLICY.md](MISIONES_FIRE_POLICY.md). No se asigna un número de ley provincial específico sin una fuente oficial verificable.
