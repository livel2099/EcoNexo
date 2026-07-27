BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE org_vertical AS ENUM ('municipio', 'forestal', 'energetica');

CREATE TABLE organizations (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          TEXT NOT NULL,
    slug          TEXT NOT NULL UNIQUE,
    vertical      org_vertical NOT NULL,
    primary_color TEXT NOT NULL DEFAULT '#2E7D5B',
    baseline_response_s INTEGER NOT NULL DEFAULT 3600,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE user_role AS ENUM ('admin', 'operador', 'visualizador');

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email         TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    role          user_role NOT NULL DEFAULT 'operador',
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_org ON users(org_id);

CREATE TABLE device_types (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    variables  JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_device_types_org ON device_types(org_id);

CREATE TYPE device_status AS ENUM ('online', 'offline', 'alerta');

CREATE TABLE devices (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id         UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    device_type_id UUID REFERENCES device_types(id) ON DELETE SET NULL,
    name           TEXT NOT NULL,
    external_id    TEXT NOT NULL,
    location       GEOGRAPHY(Point, 4326) NOT NULL,
    status         device_status NOT NULL DEFAULT 'offline',
    battery        NUMERIC(5,2),
    rssi           INTEGER,
    tags           TEXT[] NOT NULL DEFAULT '{}',
    mqtt_username  TEXT NOT NULL,
    mqtt_password_hash TEXT NOT NULL,
    last_seen      TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id, external_id)
);
CREATE INDEX idx_devices_org ON devices(org_id);
CREATE INDEX idx_devices_geom ON devices USING GIST (location);
CREATE INDEX idx_devices_tags ON devices USING GIN (tags);

CREATE TABLE readings (
    id         BIGSERIAL PRIMARY KEY,
    org_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    device_id  UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    variable   TEXT NOT NULL,
    value      DOUBLE PRECISION NOT NULL,
    ts         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_readings_device_var_ts ON readings(device_id, variable, ts DESC);
CREATE INDEX idx_readings_org_ts ON readings(org_id, ts DESC);

CREATE TYPE zone_kind AS ENUM ('incendio', 'hidrica', 'general');

CREATE TABLE risk_zones (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    kind       zone_kind NOT NULL DEFAULT 'general',
    area       GEOGRAPHY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_zones_org ON risk_zones(org_id);
CREATE INDEX idx_zones_geom ON risk_zones USING GIST (area);

CREATE TABLE citizens (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token         TEXT NOT NULL UNIQUE,
    valid_count   INTEGER NOT NULL DEFAULT 0,
    invalid_count INTEGER NOT NULL DEFAULT 0,
    reputation    NUMERIC(4,3) NOT NULL DEFAULT 0.500,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE report_status AS ENUM ('pendiente', 'verificado', 'rechazado');

CREATE TABLE citizen_reports (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    citizen_id        UUID REFERENCES citizens(id) ON DELETE SET NULL,
    type              TEXT NOT NULL,
    description       TEXT,
    photo_url         TEXT,
    location          GEOGRAPHY(Point, 4326) NOT NULL,
    status            report_status NOT NULL DEFAULT 'pendiente',
    correlation_score NUMERIC(4,3),
    reputation_score  NUMERIC(4,3),
    alert_id          UUID,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_reports_org ON citizen_reports(org_id);
CREATE INDEX idx_reports_geom ON citizen_reports USING GIST (location);
CREATE INDEX idx_reports_status ON citizen_reports(status);

CREATE TABLE satellite_detections (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id      UUID REFERENCES organizations(id) ON DELETE CASCADE,
    source      TEXT NOT NULL,
    location    GEOGRAPHY(Point, 4326) NOT NULL,
    brightness  DOUBLE PRECISION,
    confidence  NUMERIC(4,3),
    frp         DOUBLE PRECISION,
    acquired_at TIMESTAMPTZ NOT NULL,
    raw         JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_sat_geom ON satellite_detections USING GIST (location);
CREATE INDEX idx_sat_acquired ON satellite_detections(acquired_at DESC);

CREATE TYPE alert_severity AS ENUM ('baja', 'media', 'alta', 'critica');

CREATE TABLE rules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    alert_type      TEXT NOT NULL DEFAULT 'anomalia',
    conditions      JSONB NOT NULL DEFAULT '[]',
    condition_logic TEXT NOT NULL DEFAULT 'AND',
    window_seconds  INTEGER NOT NULL DEFAULT 300,
    zone_id         UUID REFERENCES risk_zones(id) ON DELETE SET NULL,
    device_tags     TEXT[] NOT NULL DEFAULT '{}',
    severity        alert_severity NOT NULL DEFAULT 'media',
    require_satellite BOOLEAN NOT NULL DEFAULT false,
    actions         JSONB NOT NULL DEFAULT '[]',
    enabled         BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_rules_org ON rules(org_id);

CREATE TYPE alert_type AS ENUM ('incendio', 'anomalia_hidrica', 'anomalia');
CREATE TYPE alert_status AS ENUM ('nueva', 'confirmada', 'descartada', 'escalada', 'asignada');

CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    type            alert_type NOT NULL,
    severity        alert_severity NOT NULL,
    status          alert_status NOT NULL DEFAULT 'nueva',
    location        GEOGRAPHY(Point, 4326) NOT NULL,
    confidence      NUMERIC(4,3) NOT NULL DEFAULT 0.500,
    title           TEXT NOT NULL,
    rule_id         UUID REFERENCES rules(id) ON DELETE SET NULL,
    device_id       UUID REFERENCES devices(id) ON DELETE SET NULL,
    assigned_to     UUID REFERENCES users(id) ON DELETE SET NULL,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_alerts_org ON alerts(org_id);
CREATE INDEX idx_alerts_geom ON alerts USING GIST (location);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_detected ON alerts(detected_at DESC);

CREATE TYPE source_type AS ENUM ('sensor', 'satelite', 'ciudadano');

CREATE TABLE alert_sources (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id    UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    source_type source_type NOT NULL,
    ref_id      UUID,
    weight      NUMERIC(4,3) NOT NULL DEFAULT 0.333,
    detail      JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_alert_sources_alert ON alert_sources(alert_id);

ALTER TABLE citizen_reports
    ADD CONSTRAINT fk_report_alert
    FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE SET NULL;

CREATE TABLE alert_events (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id   UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    user_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    action     TEXT NOT NULL,
    payload    JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_alert_events_alert ON alert_events(alert_id);

CREATE TABLE notifications (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    alert_id   UUID REFERENCES alerts(id) ON DELETE CASCADE,
    channel    TEXT NOT NULL DEFAULT 'in_app',
    title      TEXT NOT NULL,
    body       TEXT,
    read       BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_org ON notifications(org_id, created_at DESC);

-- Correlacion espacial: nodos dentro de un radio (metros) de un punto.
-- ST_DWithin sobre GEOGRAPHY usa metros. Usada por el pipeline de alertas.
CREATE OR REPLACE FUNCTION nearby_devices(
    p_org_id UUID, p_lat DOUBLE PRECISION, p_lon DOUBLE PRECISION, p_radius_m DOUBLE PRECISION
) RETURNS TABLE (device_id UUID, distance_m DOUBLE PRECISION) AS $fn$
    SELECT d.id,
           ST_Distance(d.location, ST_MakePoint(p_lon, p_lat)::geography) AS distance_m
    FROM devices d
    WHERE d.org_id = p_org_id
      AND ST_DWithin(d.location, ST_MakePoint(p_lon, p_lat)::geography, p_radius_m)
    ORDER BY distance_m ASC;
$fn$ LANGUAGE sql STABLE;

COMMIT;
