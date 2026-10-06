# Econexo: revisión de producto y plan de ejecución

Fecha: 6 de octubre de 2026. Alcance: revisión estática del repositorio y validación local de los cambios; no auditoría de datos ni infraestructura de producción.

Actualización posterior: se implementó el primer ciclo predictivo para incendios, con ledger, evidencia independiente, aprendizaje supervisado, validación temporal, calibración, deriva y reversión en modo sombra. Ver `CICLO_PREDICTIVO.md` para alcance, activación y limitaciones. El backlog de esta revisión describe el diagnóstico original; varios de sus componentes ya tienen implementación. La validación del desempeño real sigue pendiente de datos del territorio.

## Decisión de producto

Econexo tiene una base de monitoreo, detección y apoyo preventivo. Todavía no hay evidencia en el código revisado para declarar validada una predicción propia de incidentes futuros. Priorizar un piloto de riesgo de incendio a 24 horas en un territorio de Misiones, con responsables operativos y resultados verificables, antes de extender modelos a todas las verticales.

## Evidencia y brechas

| Evidencia en el repositorio | Implicación | Trabajo requerido |
|---|---|---|
| `services/anomaly/app/model.py`: autoencoder de valor y hora; error normalizado con sigmoide | Detecta rareza actual. El score no es una probabilidad calibrada de incendio futuro | Modelo con objetivo futuro; separar detección y pronóstico |
| `services/anomaly/app/main.py`: entrenamiento global de 30 días al arrancar | Mezcla dispositivos y organizaciones; no hay evaluación temporal, artefacto persistido o registro de versiones | Modelos por contexto, datasets trazables, evaluación temporal y territorial, registro y reversión |
| `apps/web/app/lib/spaceai.ts`: reglas e índices con coeficientes de confianza fijos | Heurísticas útiles, pero su confianza no acredita exactitud estadística | Etiquetar como índices; validar y calibrar antes de presentar porcentajes de probabilidad |
| `apps/api/app/routers/agro.py` y `agro.py`: pronósticos y balance agronómico | Existe anticipación con modelos externos | Medir desempeño local y conservar el pronóstico tal como fue emitido |
| `apps/api/app/routers/kpis.py`: confirmadas / confirmadas + descartadas | Mide alertas revisadas; no detecta incidentes que el sistema omitió ni mide adelanto | Ground truth independiente, recall, falsas alarmas por territorio y anticipación |
| `readings`: valor, variable, dispositivo y timestamp; dispositivos virtuales en pipeline | La procedencia y calidad no quedan completas por observación | Distinguir sensor, modelo externo, manual y simulación; conservar tiempo de adquisición e ingesta y flags de calidad |
| `/plataforma` y `/platform/*`: administración general ya existente | Hay permisos en API, cuentas, licencias y auditoría | Ampliar operación y madurez predictiva; mantener acceso sin enlace público |

## Cambios entregados en esta revisión

- Ingreso exclusivo `/plataforma/ingreso`, sin registro ni cuentas demo. Reutiliza autenticación, límites de intentos y cambio de contraseña existentes. No guarda una sesión de un usuario sin privilegios de plataforma.
- La consola conserva la autorización en API: cuenta activa, organización habilitada, rol admin y correo en `PLATFORM_ADMIN_EMAILS`. Ocultar una ruta no concede seguridad.
- Pestaña Operación y predicción con diagnóstico global protegido: frescura de nodos, alertas, pipeline e indicadores de configuración sin secretos.
- Lecturas posteriores al reloj de la base no se presentan como última observación válida; nodos con reloj adelantado se marcan para revisar.
- El diagnóstico declara predicción pendiente de validación y conserva la fecha del diagnóstico anterior si falla una actualización.
- El pipeline ya no acepta scores de un modelo sin entrenamiento, sin indicador de entrenamiento, no finitos o fuera de 0–1: utiliza el fallback neutro existente. Esto evita ponderar una red sin entrenar como evidencia de IA; el fallback no equivale a una probabilidad calibrada.

## Backlog por prioridad

Estimaciones orientativas para un equipo con backend, datos y frontend; no son compromisos de entrega. Validar disponibilidad de datos y responsables al iniciar.

| Prioridad / plazo | Resultado | Responsable | Criterio de aceptación |
|---|---|---|---|
| P0 / semana 1 | Contrato del piloto: incidente, área, ventana de 24 h, decisión y costo de errores | PO + referente de territorio | Definición aprobada y protocolo independiente para registrar eventos y no eventos |
| P0 / semanas 1–2 | Procedencia y calidad por observación | Backend + datos | Fuente, adquirido en, recibido en, unidad, flags, cobertura y faltantes; simulación excluida de evaluación productiva |
| P0 / semanas 1–2 | Ledger de predicciones | Backend + datos | Cada registro guarda `issued_at`, `valid_from/to`, territorio, versión, features disponibles al emitir, riesgo/probabilidad y acción; nunca se sobrescribe al actualizar el pronóstico |
| P0 / semanas 2–3 | Resultados verificados | PO + operaciones | Eventos independientes de alertas; emparejamiento espacio-temporal documentado; revisión de eventos omitidos; distinguir no evento de resultado aún desconocido |
| P0 / semanas 3–4 | Línea base y evaluación sin fuga | Datos | Comparar reglas actuales, persistencia y candidato; cortes por fecha con separación acorde al horizonte y por territorio; ausencia de datos futuros entre features |
| P1 / semanas 4–6 | Modelo supervisado y calibración | Datos | Precision, recall, PR-AUC, Brier y curvas de calibración por horizonte; volumen, período e incertidumbre publicados; el candidato supera la línea base con costos operativos aceptables |
| P1 / semanas 4–6 | Alertas anticipadas operables | Frontend + operaciones | Tarjeta con qué puede ocurrir, dónde, cuándo, fuentes, incertidumbre, responsable y acción; estado sin datos; deduplicación y escalamiento |
| P1 / semanas 5–6 | Validación en modo sombra | PM + operaciones | Predicciones guardadas sin activar respuesta automáticamente; evaluación prospectiva y aprobación humana antes de activar |
| P1 / semanas 5–8 | Gestión de modelos | Backend + datos | Versionado de modelo/dataset, artefacto persistido, historial de entrenamiento, deriva, umbrales y reversión auditada |
| P1 / semanas 1–4 | Operación confiable | Backend + infraestructura | Monitoreo de fuentes reales, latencias y errores; notificaciones con entrega y reintentos; restauración de backup probada |
| P1 / semanas 2–4 | Administración reforzada | Backend + frontend | MFA para administradores, sesiones revocables, paginación completa, auditoría exportable y selección explícita de organización para soporte sin suplantación silenciosa |
| P2 / después del piloto | Extensión a agua, plagas y otras verticales | PO + datos | Evidencia local y objetivos específicos por módulo; no extrapolar métricas de incendio |

## Puertas de salida del piloto

No lanzar una promesa de precisión antes de fijar las métricas con operaciones. El 85% de alertas confirmadas no basta: se puede lograr alertando muy poco y omitiendo incidentes. Medir por horizonte y territorio: recall, falsas alarmas por semana, tiempo de anticipación respecto del inicio real, cobertura de datos y calibración. Reportar volumen y eventos revisados; ninguna muestra mínima arbitraria garantiza validez.

En la reunión semanal, PM revisa frescura, disponibilidad y bloqueos; PO revisa si la alerta cambia una decisión; datos compara desempeño con la línea base; operaciones valida incidentes y acciones. Cada incremento debe demostrar una mejora medible del piloto.

## Mejoras de experiencia y comercialización

1. Una tarjeta principal que responda qué puede pasar, en qué ventana y qué acción tomar; separar observado de pronosticado.
2. Mostrar datos faltantes y antigüedad por fuente; ausencia de datos no significa riesgo bajo.
3. Mostrar explicación de factores como ayuda a la decisión; evitar inferir causalidad del modelo.
4. Onboarding con territorio, fuentes, responsables y canales verificados. Una organización sin fuentes suficientes no debe parecer plenamente operativa.
5. Alinear planes y módulos con capacidad operativa comprobada. Revisar README y material comercial: algunas descripciones de Copernicus están atrasadas respecto del cliente actual.

## Acceso y puesta en marcha

Usar `/plataforma/ingreso`. Configurar la lista de correos autorizados y crear cuentas con el bootstrap ya documentado en `ADMIN_GENERAL_OCULTO.md`. No hay contraseña nueva hardcodeada ni configuración de producción modificada. Para varios administradores, el bootstrap existente solo crea el primer correo ordenado: las demás cuentas deben aprovisionarse de forma controlada.

El panel consulta tablas existentes, incluida `pipeline_runs` (migración 14); no requiere nuevas migraciones. El umbral de 30 minutos es un diagnóstico general; adaptar luego por frecuencia esperada y tipo de nodo. Integración configurada no equivale a conexión verificada. El diagnóstico de madurez es la conclusión de esta revisión, no un evaluador automático de modelos.

## Referencias de metodología

- [Validación temporal: TimeSeriesSplit, scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).
- [Calibración de probabilidades, scikit-learn](https://scikit-learn.org/stable/modules/calibration.html).

Estas referencias sustentan el método propuesto; los hallazgos sobre Econexo provienen del repositorio.

## Validación de la entrega

- 106 pruebas de API, autorización, contrato de anomalías, correlación, pipeline y compilación aprobadas.
- TypeScript y build de Next.js aprobados; la ruta privada se genera correctamente.
- Ocho escenarios de navegador comprobados con Chrome instalado: diagnóstico móvil, rechazo de administrador institucional, cambio obligatorio de clave, portada, edición de contactos, baja de licencias, restablecimiento de clave y acceso a Admin Core. Siete pasaron en la corrida general y el octavo pasó al corregir un selector ambiguo de la prueba.
- Las pruebas de API usan dobles de base de datos y las de navegador interceptan respuestas: no verifican conectividad ni datos de producción. No se desplegó ni se alteraron credenciales o configuración de producción.
