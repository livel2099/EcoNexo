-- Activacion de modulos desde administracion general.
--
-- Mismo choque de diseno que resolvio la migracion 19 para audit_events.
-- organization_modules tenia el FK compuesto (org_id, created_by) contra
-- users(org_id, id), que exige que quien crea la fila pertenezca a la
-- organizacion. Administracion general es cruzada por definicion: al aprobar
-- una licencia, sync_modules escribe las filas de modulos de OTRA organizacion
-- firmando con el usuario administrador. El resultado era un 500 al pulsar
-- "Aprobar y activar", despues de haber actualizado la suscripcion.
--
-- Se conserva la integridad referencial del actor y se abandona la exigencia
-- de que actor y organizacion coincidan, que la consola no puede cumplir.
--
-- Los otros cuatro FK compuestos de la migracion 11 (impact_reports,
-- environmental_snapshots, environmental_source_settings y alert_shares) se
-- dejan como estan: esos registros los crea siempre un usuario de la propia
-- organizacion, y ahi la restriccion expresa una invariante real.

BEGIN;

ALTER TABLE organization_modules
    DROP CONSTRAINT IF EXISTS fk_organization_modules_org_user;

-- El constraint anterior era NOT VALID: las filas previas nunca se
-- verificaron y pueden apuntar a usuarios que ya no existen.
UPDATE organization_modules SET created_by = NULL
WHERE created_by IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM users WHERE users.id = organization_modules.created_by);

DO $block$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.organization_modules'::regclass
          AND conname = 'fk_organization_modules_creator'
    ) THEN
        ALTER TABLE organization_modules
            ADD CONSTRAINT fk_organization_modules_creator
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END;
$block$;

COMMIT;
