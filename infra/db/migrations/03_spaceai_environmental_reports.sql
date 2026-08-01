-- EcoNexo SpaceAI: fuentes ambientales, snapshots versionados y trazabilidad.

BEGIN;

ALTER TYPE alert_type ADD VALUE IF NOT EXISTS 'calidad_aire';
ALTER TYPE alert_type ADD VALUE IF NOT EXISTS 'estres_termico';
ALTER TYPE alert_type ADD VALUE IF NOT EXISTS 'riesgo_hidrico';
ALTER TYPE alert_type ADD VALUE IF NOT EXISTS 'radiacion_uv';
ALTER TYPE alert_type ADD VALUE IF NOT EXISTS 'riesgo_vectorial';
ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'modelo';

CREATE TABLE IF NOT EXISTS environmental_source_settings (
    org_id                       UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    default_latitude             DOUBLE PRECISION NOT NULL DEFAULT -26.82 CHECK (default_latitude BETWEEN -90 AND 90),
    default_longitude            DOUBLE PRECISION NOT NULL DEFAULT -54.45 CHECK (default_longitude BETWEEN -180 AND 180),
    open_meteo_enabled           BOOLEAN NOT NULL DEFAULT true,
    air_quality_enabled          BOOLEAN NOT NULL DEFAULT true,
    flood_enabled                BOOLEAN NOT NULL DEFAULT true,
    firms_enabled                BOOLEAN NOT NULL DEFAULT true,
    refresh_minutes              INTEGER NOT NULL DEFAULT 10 CHECK (refresh_minutes BETWEEN 2 AND 180),
    fire_radius_km               DOUBLE PRECISION NOT NULL DEFAULT 50 CHECK (fire_radius_km BETWEEN 1 AND 500),
    operational_alert_min_level  TEXT NOT NULL DEFAULT 'R3' CHECK (operational_alert_min_level IN ('R0','R1','R2','R3','R4','R5')),
    auto_activate_alerts         BOOLEAN NOT NULL DEFAULT false,
    updated_by                   UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO environmental_source_settings (org_id)
SELECT id FROM organizations
ON CONFLICT (org_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS environmental_snapshots (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id               UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by           UUID REFERENCES users(id) ON DELETE SET NULL,
    methodology_version  TEXT NOT NULL,
    overall_level        TEXT NOT NULL CHECK (overall_level IN ('R0','R1','R2','R3','R4','R5')),
    overall_score        NUMERIC(5,2) NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
    location             GEOGRAPHY(Point, 4326) NOT NULL,
    origin               TEXT NOT NULL DEFAULT 'observatorio_web',
    activated_alerts     INTEGER NOT NULL DEFAULT 0 CHECK (activated_alerts >= 0),
    snapshot             JSONB NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_environmental_snapshots_org_created
    ON environmental_snapshots(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_environmental_snapshots_level
    ON environmental_snapshots(org_id, overall_level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_environmental_snapshots_geom
    ON environmental_snapshots USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_environmental_snapshots_json
    ON environmental_snapshots USING GIN(snapshot);

CREATE TABLE IF NOT EXISTS environmental_alert_links (
    snapshot_id UUID NOT NULL REFERENCES environmental_snapshots(id) ON DELETE CASCADE,
    alert_id    UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    domain      TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (snapshot_id, alert_id, domain)
);
CREATE INDEX IF NOT EXISTS idx_environmental_alert_links_alert
    ON environmental_alert_links(alert_id);

-- Extensiones documentales para partes e informes derivados de un snapshot congelado.
ALTER TABLE impact_reports ADD COLUMN IF NOT EXISTS report_kind TEXT NOT NULL DEFAULT 'desempeno_operativo';
ALTER TABLE impact_reports ADD COLUMN IF NOT EXISTS environmental_snapshot_id UUID REFERENCES environmental_snapshots(id) ON DELETE SET NULL;
ALTER TABLE impact_reports ADD COLUMN IF NOT EXISTS methodology_version TEXT;
ALTER TABLE impact_reports ADD COLUMN IF NOT EXISTS official_metadata JSONB NOT NULL DEFAULT '{}';
CREATE INDEX IF NOT EXISTS idx_impact_reports_snapshot
    ON impact_reports(environmental_snapshot_id) WHERE environmental_snapshot_id IS NOT NULL;

COMMIT;
