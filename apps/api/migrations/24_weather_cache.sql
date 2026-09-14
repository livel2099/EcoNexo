-- Public meteorological responses only. Keys are SHA-256; no API keys or user data.
CREATE TABLE IF NOT EXISTS weather_cache (
    cache_key TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS weather_cache_expiry_idx ON weather_cache(expires_at);
ALTER TABLE weather_cache ENABLE ROW LEVEL SECURITY;
