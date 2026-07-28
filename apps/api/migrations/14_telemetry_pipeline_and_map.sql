-- EcoNexo 1.0.0-rc.6
-- Telemetria configurable, marcadores de mapa y ejecuciones del pipeline.
-- Idempotente.

BEGIN;

ALTER TABLE devices
  ADD COLUMN IF NOT EXISTS marker_shape TEXT NOT NULL DEFAULT 'circle';
ALTER TABLE devices
  ADD COLUMN IF NOT EXISTS telemetry_mode TEXT NOT NULL DEFAULT 'mqtt';
ALTER TABLE devices
  ADD COLUMN IF NOT EXISTS zone_id UUID REFERENCES risk_zones(id) ON DELETE SET NULL;
ALTER TABLE devices
  ADD COLUMN IF NOT EXISTS pipeline_enabled BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE devices
  ADD COLUMN IF NOT EXISTS telemetry_config JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE devices
  ADD COLUMN IF NOT EXISTS last_pipeline_at TIMESTAMPTZ;
ALTER TABLE devices
  ADD COLUMN IF NOT EXISTS last_pipeline_status TEXT;

DO $block$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='devices_marker_shape_check'
  ) THEN
    ALTER TABLE devices
      ADD CONSTRAINT devices_marker_shape_check
      CHECK (marker_shape IN ('circle','square','triangle'));
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='devices_telemetry_mode_check'
  ) THEN
    ALTER TABLE devices
      ADD CONSTRAINT devices_telemetry_mode_check
      CHECK (telemetry_mode IN ('mqtt','open_meteo','manual'));
  END IF;
END;
$block$;

CREATE INDEX IF NOT EXISTS idx_devices_zone ON devices(zone_id);
CREATE INDEX IF NOT EXISTS idx_devices_pipeline
  ON devices(org_id, pipeline_enabled, telemetry_mode, status);

CREATE TABLE IF NOT EXISTS telemetry_pipeline_settings (
  org_id              UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
  enabled             BOOLEAN NOT NULL DEFAULT true,
  auto_run            BOOLEAN NOT NULL DEFAULT false,
  interval_minutes    INTEGER NOT NULL DEFAULT 15,
  stale_minutes       INTEGER NOT NULL DEFAULT 30,
  refresh_firms       BOOLEAN NOT NULL DEFAULT true,
  evaluate_rules      BOOLEAN NOT NULL DEFAULT true,
  updated_by          UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT telemetry_pipeline_interval_check CHECK (interval_minutes BETWEEN 2 AND 1440),
  CONSTRAINT telemetry_pipeline_stale_check CHECK (stale_minutes BETWEEN 5 AND 10080)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id                UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  started_by            UUID REFERENCES users(id) ON DELETE SET NULL,
  source                TEXT NOT NULL DEFAULT 'command_core',
  status                TEXT NOT NULL DEFAULT 'running',
  started_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at           TIMESTAMPTZ,
  devices_total         INTEGER NOT NULL DEFAULT 0,
  devices_updated       INTEGER NOT NULL DEFAULT 0,
  readings_inserted     INTEGER NOT NULL DEFAULT 0,
  detections_ingested   INTEGER NOT NULL DEFAULT 0,
  alerts_created        INTEGER NOT NULL DEFAULT 0,
  errors                JSONB NOT NULL DEFAULT '[]'::jsonb,
  summary               JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT pipeline_run_status_check CHECK (status IN ('running','completed','partial','failed'))
);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_org_started
  ON pipeline_runs(org_id, started_at DESC);

ALTER TABLE satellite_detections
  ADD COLUMN IF NOT EXISTS dedup_key TEXT;
DROP INDEX IF EXISTS uq_satellite_detections_dedup;
CREATE UNIQUE INDEX uq_satellite_detections_dedup
  ON satellite_detections(dedup_key);

INSERT INTO telemetry_pipeline_settings(org_id)
SELECT id FROM organizations
ON CONFLICT (org_id) DO NOTHING;

COMMIT;
