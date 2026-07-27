-- EcoNexo 0.4 - licencias modulares, app movil y trazabilidad de Alerta IA.
-- Idempotente: puede aplicarse sobre una base ya inicializada.

CREATE TABLE IF NOT EXISTS organization_modules (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    module_key  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'trial',
    plan_name   TEXT NOT NULL,
    starts_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ,
    config      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by  UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_organization_modules_key CHECK (module_key IN ('core','fire_smoke')),
    CONSTRAINT ck_organization_modules_status CHECK (status IN ('trial','active','suspended','expired')),
    UNIQUE (org_id, module_key)
);
CREATE INDEX IF NOT EXISTS idx_organization_modules_org ON organization_modules(org_id, module_key);

CREATE TABLE IF NOT EXISTS alert_shares (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    channel     TEXT NOT NULL,
    audience    TEXT NOT NULL,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    module_key  TEXT NOT NULL DEFAULT 'core',
    snapshot_id UUID REFERENCES environmental_snapshots(id) ON DELETE SET NULL,
    alert_id    UUID REFERENCES alerts(id) ON DELETE SET NULL,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_alert_shares_channel CHECK (channel IN ('whatsapp','telegram','copiar','email','otro')),
    CONSTRAINT ck_alert_shares_audience CHECK (audience IN ('medios','organizacion','laboratorio','emergencia','publico','otro')),
    CONSTRAINT ck_alert_shares_module CHECK (module_key IN ('core','fire_smoke'))
);
CREATE INDEX IF NOT EXISTS idx_alert_shares_org_created ON alert_shares(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_shares_snapshot ON alert_shares(snapshot_id) WHERE snapshot_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_alert_shares_alert ON alert_shares(alert_id) WHERE alert_id IS NOT NULL;

-- Toda organizacion posee el nucleo. El modulo de fuego/humo inicia como prueba
-- de 30 dias y puede ser activado, suspendido o renovado desde una consola comercial.
INSERT INTO organization_modules (org_id, module_key, status, plan_name, expires_at, config)
SELECT id, 'core', 'active', 'Plataforma EcoNexo', NULL,
       '{"plain_language":false,"human_approval_required":true}'::jsonb
FROM organizations
ON CONFLICT (org_id, module_key) DO NOTHING;

INSERT INTO organization_modules (org_id, module_key, status, plan_name, expires_at, config)
SELECT id, 'fire_smoke', 'trial', 'Focos de incendio forestal y humo', now() + interval '30 days',
       '{"plain_language":true,"human_approval_required":true,"emergency_numbers":["911","100","103","105"]}'::jsonb
FROM organizations
ON CONFLICT (org_id, module_key) DO NOTHING;
