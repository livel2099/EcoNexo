"""Diagnóstico operativo global. Configurado no implica disponible ni validado."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from . import db
from .config import get_settings


class OperationsMetrics(BaseModel):
    devices_total: int
    devices_stale: int
    latest_reading_at: datetime | None
    alerts_pending: int
    alerts_confirmed: int
    alerts_discarded: int
    pipeline_degraded_24h: int
    latest_pipeline_at: datetime | None


class IntegrationStatus(BaseModel):
    name: str
    configured: bool
    detail: str
    state: str = 'unverified'
    verified: bool = False
    required_for: str = ''
    setup_steps: list[str] = []


class PlatformOperationsOut(BaseModel):
    generated_at: datetime
    stale_after_minutes: int
    metrics: OperationsMetrics
    integrations: list[IntegrationStatus]
    predictive_status: str = "not_validated"
    predictive_gaps: list[str]


async def operations_snapshot() -> PlatformOperationsOut:
    # Una consulta y un reloj de base común. No se exponen URLs, claves ni errores crudos.
    row = await db.pool().fetchrow("""
        SELECT now() AS generated_at,
          (SELECT count(*) FROM devices) AS devices_total,
          (SELECT count(*) FROM devices
             WHERE last_seen IS NULL OR last_seen < now() - interval '30 minutes'
                OR last_seen > now() + interval '5 minutes') AS devices_stale,
          (SELECT max(ts) FROM readings WHERE ts <= now()) AS latest_reading_at,
          (SELECT count(*) FROM alerts
             WHERE status IN ('nueva','escalada','asignada')) AS alerts_pending,
          (SELECT count(*) FROM alerts WHERE status='confirmada') AS alerts_confirmed,
          (SELECT count(*) FROM alerts WHERE status='descartada') AS alerts_discarded,
          (SELECT count(*) FROM pipeline_runs
             WHERE started_at >= now() - interval '24 hours'
               AND (status IN ('failed','partial') OR
                    (status='running' AND started_at < now() - interval '30 minutes')))
            AS pipeline_degraded_24h,
          (SELECT max(finished_at) FROM pipeline_runs
             WHERE status IN ('completed','partial')) AS latest_pipeline_at
    """)
    settings = get_settings()
    configured = [
        ("Ingesta programada", settings.pipeline_scheduler_enabled, "Habilitación del scheduler; verificar ejecuciones recientes."),
        ("MQTT", settings.mqtt_enabled, "Habilitación del bus; verificar frescura de nodos."),
        ("Detección de anomalías", settings.anomaly_enabled, "Habilitación del servicio; no demuestra entrenamiento ni precisión."),
        ("NASA FIRMS", settings.firms_inline_enabled and bool(settings.nasa_firms_key.strip()), "Ingesta habilitada y credencial presente; no prueba conectividad."),
        ("Copernicus Process API", settings.copernicus_mode == "process_api" and bool(settings.copernicus_client_id.strip() and settings.copernicus_client_secret.strip()), "Modo y credenciales presentes; cada organización controla su activación."),
        ("Archivos S3", settings.s3_enabled, "Almacenamiento habilitado; no prueba disponibilidad."),
    ]
    guidance = {
        'Ingesta programada': ('Actualización automática de nodos y fuentes', ['Configurar PIPELINE_SCHEDULER_ENABLED y verificar una ejecución reciente con lecturas.']),
        'MQTT': ('Sensores físicos conectados al broker; no es necesario para consultar clima o satélite', ['Disponer de un broker accesible desde los servicios.', 'Revisar MQTT_ENABLED, MQTT_HOST y MQTT_PORT; configurar autenticación y TLS según el broker.', 'Publicar una lectura real y verificar recepción, organización y hora del nodo.']),
        'Detección de anomalías': ('Análisis adicional de telemetría; no es necesario para el pronóstico meteorológico', ['Desplegar el servicio de anomalías y configurar ANOMALY_SERVICE_URL.', 'Habilitar ANOMALY_ENABLED después de verificar conectividad.', 'Verificar entrenamiento y contrastar resultados antes de atribuir precisión al modelo.']),
        'NASA FIRMS': ('Consulta de focos de calor', ['Revisar FIRMS_INLINE_ENABLED y NASA_FIRMS_KEY.', 'Consultar una detección real y comprobar fecha y cobertura.']),
        'Copernicus Process API': ('Imágenes Sentinel-2 y estadísticas de vegetación', ['Revisar COPERNICUS_MODE, COPERNICUS_CLIENT_ID y COPERNICUS_CLIENT_SECRET.', 'Habilitar la fuente de la organización y consultar un polígono real.', 'Comprobar cuota y fecha de las observaciones.']),
        'Archivos S3': ('Fotografías y evidencias adjuntas; no es necesario para generar informes HTML', ['Disponer de bucket privado S3 o compatible R2 con permisos mínimos.', 'Configurar S3_ENDPOINT, S3_BUCKET, S3_REGION, S3_ACCESS_KEY y S3_SECRET_KEY.', 'Revisar S3_PUBLIC_ENDPOINT y S3_SERVER_SIDE_ENCRYPTION para producción.', 'Habilitar S3_ENABLED y comprobar carga y lectura autorizada de un archivo.']),
    }
    integrations = []
    for name, enabled, detail in configured:
        purpose, steps = guidance[name]
        integrations.append(IntegrationStatus(name=name,configured=bool(enabled),detail=detail,
            state='configured_unverified' if enabled else 'disabled_or_missing',required_for=purpose,setup_steps=steps))
    return PlatformOperationsOut(
        generated_at=row["generated_at"], stale_after_minutes=30,
        metrics=OperationsMetrics(**{key: row[key] for key in OperationsMetrics.model_fields}),
        integrations=integrations,
        predictive_gaps=[
            "Habilitar cada riesgo por organización y reunir pronósticos reales a 6/24/72 horas: incendio, anegamiento pluvial, calor y PM2.5.",
            "Verificar incidentes y períodos sin incidente, incluidos eventos no alertados.",
            "Entrenar candidatos con el ledger y revisar la evaluación temporal frente a las líneas base.",
            "Validar prospectivamente y en territorios separados antes de extrapolar resultados.",
            "Revisar anticipación, recall, falsas alarmas, calibración y deriva; reentrenar o revertir cuando corresponda.",
        ],
    )
