-- EcoNexo Misiones 1.0.0-rc.1 - cierre territorial de lanzamiento.
-- Idempotente. Amplia auditoria, asegura el centro de fuentes y expone un
-- estado consolidado para la puerta de preproduccion.

BEGIN;

DO $block$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='organizations_misiones_only_check') THEN
    ALTER TABLE organizations ADD CONSTRAINT organizations_misiones_only_check
      CHECK (lower(btrim(province))='misiones') NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='environment_sources_inside_misiones_check') THEN
    ALTER TABLE environmental_source_settings ADD CONSTRAINT environment_sources_inside_misiones_check
      CHECK (econexo_inside_misiones(
        ST_MakePoint(default_longitude, default_latitude)::geography
      )) NOT VALID;
  END IF;
END;
$block$;

CREATE OR REPLACE VIEW misiones_external_data_audit AS
SELECT 'devices'::text AS resource, count(*)::bigint AS external_rows
FROM devices WHERE NOT econexo_inside_misiones(location)
UNION ALL
SELECT 'alerts', count(*)::bigint FROM alerts WHERE NOT econexo_inside_misiones(location)
UNION ALL
SELECT 'citizen_reports', count(*)::bigint FROM citizen_reports WHERE NOT econexo_inside_misiones(location)
UNION ALL
SELECT 'satellite_detections', count(*)::bigint FROM satellite_detections WHERE NOT econexo_inside_misiones(location)
UNION ALL
SELECT 'environmental_snapshots', count(*)::bigint FROM environmental_snapshots WHERE NOT econexo_inside_misiones(location)
UNION ALL
SELECT 'risk_zones', count(*)::bigint FROM risk_zones WHERE NOT econexo_inside_misiones(center)
UNION ALL
SELECT 'environmental_source_settings', count(*)::bigint
FROM environmental_source_settings
WHERE NOT econexo_inside_misiones(
  ST_MakePoint(default_longitude, default_latitude)::geography
);

CREATE OR REPLACE VIEW misiones_launch_status AS
SELECT
  EXISTS (
    SELECT 1 FROM territory_boundaries
    WHERE province='Misiones' AND is_official
  ) AS official_boundary,
  COALESCE((SELECT sum(external_rows) FROM misiones_external_data_audit), 0)::bigint AS external_rows,
  NOT EXISTS (
    SELECT 1 FROM misiones_external_data_audit WHERE external_rows > 0
  ) AS external_data_clean,
  now() AS checked_at;

COMMENT ON VIEW misiones_launch_status IS
  'Puerta territorial consolidada. Produccion requiere official_boundary=true y external_data_clean=true.';

COMMIT;
