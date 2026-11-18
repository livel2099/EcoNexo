-- Portfolio, field evidence and durable delivery queue for Mato Grosso.
CREATE TABLE IF NOT EXISTS brazil_operations_settings (
 org_id uuid PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
 target_area_ha numeric NOT NULL DEFAULT 450000 CHECK(target_area_ha > 0),
 enabled boolean NOT NULL DEFAULT false,
 fire_buffer_m integer NOT NULL DEFAULT 5000 CHECK(fire_buffer_m BETWEEN 0 AND 20000),
 recipients jsonb NOT NULL DEFAULT '[]',
 last_scan_at timestamptz,
 last_scan_status text NOT NULL DEFAULT 'pending',
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS brazil_parcels (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
 code text NOT NULL,
 estate text NOT NULL,
 name text NOT NULL,
 crop text NOT NULL CHECK(crop IN ('orange','eucalyptus','soy','reserve')),
 cultivar text NOT NULL DEFAULT '',
 planted_on date,
 manager text NOT NULL DEFAULT '',
 geom geometry(MultiPolygon,4326) NOT NULL,
 area_ha double precision NOT NULL CHECK(area_ha > 0),
 context jsonb,
 context_at timestamptz,
 satellite jsonb,
 satellite_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(org_id,code), UNIQUE(org_id,id)
);
CREATE INDEX IF NOT EXISTS brazil_parcels_scope ON brazil_parcels(org_id,crop,estate,id);
CREATE INDEX IF NOT EXISTS brazil_parcels_geography ON brazil_parcels USING gist((geom::geography));
CREATE INDEX IF NOT EXISTS brazil_parcels_geometry ON brazil_parcels USING gist(geom);
CREATE TABLE IF NOT EXISTS brazil_soil_readings (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 org_id uuid NOT NULL,
 parcel_id uuid NOT NULL,
 observed_at timestamptz NOT NULL,
 source text NOT NULL CHECK(source IN ('sensor','laboratory')),
 reference text NOT NULL,
 depth_cm integer NOT NULL CHECK(depth_cm BETWEEN 0 AND 200),
 ph double precision CHECK(ph BETWEEN 0 AND 14),
 ph_method text NOT NULL CHECK(ph_method IN ('H2O','CaCl2','KCl','electrode')),
 temperature_c double precision CHECK(temperature_c BETWEEN -20 AND 80),
 calibrated_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(org_id,parcel_id) REFERENCES brazil_parcels(org_id,id) ON DELETE CASCADE,
 UNIQUE(org_id,parcel_id,source,reference,observed_at),
 CHECK(ph IS NOT NULL OR temperature_c IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS brazil_soil_latest ON brazil_soil_readings(org_id,parcel_id,observed_at DESC);
CREATE TABLE IF NOT EXISTS brazil_inspections (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 org_id uuid NOT NULL,
 parcel_id uuid NOT NULL,
 created_by uuid REFERENCES users(id),
 observed_at timestamptz NOT NULL,
 payload jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(org_id,parcel_id) REFERENCES brazil_parcels(org_id,id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS brazil_inspections_scope ON brazil_inspections(org_id,parcel_id,observed_at DESC);
CREATE TABLE IF NOT EXISTS brazil_operations_alerts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 org_id uuid NOT NULL,
 parcel_id uuid NOT NULL,
 event_key text NOT NULL,
 kind text NOT NULL CHECK(kind IN ('fire','pest','vegetation')),
 priority text NOT NULL CHECK(priority IN ('critical','high','medium')),
 status text NOT NULL DEFAULT 'open' CHECK(status IN ('open','acknowledged','resolved','dismissed')),
 observed_at timestamptz NOT NULL,
 evidence jsonb NOT NULL,
 assigned_to text NOT NULL DEFAULT '',
 resolution text NOT NULL DEFAULT '',
 updated_by uuid REFERENCES users(id),
 updated_at timestamptz NOT NULL DEFAULT now(),
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(org_id,parcel_id) REFERENCES brazil_parcels(org_id,id) ON DELETE CASCADE,
 UNIQUE(org_id,parcel_id,event_key), UNIQUE(org_id,id)
);
CREATE INDEX IF NOT EXISTS brazil_ops_alerts_queue ON brazil_operations_alerts(org_id,status,priority,created_at DESC);
CREATE TABLE IF NOT EXISTS brazil_alert_actions (
 id bigserial PRIMARY KEY,
 org_id uuid NOT NULL,
 alert_id uuid NOT NULL,
 actor_id uuid NOT NULL REFERENCES users(id),
 payload jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(org_id,alert_id) REFERENCES brazil_operations_alerts(org_id,id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS brazil_delivery_queue (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 org_id uuid NOT NULL,
 alert_id uuid NOT NULL,
 channel text NOT NULL CHECK(channel IN ('email','whatsapp')),
 recipient text NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','accepted','failed','uncertain','cancelled')),
 attempts integer NOT NULL DEFAULT 0,
 available_at timestamptz NOT NULL DEFAULT now(),
 claimed_at timestamptz,
 provider_id text,
 last_error text,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(org_id,alert_id) REFERENCES brazil_operations_alerts(org_id,id) ON DELETE CASCADE,
 UNIQUE(alert_id,channel,recipient)
);
CREATE INDEX IF NOT EXISTS brazil_delivery_due ON brazil_delivery_queue(status,available_at);
