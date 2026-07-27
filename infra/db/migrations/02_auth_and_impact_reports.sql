-- EcoNexo investor-ready: Google auth, consentimiento legal e informes compartibles.

ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider TEXT NOT NULL DEFAULT 'password';
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS legal_version TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_google_sub
    ON users(google_sub) WHERE google_sub IS NOT NULL;

DO $block$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'impact_report_status') THEN
        CREATE TYPE impact_report_status AS ENUM ('borrador', 'publicado', 'archivado');
    END IF;
END
$block$;

CREATE TABLE IF NOT EXISTS impact_reports (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    title             TEXT NOT NULL,
    recipient_type    TEXT NOT NULL,
    recipient_name    TEXT NOT NULL,
    period_start      DATE NOT NULL,
    period_end        DATE NOT NULL,
    executive_summary TEXT NOT NULL DEFAULT '',
    metrics           JSONB NOT NULL DEFAULT '{}',
    highlights        JSONB NOT NULL DEFAULT '[]',
    recommendations   JSONB NOT NULL DEFAULT '[]',
    status            impact_report_status NOT NULL DEFAULT 'borrador',
    public_token_hash TEXT,
    published_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT impact_report_period CHECK (period_end >= period_start)
);
CREATE INDEX IF NOT EXISTS idx_impact_reports_org_created
    ON impact_reports(org_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_impact_reports_public_token
    ON impact_reports(public_token_hash) WHERE public_token_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS audit_events (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id      UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    resource    TEXT NOT NULL,
    resource_id UUID,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_events_org_created
    ON audit_events(org_id, created_at DESC);
