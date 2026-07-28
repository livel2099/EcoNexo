# EcoNexo Misiones 1.0.0-rc.3

Candidato de lanzamiento tecnico orientado exclusivamente a la provincia de Misiones.

## Correcciones principales

- Retiro de referencias operativas, coordenadas y datos demo externos a Misiones.
- Catalogo de 17 departamentos y 79 municipios.
- Limite provincial oficial sincronizable desde GeoRef Argentina.
- Filtros territoriales en frontend, API, PostgreSQL/PostGIS, FIRMS, informes y app movil.
- Seeds de Posadas, San Pedro/Yaboti y Obera con municipio/departamento explicitos.
- Mapa base estable y WMS opcional sin credenciales de terceros.
- Focos termicos comunicados como senales a verificar, no como incendios confirmados.
- Produccion sin fixtures satelitales ante fallas o falta de MAP_KEY.
- Informes tecnicos extensos con SpaceAI, formulas, QA, laboratorio, revision y firmas.
- Guardia de configuracion productiva y scripts de deploy/pre-flight.

## Validacion incluida

- 29 pruebas API.
- Compilacion Python aprobada.
- 44 archivos TypeScript/TSX sin errores de sintaxis.
- JSON, YAML y CSS aprobados.

## Condicion de lanzamiento

Completar `docs/OFFICIAL_LAUNCH_MISIONES.md`, sincronizar GeoRef, dejar la auditoria externa en cero, configurar infraestructura/credenciales reales y obtener aprobacion legal, operativa y cientifica.

## rc.2 - Sentinel-2 y sanidad forestal del norte

- Soluciona la capa Copernicus deshabilitada mediante configuración WMS por organización.
- Incorpora verificación GetCapabilities y selección de nombres de capas.
- Corrige el polígono territorial de respaldo para incluir San Antonio y todos los centros operativos del norte provincial.
- Añade la sección licenciable `Plagas forestales` enfocada en San Antonio.
- Representa el radar meteorológico de Bernardo de Irigoyen como contexto regional, no como diagnóstico de plagas.
- Integra rutas de escalamiento hacia SENASA/SINAVIMO, FCF UNaM e INTA Montecarlo.

## rc.3 - Accesos y licencias comerciales

- Los ingresos correctos por email o Google generan mensajes para el panel administrador.
- Bandeja de mensajes con lectura individual, contador e IP anonimizada.
- Suscripciones limitadas según el pricing del plan de negocios.
- Sandbox calificado, diagnóstico, piloto 8 semanas, municipal, provincia/pro, enterprise y academia.
- Solicitud de licencia desde la organización y aprobación desde una consola comercial global.
- Límites de usuarios, dispositivos, geocercas, reglas e informes mensuales.
- Migración 11 y documentación operativa.
