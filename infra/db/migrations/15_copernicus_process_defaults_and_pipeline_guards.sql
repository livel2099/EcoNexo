-- EcoNexo 1.0.0-rc.6.2
-- Copernicus Process API como proveedor predeterminado y guardas de concurrencia.
-- Idempotente; no modifica migraciones ya aplicadas.

BEGIN;

ALTER TABLE environmental_source_settings
  ADD COLUMN IF NOT EXISTS copernicus_use_system_default BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS copernicus_last_test_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS copernicus_last_test_ok BOOLEAN,
  ADD COLUMN IF NOT EXISTS copernicus_last_error TEXT,
  ADD COLUMN IF NOT EXISTS copernicus_available_layers JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE environmental_source_settings
  ALTER COLUMN copernicus_enabled SET DEFAULT true;

ALTER TABLE environmental_source_settings
  DROP CONSTRAINT IF EXISTS environment_sources_copernicus_config_check;

ALTER TABLE environmental_source_settings
  ADD CONSTRAINT environment_sources_copernicus_config_check
  CHECK (
    NOT copernicus_enabled
    OR copernicus_use_system_default
    OR NULLIF(btrim(copernicus_wms_url), '') IS NOT NULL
  ) NOT VALID;

-- La actualización habilita el proveedor predeterminado de sistema en registros
-- existentes sin borrar una instancia WMS explícita ya configurada.
UPDATE environmental_source_settings
SET copernicus_enabled = true,
    copernicus_use_system_default = CASE
      WHEN NULLIF(btrim(copernicus_wms_url), '') IS NULL THEN true
      ELSE false
    END,
    copernicus_moisture_layer = CASE
      WHEN copernicus_moisture_layer = 'MOISTURE_INDEX' THEN 'NDMI'
      ELSE copernicus_moisture_layer
    END,
    copernicus_burn_layer = CASE
      WHEN copernicus_burn_layer = 'NBR_RAW' THEN 'NBR'
      ELSE copernicus_burn_layer
    END,
    updated_at = now();

DO $block$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'environment_sources_copernicus_layers_json_check'
  ) THEN
    ALTER TABLE environmental_source_settings
      ADD CONSTRAINT environment_sources_copernicus_layers_json_check
      CHECK (jsonb_typeof(copernicus_available_layers) = 'array');
  END IF;
END;
$block$;

CREATE INDEX IF NOT EXISTS idx_environment_sources_copernicus_status
  ON environmental_source_settings (
    copernicus_enabled,
    copernicus_use_system_default,
    copernicus_last_test_ok,
    copernicus_last_test_at DESC
  );

-- Limpia ejecuciones huérfanas y conserva como máximo una corrida activa por
-- organización antes de crear la guarda única.
UPDATE pipeline_runs
SET status = 'failed',
    finished_at = COALESCE(finished_at, now()),
    errors = COALESCE(errors, '[]'::jsonb) ||
      jsonb_build_array(jsonb_build_object(
        'stage', 'migration_guard',
        'detail', 'Ejecución huérfana cerrada al activar la guarda de concurrencia'
      ))
WHERE status = 'running'
  AND started_at < now() - interval '30 minutes';

WITH ranked AS (
  SELECT id,
         row_number() OVER (PARTITION BY org_id ORDER BY started_at DESC, id DESC) AS rn
  FROM pipeline_runs
  WHERE status = 'running'
)
UPDATE pipeline_runs p
SET status = 'failed',
    finished_at = COALESCE(p.finished_at, now()),
    errors = COALESCE(p.errors, '[]'::jsonb) ||
      jsonb_build_array(jsonb_build_object(
        'stage', 'migration_guard',
        'detail', 'Ejecución duplicada cerrada al activar la guarda de concurrencia'
      ))
FROM ranked r
WHERE p.id = r.id AND r.rn > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_pipeline_runs_one_running_per_org
  ON pipeline_runs(org_id)
  WHERE status = 'running';

COMMIT;
