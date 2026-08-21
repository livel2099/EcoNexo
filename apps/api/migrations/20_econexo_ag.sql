-- EcoNexo AG: modulo agro.
--
-- Un lote es la unidad de decision: un poligono de campo con un cultivo y una
-- fecha de siembra. Sobre cada lote se guarda una serie diaria de indicadores
-- agronomicos derivados de datos meteorologicos reales (Open-Meteo: reanalisis
-- ERA5 para el historico, pronostico para los proximos dias) y las
-- recomendaciones que salen de esa serie.
--
-- La serie se guarda calculada y no solo cruda a proposito: el valor que vio
-- el productor el dia que decidio regar o pulverizar tiene que quedar
-- reproducible, aunque despues cambien los coeficientes del catalogo.

BEGIN;

CREATE TABLE IF NOT EXISTS agro_lots (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    crop_key      TEXT NOT NULL,
    sowing_date   DATE,
    area_ha       NUMERIC(10,2) NOT NULL DEFAULT 1 CHECK (area_ha > 0 AND area_ha <= 100000),
    location      GEOGRAPHY(POINT, 4326) NOT NULL,
    zone_id       UUID REFERENCES risk_zones(id) ON DELETE SET NULL,
    notes         TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    last_refresh_at     TIMESTAMPTZ,
    last_refresh_status TEXT,
    created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT agro_lots_name_length CHECK (char_length(name) BETWEEN 2 AND 120),
    CONSTRAINT agro_lots_org_name_unique UNIQUE (org_id, name)
);

CREATE INDEX IF NOT EXISTS idx_agro_lots_org
    ON agro_lots (org_id, is_active, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agro_lots_location
    ON agro_lots USING GIST (location);

-- Serie diaria ya procesada. La clave natural es (lote, dia): recalcular un
-- dia lo pisa, no lo duplica.
CREATE TABLE IF NOT EXISTS agro_lot_daily (
    lot_id            UUID NOT NULL REFERENCES agro_lots(id) ON DELETE CASCADE,
    org_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    day               DATE NOT NULL,
    tmax_c            DOUBLE PRECISION,
    tmin_c            DOUBLE PRECISION,
    precipitation_mm  DOUBLE PRECISION,
    et0_mm            DOUBLE PRECISION,
    kc                DOUBLE PRECISION,
    etc_mm            DOUBLE PRECISION,
    gdd               DOUBLE PRECISION,
    gdd_accum         DOUBLE PRECISION,
    balance_mm        DOUBLE PRECISION,
    balance_accum_mm  DOUBLE PRECISION,
    stage_key         TEXT,
    stage_name        TEXT,
    source            TEXT NOT NULL DEFAULT 'open-meteo',
    is_forecast       BOOLEAN NOT NULL DEFAULT false,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (lot_id, day)
);

CREATE INDEX IF NOT EXISTS idx_agro_lot_daily_org_day
    ON agro_lot_daily (org_id, day DESC);

-- Recomendaciones derivadas de la serie. payload guarda los numeros que las
-- justifican, para que la recomendacion sea auditable y no un veredicto.
CREATE TABLE IF NOT EXISTS agro_advisories (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    lot_id      UUID NOT NULL REFERENCES agro_lots(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    level       TEXT NOT NULL,
    title       TEXT NOT NULL,
    detail      TEXT NOT NULL,
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    valid_from  TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to    TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT agro_advisories_kind_check
        CHECK (kind IN ('helada','riego','pulverizacion','enfermedad','estres_termico','fenologia')),
    CONSTRAINT agro_advisories_level_check
        CHECK (level IN ('bajo','medio','alto'))
);

CREATE INDEX IF NOT EXISTS idx_agro_advisories_lot
    ON agro_advisories (lot_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agro_advisories_org_level
    ON agro_advisories (org_id, level, created_at DESC);

DO $block$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger
                   WHERE tgname = 'trg_agro_lots_updated_at' AND NOT tgisinternal) THEN
        CREATE TRIGGER trg_agro_lots_updated_at BEFORE UPDATE ON agro_lots
            FOR EACH ROW EXECUTE FUNCTION econexo_set_updated_at();
    END IF;
END;
$block$;

-- El modulo agro se suma al catalogo de modulos licenciables.
ALTER TABLE organization_modules
    DROP CONSTRAINT IF EXISTS ck_organization_modules_key;
ALTER TABLE organization_modules
    ADD CONSTRAINT ck_organization_modules_key
    CHECK (module_key IN ('core','fire_smoke','forestry_pests','agro'));

ALTER TABLE alert_shares
    DROP CONSTRAINT IF EXISTS ck_alert_shares_module;
ALTER TABLE alert_shares
    ADD CONSTRAINT ck_alert_shares_module
    CHECK (module_key IN ('core','fire_smoke','forestry_pests','agro'));

INSERT INTO organization_modules (org_id, module_key, status, plan_name, config)
SELECT id, 'agro', 'suspended', 'EcoNexo AG · inteligencia agronómica', '{}'::jsonb
FROM organizations
ON CONFLICT (org_id, module_key) DO NOTHING;

COMMIT;
