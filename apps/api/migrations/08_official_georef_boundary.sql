-- EcoNexo Misiones - límite territorial versionado.
-- La geometría local es un fallback operativo. Antes del lanzamiento público,
-- sincronizar la geometría oficial desde GeoRef Argentina mediante
-- POST /territory/sync-georef como administrador.

BEGIN;

CREATE TABLE IF NOT EXISTS territory_boundaries (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  province text NOT NULL,
  source text NOT NULL,
  source_version text,
  source_url text,
  is_official boolean NOT NULL DEFAULT false,
  boundary geometry(MultiPolygon, 4326) NOT NULL,
  fetched_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (province, source)
);

CREATE INDEX IF NOT EXISTS idx_territory_boundaries_geom
  ON territory_boundaries USING gist(boundary);

INSERT INTO territory_boundaries (
  province, source, source_version, source_url, is_official, boundary, fetched_at
)
VALUES (
  'Misiones',
  'EcoNexo fallback operativo',
  '2026-07-27',
  'https://www.argentina.gob.ar/georef',
  false,
  ST_Multi(ST_GeomFromText(
    'POLYGON((-54.64 -25.50,-54.30 -25.58,-53.98 -25.62,-53.72 -25.78,-53.60 -26.05,-53.57 -26.30,-53.68 -26.62,-53.88 -27.02,-54.20 -27.36,-54.64 -27.62,-55.12 -27.93,-55.66 -28.18,-55.86 -27.84,-55.96 -27.37,-55.72 -27.06,-55.42 -26.70,-55.08 -26.35,-54.82 -25.98,-54.68 -25.66,-54.64 -25.50))',
    4326
  )),
  now()
)
ON CONFLICT (province, source) DO NOTHING;

CREATE OR REPLACE FUNCTION econexo_inside_misiones(point_value geography)
RETURNS boolean AS $fn$
  SELECT COALESCE(
    (
      SELECT ST_Covers(tb.boundary, point_value::geometry)
      FROM territory_boundaries tb
      WHERE tb.province='Misiones'
      ORDER BY tb.is_official DESC, tb.fetched_at DESC NULLS LAST, tb.updated_at DESC
      LIMIT 1
    ),
    false
  );
$fn$ LANGUAGE sql STABLE STRICT;

CREATE OR REPLACE VIEW misiones_boundary_status AS
SELECT
  province,
  source,
  source_version,
  source_url,
  is_official,
  fetched_at,
  updated_at,
  ST_Area(boundary::geography) / 1000000.0 AS area_km2
FROM territory_boundaries
WHERE province='Misiones'
ORDER BY is_official DESC, fetched_at DESC NULLS LAST, updated_at DESC;

COMMENT ON TABLE territory_boundaries IS
  'Límites territoriales versionados. El registro oficial debe sincronizarse desde GeoRef antes del lanzamiento público.';

COMMIT;
