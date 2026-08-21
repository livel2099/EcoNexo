-- Auditoria de acciones de administracion general.
--
-- audit_events tenia el FK compuesto (org_id, user_id) -> users(org_id, id),
-- que exige que el actor pertenezca a la organizacion auditada. Administracion
-- general es cruzada por definicion: aprueba, suspende y renombra
-- organizaciones que no son la suya. Cada una de esas acciones violaba el
-- constraint y terminaba en 500, despues de haber aplicado el UPDATE.
--
-- Se reemplaza por un FK simple sobre el actor. Se conserva la integridad
-- referencial del usuario; lo que se abandona es la exigencia de que actor y
-- organizacion coincidan, que la consola de plataforma no puede cumplir.

BEGIN;

ALTER TABLE audit_events
    DROP CONSTRAINT IF EXISTS fk_audit_events_org_user;

-- El constraint anterior era NOT VALID, asi que las filas previas a su creacion
-- nunca se verificaron y pueden apuntar a usuarios que ya no existen. El nuevo
-- FK se valida al crearse, de modo que primero hay que dejar en NULL a esos
-- actores huerfanos o la migracion falla sobre una base con historial real.
UPDATE audit_events SET user_id = NULL
WHERE user_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM users WHERE users.id = audit_events.user_id);

DO $block$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.audit_events'::regclass
          AND conname = 'fk_audit_events_user'
    ) THEN
        ALTER TABLE audit_events
            ADD CONSTRAINT fk_audit_events_user
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END;
$block$;

CREATE INDEX IF NOT EXISTS idx_audit_events_user
    ON audit_events (user_id, created_at DESC);

COMMIT;
