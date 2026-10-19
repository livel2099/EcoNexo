CREATE TABLE IF NOT EXISTS paraguay_soy_reports (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
 created_by uuid NOT NULL REFERENCES users(id),
 created_at timestamptz NOT NULL DEFAULT now(),
 payload jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS paraguay_soy_reports_org_date ON paraguay_soy_reports(org_id,created_at DESC);
