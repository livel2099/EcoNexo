-- El alta anterior descartaba telemetry_mode y telemetry_config del formulario.
-- Recuperar únicamente nodos sin lecturas marcados explícitamente como virtuales
-- por los dos flujos afectados. Nunca inventar lecturas ni ponerlos online.
BEGIN;

UPDATE devices d
SET telemetry_mode='open_meteo',
    telemetry_config='{"provider":"open-meteo","mode":"modelled_context","repair":"23"}'::jsonb,
    last_pipeline_status='pending',
    updated_at=now()
WHERE d.telemetry_mode='mqtt'
  AND d.telemetry_config='{}'::jsonb
  AND d.last_seen IS NULL
  AND (d.tags @> ARRAY['virtual','open-meteo','pipeline']::text[]
       OR d.tags @> ARRAY['virtual','telemetria']::text[])
  AND NOT EXISTS (SELECT 1 FROM readings r WHERE r.device_id=d.id);

COMMIT;
