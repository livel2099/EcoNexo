-- EcoNexo Misiones 1.0.0-rc.2 - Copernicus runtime + sanidad forestal norte.
-- Idempotente.

ALTER TABLE environmental_source_settings
  ADD COLUMN IF NOT EXISTS copernicus_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS copernicus_wms_url TEXT,
  ADD COLUMN IF NOT EXISTS copernicus_true_color_layer TEXT NOT NULL DEFAULT 'TRUE_COLOR',
  ADD COLUMN IF NOT EXISTS copernicus_ndvi_layer TEXT NOT NULL DEFAULT 'NDVI',
  ADD COLUMN IF NOT EXISTS copernicus_moisture_layer TEXT NOT NULL DEFAULT 'MOISTURE_INDEX',
  ADD COLUMN IF NOT EXISTS copernicus_burn_layer TEXT NOT NULL DEFAULT 'NBR_RAW',
  ADD COLUMN IF NOT EXISTS forestry_pest_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS sinarame_radar_enabled BOOLEAN NOT NULL DEFAULT true;

DO $block$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='environment_sources_copernicus_https_check') THEN
    ALTER TABLE environmental_source_settings
      ADD CONSTRAINT environment_sources_copernicus_https_check
      CHECK (
        copernicus_wms_url IS NULL OR
        copernicus_wms_url = '' OR
        copernicus_wms_url ~ '^https://sh\.dataspace\.copernicus\.eu/ogc/wms/[A-Za-z0-9-]+/?$'
      ) NOT VALID;
  END IF;
END
$block$;

ALTER TABLE organization_modules DROP CONSTRAINT IF EXISTS ck_organization_modules_key;
ALTER TABLE organization_modules
  ADD CONSTRAINT ck_organization_modules_key
  CHECK (module_key IN ('core','fire_smoke','forestry_pests'));

ALTER TABLE alert_shares DROP CONSTRAINT IF EXISTS ck_alert_shares_module;
ALTER TABLE alert_shares
  ADD CONSTRAINT ck_alert_shares_module
  CHECK (module_key IN ('core','fire_smoke','forestry_pests'));

INSERT INTO organization_modules (org_id, module_key, status, plan_name, expires_at, config)
SELECT id, 'forestry_pests', 'trial', 'Vigilancia de plagas forestales', now() + interval '30 days',
       '{"plain_language":true,"human_approval_required":true,"focus_area":"San Antonio - General Manuel Belgrano","priority_pests":["Sirex noctilio","escolitidos","anomalias sanitarias en Pinus y Eucalyptus"]}'::jsonb
FROM organizations
ON CONFLICT (org_id, module_key) DO NOTHING;
