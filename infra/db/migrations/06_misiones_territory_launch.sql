-- EcoNexo 1.0 Misiones - alcance territorial y controles de lanzamiento.
-- Idempotente. Los CHECK NOT VALID protegen nuevas escrituras sin bloquear
-- la migración por datos históricos que deban revisarse manualmente.

ALTER TABLE organizations ADD COLUMN IF NOT EXISTS province TEXT NOT NULL DEFAULT 'Misiones';
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS department TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS municipality TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS territory_scope TEXT NOT NULL DEFAULT 'provincial';

UPDATE organizations SET province='Misiones' WHERE province IS NULL OR btrim(province)='';

DO $block$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='organizations_territory_scope_check') THEN
    ALTER TABLE organizations ADD CONSTRAINT organizations_territory_scope_check
      CHECK (territory_scope IN ('provincial','departamental','municipal','area_operativa'));
  END IF;
END
$block$;

CREATE OR REPLACE FUNCTION econexo_inside_misiones(point_value geography)
RETURNS boolean AS $fn$
  SELECT ST_Covers(
    ST_GeomFromText(
      'POLYGON((-54.64 -25.50,-54.24 -25.70,-53.92 -25.95,-53.63 -26.25,-53.70 -26.62,-53.88 -27.02,-54.20 -27.36,-54.64 -27.62,-55.12 -27.93,-55.66 -28.18,-55.86 -27.84,-55.96 -27.37,-55.72 -27.06,-55.42 -26.70,-55.08 -26.35,-54.82 -25.98,-54.68 -25.66,-54.64 -25.50))',
      4326
    ),
    point_value::geometry
  );
$fn$ LANGUAGE sql IMMUTABLE STRICT;

DO $block$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='devices_inside_misiones_check') THEN
    ALTER TABLE devices ADD CONSTRAINT devices_inside_misiones_check
      CHECK (econexo_inside_misiones(location)) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='reports_inside_misiones_check') THEN
    ALTER TABLE citizen_reports ADD CONSTRAINT reports_inside_misiones_check
      CHECK (econexo_inside_misiones(location)) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='alerts_inside_misiones_check') THEN
    ALTER TABLE alerts ADD CONSTRAINT alerts_inside_misiones_check
      CHECK (econexo_inside_misiones(location)) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='snapshots_inside_misiones_check') THEN
    ALTER TABLE environmental_snapshots ADD CONSTRAINT snapshots_inside_misiones_check
      CHECK (econexo_inside_misiones(location)) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='risk_zones_inside_misiones_check') THEN
    ALTER TABLE risk_zones ADD CONSTRAINT risk_zones_inside_misiones_check
      CHECK (econexo_inside_misiones(center)) NOT VALID;
  END IF;
END
$block$;

-- Corrige centros por defecto antiguos que hayan quedado fuera de Misiones.
UPDATE environmental_source_settings
SET default_latitude=-26.92, default_longitude=-54.78, updated_at=now()
WHERE NOT econexo_inside_misiones(
  ST_MakePoint(default_longitude, default_latitude)::geography
);

-- El canal provincial vigente de aviso inmediato se comunica como 911.
UPDATE organization_modules
SET config = config || '{"province":"Misiones","emergency_number":"911","territorial_validation":true}'::jsonb,
    updated_at=now()
WHERE module_key IN ('core','fire_smoke');

CREATE INDEX IF NOT EXISTS idx_organizations_misiones_scope
  ON organizations(province, department, municipality, territory_scope);
