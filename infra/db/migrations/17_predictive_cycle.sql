BEGIN;

CREATE TABLE predictive_models (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES organizations(id),
  horizon_hours INTEGER NOT NULL CHECK (horizon_hours IN (6,24,72)),
  version TEXT NOT NULL,
  artifact JSONB NOT NULL,
  evaluation JSONB NOT NULL,
  eligible BOOLEAN NOT NULL DEFAULT false,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (org_id,created_by) REFERENCES users(org_id,id),
  UNIQUE (org_id,version), UNIQUE (id,org_id,horizon_hours)
);

CREATE TABLE predictive_settings (
  org_id UUID NOT NULL REFERENCES organizations(id),
  horizon_hours INTEGER NOT NULL CHECK (horizon_hours IN (6,24,72)),
  enabled BOOLEAN NOT NULL DEFAULT false,
  active_model_id UUID,
  PRIMARY KEY (org_id,horizon_hours),
  FOREIGN KEY (active_model_id,org_id,horizon_hours)
    REFERENCES predictive_models(id,org_id,horizon_hours)
);

CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES organizations(id),
  device_id UUID NOT NULL REFERENCES devices(id),
  device_name TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
  longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
  hazard TEXT NOT NULL DEFAULT 'fire' CHECK (hazard='fire'),
  horizon_hours INTEGER NOT NULL CHECK (horizon_hours IN (6,24,72)),
  issued_at TIMESTAMPTZ NOT NULL,
  valid_from TIMESTAMPTZ NOT NULL,
  valid_to TIMESTAMPTZ NOT NULL,
  issuance_day DATE NOT NULL,
  model_id UUID,
  model_version TEXT NOT NULL,
  risk_index DOUBLE PRECISION NOT NULL CHECK (risk_index BETWEEN 0 AND 1),
  probability DOUBLE PRECISION CHECK (probability BETWEEN 0 AND 1),
  threshold DOUBLE PRECISION NOT NULL CHECK (threshold > 0 AND threshold < 1),
  warning BOOLEAN NOT NULL,
  features JSONB NOT NULL,
  provenance JSONB NOT NULL,
  explanation JSONB NOT NULL,
  action TEXT NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (org_id,device_id) REFERENCES devices(org_id,id),
  FOREIGN KEY (model_id,org_id,horizon_hours) REFERENCES predictive_models(id,org_id,horizon_hours),
  UNIQUE (org_id,device_id,horizon_hours,issuance_day,model_version),
  CHECK (valid_from > issued_at AND valid_to > valid_from),
  CHECK (valid_to = valid_from + horizon_hours * interval '1 hour'),
  CHECK (issued_at <= recorded_at AND valid_to > recorded_at),
  CHECK ((model_id IS NULL AND probability IS NULL) OR (model_id IS NOT NULL AND probability IS NOT NULL))
);
CREATE INDEX idx_predictions_org_issued ON predictions(org_id,issued_at DESC);
CREATE INDEX idx_predictions_org_device_window ON predictions(org_id,device_id,valid_from,valid_to);

-- Una observación positiva es un incidente independiente. Una negativa es una
-- certificación de cobertura completa, nunca la ausencia de una alerta.
CREATE TABLE predictive_observations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES organizations(id),
  device_id UUID NOT NULL REFERENCES devices(id),
  latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
  longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
  outcome TEXT NOT NULL CHECK (outcome IN ('event','no_event')),
  start_at TIMESTAMPTZ NOT NULL,
  end_at TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('field_report','official_record','sensor_verified')),
  reference TEXT NOT NULL,
  notes TEXT NOT NULL,
  verified_by UUID NOT NULL REFERENCES users(id),
  verified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (org_id,device_id) REFERENCES devices(org_id,id),
  FOREIGN KEY (org_id,verified_by) REFERENCES users(org_id,id),
  UNIQUE(org_id,source,reference),
  UNIQUE(org_id,device_id,outcome,start_at,end_at,latitude,longitude),
  CHECK (end_at >= start_at AND end_at <= verified_at),
  CHECK ((outcome='event' AND end_at=start_at) OR (outcome='no_event' AND end_at>start_at))
);
CREATE INDEX idx_predictive_observations_scope ON predictive_observations(org_id,device_id,start_at,end_at);

-- El ledger y los artefactos conservan lo realmente emitido; solo cambia el
-- puntero del modelo activo en predictive_settings.
CREATE FUNCTION econexo_predictive_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'Predictive evidence is append-only';
END;
$$;
CREATE TRIGGER predictions_immutable BEFORE UPDATE OR DELETE ON predictions
  FOR EACH ROW EXECUTE FUNCTION econexo_predictive_append_only();
CREATE TRIGGER predictive_observations_immutable BEFORE UPDATE OR DELETE ON predictive_observations
  FOR EACH ROW EXECUTE FUNCTION econexo_predictive_append_only();
CREATE TRIGGER predictive_models_immutable BEFORE UPDATE OR DELETE ON predictive_models
  FOR EACH ROW EXECUTE FUNCTION econexo_predictive_append_only();

COMMIT;
