-- EcoNexo Misiones 1.0.0-rc.3
-- Suscripciones limitadas, solicitudes comerciales y mensajes de acceso al panel admin.
-- Idempotente.

CREATE TABLE IF NOT EXISTS subscription_plans (
    plan_key          TEXT PRIMARY KEY,
    display_name      TEXT NOT NULL,
    description       TEXT NOT NULL,
    price_min_usd     NUMERIC(12,2),
    price_max_usd     NUMERIC(12,2),
    billing_period    TEXT NOT NULL,
    duration_days     INTEGER,
    entitlements      JSONB NOT NULL DEFAULT '{}'::jsonb,
    active            BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_subscription_plan_billing CHECK (
      billing_period IN ('trial','one_time','monthly','annual','cohort')
    )
);

CREATE TABLE IF NOT EXISTS organization_subscriptions (
    org_id              UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    plan_key            TEXT NOT NULL REFERENCES subscription_plans(plan_key),
    status              TEXT NOT NULL DEFAULT 'trial',
    starts_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ,
    auto_renew          BOOLEAN NOT NULL DEFAULT false,
    custom_entitlements JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes               TEXT,
    activated_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    activation_source   TEXT NOT NULL DEFAULT 'manual',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_org_subscription_status CHECK (
      status IN ('pending','trial','active','past_due','suspended','expired','cancelled')
    ),
    CONSTRAINT ck_org_subscription_dates CHECK (
      expires_at IS NULL OR expires_at > starts_at
    )
);
CREATE INDEX IF NOT EXISTS idx_org_subscriptions_plan_status
  ON organization_subscriptions(plan_key, status, expires_at);

CREATE TABLE IF NOT EXISTS subscription_events (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id         UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    previous_plan  TEXT,
    next_plan      TEXT,
    previous_status TEXT,
    next_status    TEXT,
    actor_user_id  UUID REFERENCES users(id) ON DELETE SET NULL,
    metadata       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_subscription_events_org_created
  ON subscription_events(org_id, created_at DESC);

CREATE TABLE IF NOT EXISTS license_requests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    requested_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    requested_plan  TEXT NOT NULL REFERENCES subscription_plans(plan_key),
    message         TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    reviewed_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_license_request_status CHECK (
      status IN ('pending','approved','rejected','cancelled')
    )
);
CREATE INDEX IF NOT EXISTS idx_license_requests_status_created
  ON license_requests(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_license_requests_org_created
  ON license_requests(org_id, created_at DESC);

CREATE TABLE IF NOT EXISTS admin_notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL,
    visibility      TEXT NOT NULL DEFAULT 'org_admins',
    severity        TEXT NOT NULL DEFAULT 'info',
    title           TEXT NOT NULL,
    message         TEXT NOT NULL,
    actor_user_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_email     TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_admin_notification_visibility CHECK (
      visibility IN ('org_admins','platform_admins','both')
    ),
    CONSTRAINT ck_admin_notification_severity CHECK (
      severity IN ('info','success','warning','critical')
    )
);
CREATE INDEX IF NOT EXISTS idx_admin_notifications_org_created
  ON admin_notifications(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_notifications_visibility_created
  ON admin_notifications(visibility, created_at DESC);

CREATE TABLE IF NOT EXISTS admin_notification_reads (
    notification_id UUID NOT NULL REFERENCES admin_notifications(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    read_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (notification_id, user_id)
);

-- Catálogo comercial: precios extraídos del dossier; límites operativos editables.
INSERT INTO subscription_plans
  (plan_key, display_name, description, price_min_usd, price_max_usd,
   billing_period, duration_days, entitlements)
VALUES
('sandbox','Sandbox calificado','Entorno limitado para evaluación comercial; no reemplaza un piloto pago.',0,0,'trial',14,
 '{"max_users":2,"max_devices":2,"max_zones":1,"max_rules":2,"max_reports_per_month":1,"max_critical_layers":1,"municipality_limit":1,"report_frequency":"muestra","support_level":"autoservicio","api_access":false,"audit_export":false,"custom_models":false,"sla":false,"community_reports":true,"operational_alerts":false,"included_modules":["core"]}'::jsonb),
('diagnostic','Diagnóstico territorial','Mapa base, lectura de riesgo, propuesta de piloto y caso de uso priorizado.',2000,4000,'one_time',30,
 '{"max_users":3,"max_devices":0,"max_zones":1,"max_rules":0,"max_reports_per_month":1,"max_critical_layers":1,"municipality_limit":1,"report_frequency":"informe diagnóstico","support_level":"acompañamiento inicial","api_access":false,"audit_export":false,"custom_models":false,"sla":false,"community_reports":false,"operational_alerts":false,"included_modules":["core"]}'::jsonb),
('pilot_8_weeks','Piloto 8 semanas','Dashboard, tres capas críticas, validación, reportes y capacitación.',18000,35000,'one_time',56,
 '{"max_users":10,"max_devices":25,"max_zones":2,"max_rules":12,"max_reports_per_month":4,"max_critical_layers":3,"municipality_limit":2,"report_frequency":"semanal o quincenal","support_level":"acompañamiento de piloto","api_access":false,"audit_export":true,"custom_models":false,"sla":false,"community_reports":true,"operational_alerts":true,"included_modules":["core","fire_smoke","forestry_pests"]}'::jsonb),
('municipal','SaaS Municipal','Una municipalidad, alertas base, reportes mensuales y soporte limitado.',800,1500,'monthly',NULL,
 '{"max_users":10,"max_devices":50,"max_zones":5,"max_rules":20,"max_reports_per_month":4,"max_critical_layers":3,"municipality_limit":1,"report_frequency":"mensual","support_level":"limitado","api_access":false,"audit_export":false,"custom_models":false,"sla":false,"community_reports":true,"operational_alerts":true,"included_modules":["core"]}'::jsonb),
('province_pro','SaaS Provincia / Pro','Múltiples zonas, reportes quincenales, usuarios internos y playbook operativo.',3500,8000,'monthly',NULL,
 '{"max_users":50,"max_devices":500,"max_zones":30,"max_rules":100,"max_reports_per_month":12,"max_critical_layers":12,"municipality_limit":79,"report_frequency":"quincenal","support_level":"prioritario","api_access":false,"audit_export":true,"custom_models":false,"sla":false,"community_reports":true,"operational_alerts":true,"included_modules":["core"]}'::jsonb),
('enterprise','Enterprise minero / energético','SLA, integraciones, API, auditoría, modelos y evidencia personalizada.',12000,NULL,'monthly',NULL,
 '{"max_users":250,"max_devices":5000,"max_zones":250,"max_rules":1000,"max_reports_per_month":100,"max_critical_layers":50,"municipality_limit":79,"report_frequency":"personalizada","support_level":"dedicado","api_access":true,"audit_export":true,"custom_models":true,"sla":true,"community_reports":true,"operational_alerts":true,"included_modules":["core","fire_smoke","forestry_pests"]}'::jsonb),
('academy','Academia EcoNexo','Capacitación operativa, manuales, certificación interna y simulacros.',2000,6000,'cohort',45,
 '{"max_users":40,"max_devices":0,"max_zones":1,"max_rules":0,"max_reports_per_month":2,"max_critical_layers":1,"municipality_limit":1,"report_frequency":"simulación","support_level":"cohorte","api_access":false,"audit_export":false,"custom_models":false,"sla":false,"community_reports":true,"operational_alerts":false,"included_modules":["core"]}'::jsonb)
ON CONFLICT (plan_key) DO UPDATE SET
  display_name=EXCLUDED.display_name,
  description=EXCLUDED.description,
  price_min_usd=EXCLUDED.price_min_usd,
  price_max_usd=EXCLUDED.price_max_usd,
  billing_period=EXCLUDED.billing_period,
  duration_days=EXCLUDED.duration_days,
  entitlements=EXCLUDED.entitlements,
  active=true,
  updated_at=now();

-- Las organizaciones existentes reciben el piloto para no perder capacidades al migrar.
INSERT INTO organization_subscriptions
  (org_id, plan_key, status, starts_at, expires_at, activation_source)
SELECT id, 'pilot_8_weeks', 'trial', now(), now() + interval '56 days', 'migration_rc3'
FROM organizations
ON CONFLICT (org_id) DO NOTHING;

-- Mantener módulos incluidos en el piloto para instalaciones existentes.
UPDATE organization_modules om
SET status='trial',
    expires_at=COALESCE(om.expires_at, now() + interval '56 days'),
    updated_at=now()
FROM organization_subscriptions os
WHERE os.org_id=om.org_id
  AND os.plan_key='pilot_8_weeks'
  AND om.module_key IN ('core','fire_smoke','forestry_pests')
  AND om.status IN ('suspended','expired');

CREATE OR REPLACE FUNCTION econexo_touch_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_subscription_plans_updated_at ON subscription_plans;
CREATE TRIGGER trg_subscription_plans_updated_at
BEFORE UPDATE ON subscription_plans
FOR EACH ROW EXECUTE FUNCTION econexo_touch_updated_at();

DROP TRIGGER IF EXISTS trg_org_subscriptions_updated_at ON organization_subscriptions;
CREATE TRIGGER trg_org_subscriptions_updated_at
BEFORE UPDATE ON organization_subscriptions
FOR EACH ROW EXECUTE FUNCTION econexo_touch_updated_at();

DROP TRIGGER IF EXISTS trg_license_requests_updated_at ON license_requests;
CREATE TRIGGER trg_license_requests_updated_at
BEFORE UPDATE ON license_requests
FOR EACH ROW EXECUTE FUNCTION econexo_touch_updated_at();
