-- EcoNexo 1.0.0-rc.2 - endurecimiento de integridad de base de datos.
--
-- Esta migración es deliberadamente conservadora para bases existentes:
-- los CHECK y FK nuevos se agregan NOT VALID. PostgreSQL los aplica a toda
-- escritura nueva, pero los datos históricos deben auditarse y corregirse
-- antes de ejecutar ALTER TABLE ... VALIDATE CONSTRAINT.

BEGIN;

-- ---------------------------------------------------------------------------
-- Restricciones de dominio. NOT VALID evita bloquear la migración por datos
-- históricos, sin dejar entrar nuevos valores inválidos.
-- ---------------------------------------------------------------------------

DO $block$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.organizations'::regclass
      AND conname='organizations_baseline_response_positive_check'
  ) THEN
    ALTER TABLE organizations
      ADD CONSTRAINT organizations_baseline_response_positive_check
      CHECK (baseline_response_s > 0) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.users'::regclass
      AND conname='users_auth_provider_check'
  ) THEN
    ALTER TABLE users
      ADD CONSTRAINT users_auth_provider_check
      CHECK (auth_provider IN ('password','google')) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.device_types'::regclass
      AND conname='device_types_variables_array_check'
  ) THEN
    ALTER TABLE device_types
      ADD CONSTRAINT device_types_variables_array_check
      CHECK (jsonb_typeof(variables)='array') NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.devices'::regclass
      AND conname='devices_battery_range_check'
  ) THEN
    ALTER TABLE devices
      ADD CONSTRAINT devices_battery_range_check
      CHECK (battery IS NULL OR battery BETWEEN 0 AND 100) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.citizens'::regclass
      AND conname='citizens_counts_nonnegative_check'
  ) THEN
    ALTER TABLE citizens
      ADD CONSTRAINT citizens_counts_nonnegative_check
      CHECK (valid_count >= 0 AND invalid_count >= 0) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.citizens'::regclass
      AND conname='citizens_reputation_range_check'
  ) THEN
    ALTER TABLE citizens
      ADD CONSTRAINT citizens_reputation_range_check
      CHECK (reputation BETWEEN 0 AND 1) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.citizen_reports'::regclass
      AND conname='citizen_reports_scores_range_check'
  ) THEN
    ALTER TABLE citizen_reports
      ADD CONSTRAINT citizen_reports_scores_range_check
      CHECK (
        (correlation_score IS NULL OR correlation_score BETWEEN 0 AND 1)
        AND
        (reputation_score IS NULL OR reputation_score BETWEEN 0 AND 1)
      ) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.satellite_detections'::regclass
      AND conname='satellite_detections_confidence_range_check'
  ) THEN
    ALTER TABLE satellite_detections
      ADD CONSTRAINT satellite_detections_confidence_range_check
      CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.rules'::regclass
      AND conname='rules_logic_window_check'
  ) THEN
    ALTER TABLE rules
      ADD CONSTRAINT rules_logic_window_check
      CHECK (condition_logic IN ('AND','OR') AND window_seconds > 0) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.rules'::regclass
      AND conname='rules_json_arrays_check'
  ) THEN
    ALTER TABLE rules
      ADD CONSTRAINT rules_json_arrays_check
      CHECK (
        jsonb_typeof(conditions)='array'
        AND jsonb_typeof(actions)='array'
      ) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.alerts'::regclass
      AND conname='alerts_confidence_range_check'
  ) THEN
    ALTER TABLE alerts
      ADD CONSTRAINT alerts_confidence_range_check
      CHECK (confidence BETWEEN 0 AND 1) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.alerts'::regclass
      AND conname='alerts_timeline_check'
  ) THEN
    ALTER TABLE alerts
      ADD CONSTRAINT alerts_timeline_check
      CHECK (
        (acknowledged_at IS NULL OR acknowledged_at >= detected_at)
        AND
        (resolved_at IS NULL OR resolved_at >= detected_at)
        AND
        (
          acknowledged_at IS NULL OR resolved_at IS NULL
          OR resolved_at >= acknowledged_at
        )
      ) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.alert_sources'::regclass
      AND conname='alert_sources_weight_range_check'
  ) THEN
    ALTER TABLE alert_sources
      ADD CONSTRAINT alert_sources_weight_range_check
      CHECK (weight BETWEEN 0 AND 1) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.impact_reports'::regclass
      AND conname='impact_reports_json_shape_check'
  ) THEN
    ALTER TABLE impact_reports
      ADD CONSTRAINT impact_reports_json_shape_check
      CHECK (
        jsonb_typeof(metrics)='object'
        AND jsonb_typeof(highlights)='array'
        AND jsonb_typeof(recommendations)='array'
        AND jsonb_typeof(official_metadata)='object'
      ) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.audit_events'::regclass
      AND conname='audit_events_metadata_object_check'
  ) THEN
    ALTER TABLE audit_events
      ADD CONSTRAINT audit_events_metadata_object_check
      CHECK (jsonb_typeof(metadata)='object') NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.environmental_snapshots'::regclass
      AND conname='environmental_snapshots_json_object_check'
  ) THEN
    ALTER TABLE environmental_snapshots
      ADD CONSTRAINT environmental_snapshots_json_object_check
      CHECK (jsonb_typeof(snapshot)='object') NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.organization_modules'::regclass
      AND conname='organization_modules_config_object_check'
  ) THEN
    ALTER TABLE organization_modules
      ADD CONSTRAINT organization_modules_config_object_check
      CHECK (jsonb_typeof(config)='object') NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.organization_modules'::regclass
      AND conname='organization_modules_period_check'
  ) THEN
    ALTER TABLE organization_modules
      ADD CONSTRAINT organization_modules_period_check
      CHECK (expires_at IS NULL OR expires_at > starts_at) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.alert_shares'::regclass
      AND conname='alert_shares_metadata_object_check'
  ) THEN
    ALTER TABLE alert_shares
      ADD CONSTRAINT alert_shares_metadata_object_check
      CHECK (jsonb_typeof(metadata)='object') NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.environmental_source_settings'::regclass
      AND conname='environment_sources_copernicus_config_check'
  ) THEN
    ALTER TABLE environmental_source_settings
      ADD CONSTRAINT environment_sources_copernicus_config_check
      CHECK (
        NOT copernicus_enabled
        OR NULLIF(btrim(copernicus_wms_url), '') IS NOT NULL
      ) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.environmental_source_settings'::regclass
      AND conname='environment_sources_copernicus_layers_check'
  ) THEN
    ALTER TABLE environmental_source_settings
      ADD CONSTRAINT environment_sources_copernicus_layers_check
      CHECK (
        btrim(copernicus_true_color_layer) <> ''
        AND btrim(copernicus_ndvi_layer) <> ''
        AND btrim(copernicus_moisture_layer) <> ''
        AND btrim(copernicus_burn_layer) <> ''
      ) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.territory_boundaries'::regclass
      AND conname='territory_boundaries_valid_geometry_check'
  ) THEN
    ALTER TABLE territory_boundaries
      ADD CONSTRAINT territory_boundaries_valid_geometry_check
      CHECK (NOT ST_IsEmpty(boundary) AND ST_IsValid(boundary)) NOT VALID;
  END IF;
END;
$block$;

-- ---------------------------------------------------------------------------
-- Índices de las columnas FK que no estaban cubiertas por un índice cuyo
-- primer campo fuera la referencia. Reducen scans y bloqueos al borrar padres.
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_devices_device_type
  ON devices(device_type_id);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_citizen
  ON citizen_reports(citizen_id);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_alert
  ON citizen_reports(alert_id);
CREATE INDEX IF NOT EXISTS idx_satellite_detections_org_acquired
  ON satellite_detections(org_id, acquired_at DESC);
CREATE INDEX IF NOT EXISTS idx_rules_zone
  ON rules(zone_id);
CREATE INDEX IF NOT EXISTS idx_alerts_rule
  ON alerts(rule_id);
CREATE INDEX IF NOT EXISTS idx_alerts_device
  ON alerts(device_id);
CREATE INDEX IF NOT EXISTS idx_alerts_assigned_to
  ON alerts(assigned_to);
CREATE INDEX IF NOT EXISTS idx_alert_events_user
  ON alert_events(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_alert
  ON notifications(alert_id);
CREATE INDEX IF NOT EXISTS idx_impact_reports_created_by
  ON impact_reports(created_by);
CREATE INDEX IF NOT EXISTS idx_audit_events_user
  ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_environment_source_settings_updated_by
  ON environmental_source_settings(updated_by);
CREATE INDEX IF NOT EXISTS idx_environmental_snapshots_created_by
  ON environmental_snapshots(created_by);
CREATE INDEX IF NOT EXISTS idx_organization_modules_created_by
  ON organization_modules(created_by);
CREATE INDEX IF NOT EXISTS idx_alert_shares_user
  ON alert_shares(user_id);

-- PostgreSQL 16 exige una clave UNIQUE coincidente para cada FK compuesta.
-- (id) ya es globalmente único; estos índices agregan la identidad de tenant
-- para que la propia FK pueda comprobar que ambos registros pertenecen a la
-- misma organización.
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_org_id
  ON users(org_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_device_types_org_id
  ON device_types(org_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_devices_org_id
  ON devices(org_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_risk_zones_org_id
  ON risk_zones(org_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_rules_org_id
  ON rules(org_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_alerts_org_id
  ON alerts(org_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_environmental_snapshots_org_id
  ON environmental_snapshots(org_id, id);

-- El login compara emails sin distinguir mayúsculas. La misma regla debe
-- existir en la base. Si hay duplicados históricos, el trigger impide crear
-- otros y la vista de auditoría bloquea el lanzamiento hasta depurarlos.
CREATE OR REPLACE FUNCTION econexo_enforce_normalized_user_email()
RETURNS trigger AS $fn$
DECLARE
  normalized_email text;
BEGIN
  normalized_email := lower(btrim(NEW.email));
  PERFORM pg_advisory_xact_lock(hashtextextended(normalized_email, 0));
  IF EXISTS (
    SELECT 1
    FROM users existing_user
    WHERE lower(btrim(existing_user.email))=normalized_email
      AND existing_user.id IS DISTINCT FROM NEW.id
  ) THEN
    RAISE EXCEPTION 'Ya existe un usuario con el email normalizado %', normalized_email
      USING ERRCODE='23505',
            CONSTRAINT='uq_users_email_normalized';
  END IF;
  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_normalized_email ON users;
CREATE TRIGGER trg_users_normalized_email
  BEFORE INSERT OR UPDATE OF email ON users
  FOR EACH ROW EXECUTE FUNCTION econexo_enforce_normalized_user_email();

DO $block$
BEGIN
  IF to_regclass('public.uq_users_email_normalized') IS NULL THEN
    IF NOT EXISTS (
      SELECT 1
      FROM users
      GROUP BY lower(btrim(email))
      HAVING count(*) > 1
    ) THEN
      CREATE UNIQUE INDEX uq_users_email_normalized
        ON users(lower(btrim(email)));
    ELSE
      RAISE WARNING
        'No se creo uq_users_email_normalized: hay emails normalizados duplicados';
    END IF;
  END IF;
END;
$block$;

-- ---------------------------------------------------------------------------
-- Integridad multi-tenant. Las FK simples originales se conservan hasta que
-- estas FK compuestas sean validadas, para no dejar referencias históricas
-- cruzadas colgando ante un DELETE del padre.
--
-- En ON DELETE SET NULL se indica sólo la columna de referencia: org_id es
-- NOT NULL y nunca debe borrarse como efecto lateral (sintaxis de PostgreSQL 16).
-- ---------------------------------------------------------------------------

DO $block$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.devices'::regclass
      AND conname='fk_devices_org_device_type'
  ) THEN
    ALTER TABLE devices
      ADD CONSTRAINT fk_devices_org_device_type
      FOREIGN KEY (org_id, device_type_id)
      REFERENCES device_types(org_id, id)
      ON DELETE SET NULL (device_type_id) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.readings'::regclass
      AND conname='fk_readings_org_device'
  ) THEN
    ALTER TABLE readings
      ADD CONSTRAINT fk_readings_org_device
      FOREIGN KEY (org_id, device_id)
      REFERENCES devices(org_id, id)
      ON DELETE CASCADE NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.rules'::regclass
      AND conname='fk_rules_org_zone'
  ) THEN
    ALTER TABLE rules
      ADD CONSTRAINT fk_rules_org_zone
      FOREIGN KEY (org_id, zone_id)
      REFERENCES risk_zones(org_id, id)
      ON DELETE SET NULL (zone_id) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.alerts'::regclass
      AND conname='fk_alerts_org_rule'
  ) THEN
    ALTER TABLE alerts
      ADD CONSTRAINT fk_alerts_org_rule
      FOREIGN KEY (org_id, rule_id)
      REFERENCES rules(org_id, id)
      ON DELETE SET NULL (rule_id) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.alerts'::regclass
      AND conname='fk_alerts_org_device'
  ) THEN
    ALTER TABLE alerts
      ADD CONSTRAINT fk_alerts_org_device
      FOREIGN KEY (org_id, device_id)
      REFERENCES devices(org_id, id)
      ON DELETE SET NULL (device_id) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.alerts'::regclass
      AND conname='fk_alerts_org_assigned_to'
  ) THEN
    ALTER TABLE alerts
      ADD CONSTRAINT fk_alerts_org_assigned_to
      FOREIGN KEY (org_id, assigned_to)
      REFERENCES users(org_id, id)
      ON DELETE SET NULL (assigned_to) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.citizen_reports'::regclass
      AND conname='fk_citizen_reports_org_alert'
  ) THEN
    ALTER TABLE citizen_reports
      ADD CONSTRAINT fk_citizen_reports_org_alert
      FOREIGN KEY (org_id, alert_id)
      REFERENCES alerts(org_id, id)
      ON DELETE SET NULL (alert_id) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.notifications'::regclass
      AND conname='fk_notifications_org_alert'
  ) THEN
    ALTER TABLE notifications
      ADD CONSTRAINT fk_notifications_org_alert
      FOREIGN KEY (org_id, alert_id)
      REFERENCES alerts(org_id, id)
      ON DELETE CASCADE NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.impact_reports'::regclass
      AND conname='fk_impact_reports_org_created_by'
  ) THEN
    ALTER TABLE impact_reports
      ADD CONSTRAINT fk_impact_reports_org_created_by
      FOREIGN KEY (org_id, created_by)
      REFERENCES users(org_id, id)
      ON DELETE SET NULL (created_by) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.impact_reports'::regclass
      AND conname='fk_impact_reports_org_snapshot'
  ) THEN
    ALTER TABLE impact_reports
      ADD CONSTRAINT fk_impact_reports_org_snapshot
      FOREIGN KEY (org_id, environmental_snapshot_id)
      REFERENCES environmental_snapshots(org_id, id)
      ON DELETE SET NULL (environmental_snapshot_id) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.audit_events'::regclass
      AND conname='fk_audit_events_org_user'
  ) THEN
    ALTER TABLE audit_events
      ADD CONSTRAINT fk_audit_events_org_user
      FOREIGN KEY (org_id, user_id)
      REFERENCES users(org_id, id)
      ON DELETE SET NULL (user_id) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.environmental_source_settings'::regclass
      AND conname='fk_environment_source_settings_org_user'
  ) THEN
    ALTER TABLE environmental_source_settings
      ADD CONSTRAINT fk_environment_source_settings_org_user
      FOREIGN KEY (org_id, updated_by)
      REFERENCES users(org_id, id)
      ON DELETE SET NULL (updated_by) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.environmental_snapshots'::regclass
      AND conname='fk_environmental_snapshots_org_user'
  ) THEN
    ALTER TABLE environmental_snapshots
      ADD CONSTRAINT fk_environmental_snapshots_org_user
      FOREIGN KEY (org_id, created_by)
      REFERENCES users(org_id, id)
      ON DELETE SET NULL (created_by) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.organization_modules'::regclass
      AND conname='fk_organization_modules_org_user'
  ) THEN
    ALTER TABLE organization_modules
      ADD CONSTRAINT fk_organization_modules_org_user
      FOREIGN KEY (org_id, created_by)
      REFERENCES users(org_id, id)
      ON DELETE SET NULL (created_by) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.alert_shares'::regclass
      AND conname='fk_alert_shares_org_user'
  ) THEN
    ALTER TABLE alert_shares
      ADD CONSTRAINT fk_alert_shares_org_user
      FOREIGN KEY (org_id, user_id)
      REFERENCES users(org_id, id)
      ON DELETE SET NULL (user_id) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.alert_shares'::regclass
      AND conname='fk_alert_shares_org_snapshot'
  ) THEN
    ALTER TABLE alert_shares
      ADD CONSTRAINT fk_alert_shares_org_snapshot
      FOREIGN KEY (org_id, snapshot_id)
      REFERENCES environmental_snapshots(org_id, id)
      ON DELETE SET NULL (snapshot_id) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.alert_shares'::regclass
      AND conname='fk_alert_shares_org_alert'
  ) THEN
    ALTER TABLE alert_shares
      ADD CONSTRAINT fk_alert_shares_org_alert
      FOREIGN KEY (org_id, alert_id)
      REFERENCES alerts(org_id, id)
      ON DELETE SET NULL (alert_id) NOT VALID;
  END IF;
END;
$block$;

-- ---------------------------------------------------------------------------
-- Guardia territorial mutable.
--
-- Un CHECK de PostgreSQL debe comportarse como una expresión inmutable. Los
-- CHECK de 06/07/09 llamaban una función que, desde 08, consulta una tabla cuyo
-- límite puede cambiar. Se reemplazan por triggers: siguen protegiendo cada
-- INSERT/UPDATE, sin prometer a PostgreSQL que la frontera sea inmutable.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION econexo_covered_by_misiones(value geography)
RETURNS boolean AS $fn$
  SELECT COALESCE(
    (
      SELECT CASE
        WHEN ST_IsEmpty(tb.boundary) OR NOT ST_IsValid(tb.boundary) THEN false
        ELSE ST_Covers(tb.boundary, value::geometry)
      END
      FROM territory_boundaries tb
      WHERE tb.province='Misiones'
      ORDER BY tb.is_official DESC,
               tb.fetched_at DESC NULLS LAST,
               tb.updated_at DESC,
               tb.id DESC
      LIMIT 1
    ),
    false
  );
$fn$ LANGUAGE sql STABLE STRICT;

CREATE OR REPLACE FUNCTION econexo_inside_misiones(point_value geography)
RETURNS boolean AS $fn$
  SELECT econexo_covered_by_misiones(point_value);
$fn$ LANGUAGE sql STABLE STRICT;

CREATE OR REPLACE FUNCTION econexo_enforce_location_inside_misiones()
RETURNS trigger AS $fn$
BEGIN
  IF NOT COALESCE(econexo_inside_misiones(NEW.location), false) THEN
    RAISE EXCEPTION 'La ubicación de % debe quedar dentro de Misiones', TG_TABLE_NAME
      USING ERRCODE='23514',
            CONSTRAINT=TG_TABLE_NAME || '_inside_misiones_trigger';
  END IF;
  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION econexo_enforce_risk_zone_inside_misiones()
RETURNS trigger AS $fn$
BEGIN
  IF ST_IsEmpty(NEW.area::geometry) OR NOT ST_IsValid(NEW.area::geometry) THEN
    RAISE EXCEPTION 'La geometría de la zona de riesgo debe ser válida y no vacía'
      USING ERRCODE='23514',
            CONSTRAINT='risk_zones_valid_area_trigger';
  END IF;

  IF NOT ST_Covers(NEW.area::geometry, NEW.center::geometry) THEN
    RAISE EXCEPTION 'El centro de la zona de riesgo debe pertenecer a su área'
      USING ERRCODE='23514',
            CONSTRAINT='risk_zones_center_in_area_trigger';
  END IF;

  IF NOT COALESCE(econexo_inside_misiones(NEW.center), false)
     OR NOT COALESCE(econexo_covered_by_misiones(NEW.area), false) THEN
    RAISE EXCEPTION 'El centro y el área completa de la zona deben quedar dentro de Misiones'
      USING ERRCODE='23514',
            CONSTRAINT='risk_zones_inside_misiones_trigger';
  END IF;
  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION econexo_enforce_environment_source_inside_misiones()
RETURNS trigger AS $fn$
DECLARE
  point_value geography;
BEGIN
  point_value := ST_MakePoint(NEW.default_longitude, NEW.default_latitude)::geography;
  IF NOT COALESCE(econexo_inside_misiones(point_value), false) THEN
    RAISE EXCEPTION 'El centro de fuentes ambientales debe quedar dentro de Misiones'
      USING ERRCODE='23514',
            CONSTRAINT='environment_sources_inside_misiones_trigger';
  END IF;
  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

ALTER TABLE devices
  DROP CONSTRAINT IF EXISTS devices_inside_misiones_check;
ALTER TABLE citizen_reports
  DROP CONSTRAINT IF EXISTS reports_inside_misiones_check;
ALTER TABLE alerts
  DROP CONSTRAINT IF EXISTS alerts_inside_misiones_check;
ALTER TABLE environmental_snapshots
  DROP CONSTRAINT IF EXISTS snapshots_inside_misiones_check;
ALTER TABLE risk_zones
  DROP CONSTRAINT IF EXISTS risk_zones_inside_misiones_check;
ALTER TABLE satellite_detections
  DROP CONSTRAINT IF EXISTS satellite_inside_misiones_check;
ALTER TABLE environmental_source_settings
  DROP CONSTRAINT IF EXISTS environment_sources_inside_misiones_check;

DROP TRIGGER IF EXISTS trg_devices_inside_misiones ON devices;
CREATE TRIGGER trg_devices_inside_misiones
  BEFORE INSERT OR UPDATE OF location ON devices
  FOR EACH ROW EXECUTE FUNCTION econexo_enforce_location_inside_misiones();

DROP TRIGGER IF EXISTS trg_reports_inside_misiones ON citizen_reports;
CREATE TRIGGER trg_reports_inside_misiones
  BEFORE INSERT OR UPDATE OF location ON citizen_reports
  FOR EACH ROW EXECUTE FUNCTION econexo_enforce_location_inside_misiones();

DROP TRIGGER IF EXISTS trg_alerts_inside_misiones ON alerts;
CREATE TRIGGER trg_alerts_inside_misiones
  BEFORE INSERT OR UPDATE OF location ON alerts
  FOR EACH ROW EXECUTE FUNCTION econexo_enforce_location_inside_misiones();

DROP TRIGGER IF EXISTS trg_snapshots_inside_misiones ON environmental_snapshots;
CREATE TRIGGER trg_snapshots_inside_misiones
  BEFORE INSERT OR UPDATE OF location ON environmental_snapshots
  FOR EACH ROW EXECUTE FUNCTION econexo_enforce_location_inside_misiones();

DROP TRIGGER IF EXISTS trg_satellite_inside_misiones ON satellite_detections;
CREATE TRIGGER trg_satellite_inside_misiones
  BEFORE INSERT OR UPDATE OF location ON satellite_detections
  FOR EACH ROW EXECUTE FUNCTION econexo_enforce_location_inside_misiones();

DROP TRIGGER IF EXISTS trg_risk_zones_inside_misiones ON risk_zones;
CREATE TRIGGER trg_risk_zones_inside_misiones
  BEFORE INSERT OR UPDATE OF center, area ON risk_zones
  FOR EACH ROW EXECUTE FUNCTION econexo_enforce_risk_zone_inside_misiones();

DROP TRIGGER IF EXISTS trg_environment_sources_inside_misiones
  ON environmental_source_settings;
CREATE TRIGGER trg_environment_sources_inside_misiones
  BEFORE INSERT OR UPDATE OF default_latitude, default_longitude
  ON environmental_source_settings
  FOR EACH ROW EXECUTE FUNCTION econexo_enforce_environment_source_inside_misiones();

-- La auditoría territorial histórica ahora comprueba el polígono completo de
-- cada zona de riesgo, no solamente su centro.
CREATE OR REPLACE VIEW misiones_external_data_audit AS
SELECT 'devices'::text AS resource, count(*)::bigint AS external_rows
FROM devices WHERE NOT econexo_inside_misiones(location)
UNION ALL
SELECT 'alerts', count(*)::bigint
FROM alerts WHERE NOT econexo_inside_misiones(location)
UNION ALL
SELECT 'citizen_reports', count(*)::bigint
FROM citizen_reports WHERE NOT econexo_inside_misiones(location)
UNION ALL
SELECT 'satellite_detections', count(*)::bigint
FROM satellite_detections WHERE NOT econexo_inside_misiones(location)
UNION ALL
SELECT 'environmental_snapshots', count(*)::bigint
FROM environmental_snapshots WHERE NOT econexo_inside_misiones(location)
UNION ALL
SELECT 'risk_zones', count(*)::bigint
FROM risk_zones
WHERE NOT (
  econexo_inside_misiones(center)
  AND econexo_covered_by_misiones(area)
)
UNION ALL
SELECT 'environmental_source_settings', count(*)::bigint
FROM environmental_source_settings
WHERE NOT econexo_inside_misiones(
  ST_MakePoint(default_longitude, default_latitude)::geography
);

-- En una base limpia, todos los CHECK/FK NOT VALID pueden validarse de
-- inmediato. En una base existente, cada violación histórica deja sólo esa
-- restricción pendiente y queda expuesta por database_integrity_audit.
DO $block$
DECLARE
  pending record;
BEGIN
  FOR pending IN
    SELECT r.oid::regclass AS table_name, c.conname AS constraint_name
    FROM pg_constraint c
    JOIN pg_class r ON r.oid=c.conrelid
    JOIN pg_namespace n ON n.oid=r.relnamespace
    WHERE n.nspname='public'
      AND r.relkind IN ('r','p')
      AND c.contype IN ('c','f')
      AND NOT c.convalidated
    ORDER BY r.relname, c.conname
  LOOP
    BEGIN
      EXECUTE format(
        'ALTER TABLE %s VALIDATE CONSTRAINT %I',
        pending.table_name,
        pending.constraint_name
      );
    EXCEPTION
      WHEN check_violation OR foreign_key_violation THEN
        RAISE WARNING
          'Constraint %.% sigue NOT VALID por datos históricos incompatibles',
          pending.table_name,
          pending.constraint_name;
    END;
  END LOOP;
END;
$block$;

-- ---------------------------------------------------------------------------
-- Vista única de auditoría: cada fila es una regla y su cantidad de
-- violaciones históricas. Debe devolver cero en todas las filas antes de
-- validar constraints y habilitar producción.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW database_integrity_audit AS
SELECT 'unvalidated_constraints'::text AS check_name, count(*)::bigint AS violations
FROM pg_constraint c
JOIN pg_class r ON r.oid=c.conrelid
JOIN pg_namespace n ON n.oid=r.relnamespace
WHERE n.nspname='public'
  AND r.relkind IN ('r','p')
  AND c.contype IN ('c','f')
  AND NOT c.convalidated
UNION ALL
SELECT 'territorial_rows_outside', COALESCE(sum(external_rows), 0)::bigint
FROM misiones_external_data_audit
UNION ALL
SELECT 'organizations_outside_misiones', count(*)::bigint
FROM organizations
WHERE province IS NULL OR lower(btrim(province)) <> 'misiones'
UNION ALL
SELECT 'invalid_active_boundaries', count(*)::bigint
FROM territory_boundaries
WHERE province='Misiones'
  AND (ST_IsEmpty(boundary) OR NOT ST_IsValid(boundary))
UNION ALL
SELECT 'duplicate_normalized_user_emails', count(*)::bigint
FROM (
  SELECT lower(btrim(email))
  FROM users
  GROUP BY lower(btrim(email))
  HAVING count(*) > 1
) duplicated_emails
UNION ALL
SELECT 'invalid_numeric_scales', (
    (SELECT count(*) FROM devices
      WHERE battery IS NOT NULL AND NOT (battery BETWEEN 0 AND 100))
  + (SELECT count(*) FROM citizens
      WHERE valid_count < 0 OR invalid_count < 0 OR NOT (reputation BETWEEN 0 AND 1))
  + (SELECT count(*) FROM citizen_reports
      WHERE (correlation_score IS NOT NULL AND NOT (correlation_score BETWEEN 0 AND 1))
         OR (reputation_score IS NOT NULL AND NOT (reputation_score BETWEEN 0 AND 1)))
  + (SELECT count(*) FROM satellite_detections
      WHERE confidence IS NOT NULL AND NOT (confidence BETWEEN 0 AND 1))
  + (SELECT count(*) FROM alerts
      WHERE NOT (confidence BETWEEN 0 AND 1))
  + (SELECT count(*) FROM alert_sources
      WHERE NOT (weight BETWEEN 0 AND 1))
)::bigint
UNION ALL
SELECT 'invalid_json_shapes', (
    (SELECT count(*) FROM device_types
      WHERE jsonb_typeof(variables) <> 'array')
  + (SELECT count(*) FROM rules
      WHERE jsonb_typeof(conditions) <> 'array'
         OR jsonb_typeof(actions) <> 'array')
  + (SELECT count(*) FROM impact_reports
      WHERE jsonb_typeof(metrics) <> 'object'
         OR jsonb_typeof(highlights) <> 'array'
         OR jsonb_typeof(recommendations) <> 'array'
         OR jsonb_typeof(official_metadata) <> 'object')
  + (SELECT count(*) FROM audit_events
      WHERE jsonb_typeof(metadata) <> 'object')
  + (SELECT count(*) FROM environmental_snapshots
      WHERE jsonb_typeof(snapshot) <> 'object')
  + (SELECT count(*) FROM organization_modules
      WHERE jsonb_typeof(config) <> 'object')
  + (SELECT count(*) FROM alert_shares
      WHERE jsonb_typeof(metadata) <> 'object')
)::bigint
UNION ALL
SELECT 'invalid_copernicus_configuration', count(*)::bigint
FROM environmental_source_settings
WHERE (
    copernicus_enabled
    AND NULLIF(btrim(copernicus_wms_url), '') IS NULL
  )
  OR (
    copernicus_wms_url IS NOT NULL
    AND btrim(copernicus_wms_url) <> ''
    AND copernicus_wms_url !~
      '^https://sh\.dataspace\.copernicus\.eu/ogc/wms/[A-Za-z0-9-]+/?$'
  )
  OR btrim(copernicus_true_color_layer)=''
  OR btrim(copernicus_ndvi_layer)=''
  OR btrim(copernicus_moisture_layer)=''
  OR btrim(copernicus_burn_layer)=''
UNION ALL
SELECT 'invalid_alert_timelines', count(*)::bigint
FROM alerts
WHERE (acknowledged_at IS NOT NULL AND acknowledged_at < detected_at)
   OR (resolved_at IS NOT NULL AND resolved_at < detected_at)
   OR (
     acknowledged_at IS NOT NULL AND resolved_at IS NOT NULL
     AND resolved_at < acknowledged_at
   )
UNION ALL
SELECT 'invalid_module_periods', count(*)::bigint
FROM organization_modules
WHERE expires_at IS NOT NULL AND expires_at <= starts_at
UNION ALL
SELECT 'cross_org_devices_device_types', count(*)::bigint
FROM devices d
JOIN device_types dt ON dt.id=d.device_type_id
WHERE d.org_id <> dt.org_id
UNION ALL
SELECT 'cross_org_readings_devices', count(*)::bigint
FROM readings r
JOIN devices d ON d.id=r.device_id
WHERE r.org_id <> d.org_id
UNION ALL
SELECT 'cross_org_rules_zones', count(*)::bigint
FROM rules r
JOIN risk_zones z ON z.id=r.zone_id
WHERE r.org_id <> z.org_id
UNION ALL
SELECT 'cross_org_alerts_rules', count(*)::bigint
FROM alerts a
JOIN rules r ON r.id=a.rule_id
WHERE a.org_id <> r.org_id
UNION ALL
SELECT 'cross_org_alerts_devices', count(*)::bigint
FROM alerts a
JOIN devices d ON d.id=a.device_id
WHERE a.org_id <> d.org_id
UNION ALL
SELECT 'cross_org_alerts_users', count(*)::bigint
FROM alerts a
JOIN users u ON u.id=a.assigned_to
WHERE a.org_id <> u.org_id
UNION ALL
SELECT 'cross_org_reports_alerts', count(*)::bigint
FROM citizen_reports cr
JOIN alerts a ON a.id=cr.alert_id
WHERE cr.org_id <> a.org_id
UNION ALL
SELECT 'cross_org_notifications_alerts', count(*)::bigint
FROM notifications n
JOIN alerts a ON a.id=n.alert_id
WHERE n.org_id <> a.org_id
UNION ALL
SELECT 'cross_org_impact_reports_users', count(*)::bigint
FROM impact_reports ir
JOIN users u ON u.id=ir.created_by
WHERE ir.org_id <> u.org_id
UNION ALL
SELECT 'cross_org_impact_reports_snapshots', count(*)::bigint
FROM impact_reports ir
JOIN environmental_snapshots es ON es.id=ir.environmental_snapshot_id
WHERE ir.org_id <> es.org_id
UNION ALL
SELECT 'cross_org_audit_events_users', count(*)::bigint
FROM audit_events ae
JOIN users u ON u.id=ae.user_id
WHERE ae.org_id IS NOT NULL AND ae.org_id <> u.org_id
UNION ALL
SELECT 'cross_org_environment_settings_users', count(*)::bigint
FROM environmental_source_settings ess
JOIN users u ON u.id=ess.updated_by
WHERE ess.org_id <> u.org_id
UNION ALL
SELECT 'cross_org_environment_snapshots_users', count(*)::bigint
FROM environmental_snapshots es
JOIN users u ON u.id=es.created_by
WHERE es.org_id <> u.org_id
UNION ALL
SELECT 'cross_org_modules_users', count(*)::bigint
FROM organization_modules om
JOIN users u ON u.id=om.created_by
WHERE om.org_id <> u.org_id
UNION ALL
SELECT 'cross_org_alert_shares_users', count(*)::bigint
FROM alert_shares ash
JOIN users u ON u.id=ash.user_id
WHERE ash.org_id <> u.org_id
UNION ALL
SELECT 'cross_org_alert_shares_snapshots', count(*)::bigint
FROM alert_shares ash
JOIN environmental_snapshots es ON es.id=ash.snapshot_id
WHERE ash.org_id <> es.org_id
UNION ALL
SELECT 'cross_org_alert_shares_alerts', count(*)::bigint
FROM alert_shares ash
JOIN alerts a ON a.id=ash.alert_id
WHERE ash.org_id <> a.org_id
UNION ALL
SELECT 'cross_org_environment_alert_links', count(*)::bigint
FROM environmental_alert_links eal
JOIN environmental_snapshots es ON es.id=eal.snapshot_id
JOIN alerts a ON a.id=eal.alert_id
WHERE es.org_id <> a.org_id
UNION ALL
SELECT 'cross_org_alert_events_users', count(*)::bigint
FROM alert_events ae
JOIN alerts a ON a.id=ae.alert_id
JOIN users u ON u.id=ae.user_id
WHERE a.org_id <> u.org_id;

COMMENT ON VIEW database_integrity_audit IS
  'Auditoría de integridad histórica. Todas las filas deben tener violations=0 antes de validar constraints y habilitar producción.';

-- CREATE OR REPLACE VIEW exige conservar las cuatro columnas originales en el
-- mismo orden. Los nuevos indicadores se agregan después de checked_at.
CREATE OR REPLACE VIEW misiones_launch_status AS
WITH active_boundary AS (
  SELECT is_official, boundary
  FROM territory_boundaries
  WHERE province='Misiones'
  ORDER BY is_official DESC,
           fetched_at DESC NULLS LAST,
           updated_at DESC,
           id DESC
  LIMIT 1
),
facts AS (
  SELECT
    COALESCE((SELECT is_official FROM active_boundary), false) AS official_boundary,
    COALESCE(
      (SELECT NOT ST_IsEmpty(boundary) AND ST_IsValid(boundary) FROM active_boundary),
      false
    ) AS boundary_valid,
    COALESCE(
      (SELECT sum(external_rows) FROM misiones_external_data_audit),
      0
    )::bigint AS external_rows,
    (
      SELECT count(*)::bigint
      FROM organizations
      WHERE province IS NULL OR lower(btrim(province)) <> 'misiones'
    ) AS organizations_outside_misiones,
    COALESCE(
      (
        SELECT violations FROM database_integrity_audit
        WHERE check_name='unvalidated_constraints'
      ),
      0
    )::bigint AS unvalidated_constraints,
    COALESCE(
      (SELECT sum(violations) FROM database_integrity_audit),
      0
    )::bigint AS integrity_violations
)
SELECT
  official_boundary,
  external_rows,
  external_rows=0 AS external_data_clean,
  now() AS checked_at,
  boundary_valid,
  organizations_outside_misiones,
  organizations_outside_misiones=0 AS organizations_clean,
  unvalidated_constraints,
  integrity_violations,
  integrity_violations=0 AS database_integrity_clean,
  (
    official_boundary
    AND boundary_valid
    AND external_rows=0
    AND organizations_outside_misiones=0
    AND unvalidated_constraints=0
    AND integrity_violations=0
  ) AS launch_ready
FROM facts;

COMMENT ON VIEW misiones_launch_status IS
  'Puerta de lanzamiento. Producción requiere launch_ready=true; además expone frontera, territorio, constraints e integridad histórica.';

COMMIT;
