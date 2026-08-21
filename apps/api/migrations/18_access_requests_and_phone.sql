-- Alta con aprobacion manual: telefono de contacto y estado de acceso.
--
-- Hasta ahora POST /auth/register creaba la organizacion activa y devolvia
-- sesion en el acto, asi que cualquiera con un correo entraba a la plataforma.
-- Las altas institucionales pasan a quedar pendientes hasta que administracion
-- general las habilite, despues de cobrar la licencia.
--
-- Las organizaciones existentes quedan en 'approved' para no cortarles el
-- acceso. Las cuentas comunitarias de EcoNexoFoI siguen siendo gratuitas e
-- inmediatas: no pasan por esta puerta.

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS phone TEXT;

COMMENT ON COLUMN users.phone IS
  'Telefono de contacto en formato internacional. Lo usa administracion general para contactar por WhatsApp al aprobar el alta.';

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS access_status TEXT NOT NULL DEFAULT 'approved';

DO $block$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'organizations_access_status_check'
    ) THEN
        ALTER TABLE organizations ADD CONSTRAINT organizations_access_status_check
            CHECK (access_status IN ('pending', 'approved', 'suspended'));
    END IF;
END;
$block$;

COMMENT ON COLUMN organizations.access_status IS
  'pending = alta esperando aprobacion; approved = habilitada; suspended = dada de baja. is_active sigue siendo la puerta efectiva del login.';

-- Coherencia con las filas que ya existian: lo que estaba desactivado no era
-- una solicitud nueva sino una suspension.
UPDATE organizations SET access_status = 'suspended'
WHERE NOT is_active AND access_status = 'approved';

-- Los informes dejan de tener tope mensual. Se limpia el entitlement de las
-- filas ya guardadas para que la consola no muestre un limite que nadie aplica.
UPDATE subscription_plans
SET entitlements = entitlements - 'max_reports_per_month', updated_at = now()
WHERE entitlements ? 'max_reports_per_month';

UPDATE organization_subscriptions
SET custom_entitlements = custom_entitlements - 'max_reports_per_month'
WHERE custom_entitlements ? 'max_reports_per_month';

CREATE INDEX IF NOT EXISTS idx_organizations_access_status
    ON organizations (access_status, created_at DESC);

COMMIT;
