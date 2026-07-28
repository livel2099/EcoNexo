-- EcoNexo 1.0.0-rc.5
-- Consola general de plataforma y cambio obligatorio de contraseña inicial.
-- Idempotente.

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_users_platform_console
    ON users (is_active, role, created_at DESC);

COMMIT;
