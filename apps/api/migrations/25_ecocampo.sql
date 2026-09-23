BEGIN;
CREATE TABLE IF NOT EXISTS ecocampo_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lot_id UUID NOT NULL REFERENCES agro_lots(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    evidence JSONB NOT NULL,
    result JSONB NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ecocampo_history ON ecocampo_assessments(org_id, lot_id, created_at DESC);
UPDATE subscription_plans SET display_name='EcoCampo · Productor', price_min_usd=400, price_max_usd=400 WHERE plan_key='agro_productor';
UPDATE organization_modules SET plan_name='EcoCampo · inteligencia agropecuaria' WHERE module_key='agro';
CREATE TABLE IF NOT EXISTS ecocampo_satellite_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lot_id UUID NOT NULL REFERENCES agro_lots(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    polygon JSONB NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ecocampo_satellite_history ON ecocampo_satellite_runs(org_id, lot_id, created_at DESC);
COMMIT;
