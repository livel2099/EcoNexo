BEGIN;
ALTER TABLE organization_modules DROP CONSTRAINT IF EXISTS ck_organization_modules_key;
ALTER TABLE organization_modules ADD CONSTRAINT ck_organization_modules_key CHECK (module_key IN ('core','fire_smoke','forestry_pests','agro','ecocampo'));
ALTER TABLE alert_shares DROP CONSTRAINT IF EXISTS ck_alert_shares_module;
ALTER TABLE alert_shares ADD CONSTRAINT ck_alert_shares_module CHECK (module_key IN ('core','fire_smoke','forestry_pests','agro','ecocampo'));
UPDATE organization_modules SET plan_name='EcoNexo AG · inteligencia agronómica' WHERE module_key='agro';
UPDATE subscription_plans
SET display_name='Productor · EcoNexo AG + EcoCampo',
    entitlements=jsonb_set(entitlements, '{included_modules}', '["core","agro","ecocampo"]'::jsonb)
WHERE plan_key='agro_productor';
INSERT INTO organization_modules(org_id,module_key,status,plan_name,expires_at,config)
SELECT o.id,'ecocampo',
    CASE WHEN s.plan_key='agro_productor' AND s.status IN ('active','trial') AND (s.expires_at IS NULL OR s.expires_at>now()) THEN 'active' ELSE 'suspended' END,
    'EcoCampo · aptitud y producción agropecuaria',s.expires_at,'{}'::jsonb
FROM organizations o LEFT JOIN organization_subscriptions s ON s.org_id=o.id
ON CONFLICT(org_id,module_key) DO NOTHING;
COMMIT;