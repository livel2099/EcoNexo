-- Reparacion de deriva de esquema (schema drift).
--
-- Un `python -m app.migrate --baseline-existing` sobre una base que todavia no
-- tenia todas las migraciones marca los archivos como aplicados sin ejecutarlos.
-- El resultado es un esquema mas viejo que el codigo: `POST /auth/login`
-- respondia 500 porque faltaba `users.account_type` y las tablas `foi_*`.
--
-- Esta migracion vuelve a declarar, de forma idempotente, todo lo que el codigo
-- actual necesita. Es segura de correr sobre una base ya completa: no altera
-- datos existentes ni recrea objetos que ya existen.

BEGIN;

-- Columnas que el flujo de autenticacion consulta (migraciones 02, 04, 12, 13).
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS auth_provider TEXT NOT NULL DEFAULT 'password',
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS avatar_url TEXT,
    ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS legal_version TEXT,
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

-- DDL de la migracion 15, que fue editada despues de aplicarse. Segun cuando
-- corrio cada entorno puede faltarle el DEFAULT o el CHECK, asi que se
-- redeclaran los dos. Se omiten a proposito los UPDATE de la 15: reactivarian
-- copernicus_enabled y cerrarian pipeline_runs en curso, pisando datos reales.
ALTER TABLE environmental_source_settings
  ALTER COLUMN copernicus_enabled SET DEFAULT true;

ALTER TABLE environmental_source_settings
  DROP CONSTRAINT IF EXISTS environment_sources_copernicus_config_check;

ALTER TABLE environmental_source_settings
  ADD CONSTRAINT environment_sources_copernicus_config_check
  CHECK (
    NOT copernicus_enabled
    OR copernicus_use_system_default
    OR NULLIF(btrim(copernicus_wms_url), '') IS NOT NULL
  ) NOT VALID;

-- Red EcoNexoFoI (migracion 16), re-declarada de forma idempotente.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS account_type TEXT NOT NULL DEFAULT 'institutional';

DO $block$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_account_type_check') THEN
        ALTER TABLE users ADD CONSTRAINT users_account_type_check
            CHECK (account_type IN ('institutional', 'community'));
    END IF;
END;
$block$;

CREATE INDEX IF NOT EXISTS idx_users_account_type_active
    ON users (account_type, is_active, created_at DESC);

INSERT INTO organizations (name, slug, vertical, primary_color, baseline_response_s)
VALUES ('EcoNexoFoI · Comunidad abierta', 'econexofoi-community', 'forestal', '#059669', 3600)
ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, primary_color = EXCLUDED.primary_color;

CREATE TABLE IF NOT EXISTS foi_profiles (
    user_id       UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    headline      TEXT NOT NULL DEFAULT 'Investigador/a independiente',
    institution   TEXT,
    discipline    TEXT,
    bio           TEXT,
    location      TEXT,
    website       TEXT,
    orcid         TEXT,
    interests     TEXT[] NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT foi_profiles_orcid_check CHECK (orcid IS NULL OR orcid ~ '^([0-9]{4}-){3}[0-9X]{4}$')
);

CREATE TABLE IF NOT EXISTS foi_attachments (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename      TEXT NOT NULL,
    content_type  TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 15728640),
    data          BYTEA NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_foi_attachments_owner
    ON foi_attachments (owner_id, created_at DESC);

CREATE TABLE IF NOT EXISTS foi_communities (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    description   TEXT NOT NULL,
    icon          TEXT NOT NULL DEFAULT '◌',
    color         TEXT NOT NULL DEFAULT '#059669',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS foi_community_members (
    community_id  UUID NOT NULL REFERENCES foi_communities(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (community_id, user_id)
);

CREATE TABLE IF NOT EXISTS foi_posts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    author_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    community_id    UUID REFERENCES foi_communities(id) ON DELETE SET NULL,
    kind            TEXT NOT NULL,
    title           TEXT NOT NULL,
    abstract        TEXT NOT NULL,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    attachment_url  TEXT,
    attachment_name TEXT,
    attachment_mime TEXT,
    status          TEXT NOT NULL DEFAULT 'published',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT foi_posts_kind_check CHECK (kind IN ('research', 'question', 'proposal')),
    CONSTRAINT foi_posts_status_check CHECK (status IN ('published', 'archived')),
    CONSTRAINT foi_posts_title_length CHECK (char_length(title) BETWEEN 8 AND 220),
    CONSTRAINT foi_posts_abstract_length CHECK (char_length(abstract) BETWEEN 20 AND 10000)
);

CREATE INDEX IF NOT EXISTS idx_foi_posts_created
    ON foi_posts (created_at DESC) WHERE status = 'published';
CREATE INDEX IF NOT EXISTS idx_foi_posts_author
    ON foi_posts (author_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_foi_posts_community
    ON foi_posts (community_id, created_at DESC) WHERE status = 'published';
CREATE INDEX IF NOT EXISTS idx_foi_posts_tags
    ON foi_posts USING GIN (tags);

CREATE TABLE IF NOT EXISTS foi_comments (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id     UUID NOT NULL REFERENCES foi_posts(id) ON DELETE CASCADE,
    author_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT foi_comments_body_length CHECK (char_length(body) BETWEEN 2 AND 4000)
);
CREATE INDEX IF NOT EXISTS idx_foi_comments_post
    ON foi_comments (post_id, created_at ASC);

CREATE TABLE IF NOT EXISTS foi_post_reactions (
    post_id     UUID NOT NULL REFERENCES foi_posts(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL DEFAULT 'like' CHECK (kind = 'like'),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (post_id, user_id, kind)
);

CREATE TABLE IF NOT EXISTS foi_saved_posts (
    post_id     UUID NOT NULL REFERENCES foi_posts(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (post_id, user_id)
);

CREATE TABLE IF NOT EXISTS foi_follows (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followed_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, followed_id),
    CONSTRAINT foi_follows_not_self CHECK (follower_id <> followed_id)
);

INSERT INTO foi_communities (slug, name, description, icon, color) VALUES
    ('agroecologia', 'Agroecología', 'Producción regenerativa, suelos y biodiversidad aplicada.', '🌱', '#059669'),
    ('ciencia-de-datos', 'Ciencia de datos', 'Métodos abiertos, IA responsable y reproducibilidad.', '◌', '#22D3EE'),
    ('transicion-energetica', 'Transición energética', 'Energía limpia, eficiencia y territorio.', '☀', '#F4B942'),
    ('salud-ambiental', 'Salud ambiental', 'Ambiente, epidemiología y bienestar comunitario.', '✚', '#A78BFA')
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color;

DO $block$
DECLARE
    table_name TEXT;
    trigger_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['foi_profiles','foi_communities','foi_posts','foi_comments'] LOOP
        trigger_name := 'trg_' || table_name || '_updated_at';
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = trigger_name AND NOT tgisinternal) THEN
            EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION econexo_set_updated_at()', trigger_name, table_name);
        END IF;
    END LOOP;
END;
$block$;

COMMIT;
