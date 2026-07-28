-- EcoNexo 1.0.0-rc.5
-- Baja lógica global de organizaciones para la consola de plataforma.
-- Idempotente.

BEGIN;

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

CREATE INDEX IF NOT EXISTS idx_organizations_active_created
    ON organizations (is_active, created_at DESC);

COMMIT;
