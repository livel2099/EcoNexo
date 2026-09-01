-- Limite de intentos compartido entre replicas.
--
-- El limitador vivia en memoria del proceso. Con `replicas: 2` en k8s/10-api.yaml
-- (y con cualquier escalado horizontal en Render) el limite efectivo se
-- multiplica por la cantidad de instancias: 10 intentos de login por ventana se
-- vuelven 20, y el atacante ni siquiera necesita elegir replica porque el
-- balanceador lo reparte solo.
--
-- Se usa Postgres en vez de sumar Redis: la conexion ya existe, el volumen es
-- de endpoints publicos de auth (bajo) y evita un componente de infraestructura
-- nuevo para un control que hoy no tiene ninguno.
--
-- Una fila por intento, no un contador por ventana: conserva la semantica de
-- ventana deslizante que ya tenia el limitador en memoria y permite calcular
-- Retry-After a partir del intento mas viejo que sigue vigente.

BEGIN;

CREATE TABLE IF NOT EXISTS rate_limit_hits (
    id BIGSERIAL PRIMARY KEY,
    bucket_key TEXT NOT NULL,
    hit_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- La consulta siempre filtra por clave y ventana temporal.
CREATE INDEX IF NOT EXISTS idx_rate_limit_hits_key_time
    ON rate_limit_hits (bucket_key, hit_at DESC);

-- Para la purga global periodica de claves que no volvieron a aparecer.
CREATE INDEX IF NOT EXISTS idx_rate_limit_hits_time
    ON rate_limit_hits (hit_at);

COMMIT;
