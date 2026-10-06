BEGIN;
-- Los registros existentes conservan su identidad de incendio y consentimiento.
ALTER TABLE predictive_models ADD COLUMN hazard TEXT NOT NULL DEFAULT 'fire';
ALTER TABLE predictive_settings ADD COLUMN hazard TEXT NOT NULL DEFAULT 'fire';
ALTER TABLE predictive_observations ADD COLUMN hazard TEXT NOT NULL DEFAULT 'fire';
ALTER TABLE predictions DROP CONSTRAINT predictions_hazard_check;
ALTER TABLE predictions ADD CHECK (hazard IN ('fire','hydric','health_heat','health_air'));
ALTER TABLE predictive_models ADD CHECK (hazard IN ('fire','hydric','health_heat','health_air'));
ALTER TABLE predictive_settings ADD CHECK (hazard IN ('fire','hydric','health_heat','health_air'));
ALTER TABLE predictive_observations ADD CHECK (hazard IN ('fire','hydric','health_heat','health_air'));
ALTER TABLE predictive_models ADD UNIQUE(id,org_id,horizon_hours,hazard);

-- Reemplazar las referencias a modelos por referencias al riesgo exacto.
DO $$
DECLARE c RECORD;
BEGIN
  FOR c IN SELECT conrelid::regclass AS relation,conname FROM pg_constraint
    WHERE conrelid IN ('predictive_settings'::regclass,'predictions'::regclass)
      AND contype='f' AND confrelid='predictive_models'::regclass
  LOOP
    EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I',c.relation,c.conname);
  END LOOP;
  FOR c IN SELECT conrelid::regclass AS relation,conname FROM pg_constraint
    WHERE (conrelid='predictive_settings'::regclass AND contype='p')
       OR (conrelid IN ('predictions'::regclass,'predictive_observations'::regclass) AND contype='u')
  LOOP
    EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I',c.relation,c.conname);
  END LOOP;
END;
$$;
ALTER TABLE predictive_settings ADD PRIMARY KEY(org_id,horizon_hours,hazard);
ALTER TABLE predictive_settings ADD FOREIGN KEY(active_model_id,org_id,horizon_hours,hazard)
  REFERENCES predictive_models(id,org_id,horizon_hours,hazard);
ALTER TABLE predictions ADD FOREIGN KEY(model_id,org_id,horizon_hours,hazard)
  REFERENCES predictive_models(id,org_id,horizon_hours,hazard);
ALTER TABLE predictions ADD UNIQUE(org_id,device_id,horizon_hours,issuance_day,model_version,hazard);
ALTER TABLE predictive_observations ADD UNIQUE(org_id,hazard,source,reference);
ALTER TABLE predictive_observations ADD UNIQUE(org_id,device_id,hazard,outcome,start_at,end_at,latitude,longitude);
CREATE INDEX idx_predictions_risk ON predictions(org_id,hazard,horizon_hours,issued_at DESC);
CREATE INDEX idx_observations_risk ON predictive_observations(org_id,hazard,device_id,start_at,end_at);
-- No se habilitan nuevas fuentes: cada riesgo requiere consentimiento explícito.
COMMIT;
