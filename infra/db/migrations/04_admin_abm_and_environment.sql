-- EcoNexo Admin Core / ABM: estado, timestamps, geocercas circulares y auditoria.

ALTER TABLE organizations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE device_types ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE devices ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE rules ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE risk_zones ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE risk_zones ADD COLUMN IF NOT EXISTS center GEOGRAPHY(Point, 4326);
ALTER TABLE risk_zones ADD COLUMN IF NOT EXISTS radius_m DOUBLE PRECISION;

UPDATE risk_zones
SET center = COALESCE(center, ST_Centroid(area::geometry)::geography),
    radius_m = COALESCE(radius_m, sqrt(GREATEST(ST_Area(area), 1) / pi()))
WHERE center IS NULL OR radius_m IS NULL;

ALTER TABLE risk_zones ALTER COLUMN center SET NOT NULL;
ALTER TABLE risk_zones ALTER COLUMN radius_m SET NOT NULL;

DO $block$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'risk_zones_radius_check'
    ) THEN
        ALTER TABLE risk_zones
          ADD CONSTRAINT risk_zones_radius_check CHECK (radius_m BETWEEN 50 AND 100000);
    END IF;
END
$block$;

CREATE INDEX IF NOT EXISTS idx_risk_zones_center ON risk_zones USING GIST(center);
CREATE INDEX IF NOT EXISTS idx_users_org_active ON users(org_id, is_active);
CREATE INDEX IF NOT EXISTS idx_audit_events_resource ON audit_events(org_id, resource, created_at DESC);

CREATE OR REPLACE FUNCTION econexo_set_updated_at()
RETURNS trigger AS $fn$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

DO $block$
DECLARE
    table_name TEXT;
    trigger_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'organizations','users','device_types','devices','rules','risk_zones',
        'environmental_source_settings','impact_reports'
    ]
    LOOP
        trigger_name := 'trg_' || table_name || '_updated_at';
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger WHERE tgname = trigger_name AND NOT tgisinternal
        ) THEN
            EXECUTE format(
                'CREATE TRIGGER %I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION econexo_set_updated_at()',
                trigger_name, table_name
            );
        END IF;
    END LOOP;
END
$block$;
