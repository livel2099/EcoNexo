-- EcoNexo Misiones - gobernanza territorial para release candidate.
-- Idempotente. Completa controles que no estaban cubiertos por la migración 06.

BEGIN;

DO $block$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='satellite_inside_misiones_check') THEN
    ALTER TABLE satellite_detections ADD CONSTRAINT satellite_inside_misiones_check
      CHECK (econexo_inside_misiones(location)) NOT VALID;
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
SELECT 'environmental_snapshots', count(*)::bigint FROM environmental_snapshots WHERE NOT econexo_inside_misiones(location);

COMMENT ON VIEW misiones_external_data_audit IS
  'Auditoría de registros históricos fuera del alcance Misiones. Debe devolver cero para lanzamiento.';

COMMIT;
