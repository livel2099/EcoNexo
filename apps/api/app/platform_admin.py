"""Bootstrap seguro del administrador general de EcoNexo.

La contraseña temporal vive exclusivamente en variables de entorno. Nunca se
incluye en respuestas, logs ni archivos del frontend. Solo se usa al crear la
cuenta o para tomar una cuenta previa que todavía no registró un cambio seguro.
"""
from __future__ import annotations

import logging

from . import db
from .config import get_settings
from .security import hash_secret
from .subscriptions import ensure_subscription, seed_plan_catalog, sync_modules

log = logging.getLogger("econexo.platform_admin")


async def ensure_platform_admin() -> None:
    settings = get_settings()
    if not settings.platform_admin_bootstrap_enabled:
        return
    if not settings.platform_admin_list:
        raise RuntimeError("PLATFORM_ADMIN_EMAILS no contiene un correo válido")

    email = settings.platform_admin_list[0]
    password = settings.platform_admin_initial_password
    created = False
    reset_existing = False
    pool = db.pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            user = await conn.fetchrow(
                """
                SELECT id, org_id, must_change_password, password_changed_at
                FROM users WHERE lower(email)=lower($1)
                """,
                email,
            )

            if user is None:
                org_id = await conn.fetchval(
                    """
                    INSERT INTO organizations (
                        name, slug, vertical, province, department, municipality,
                        territory_scope, is_active
                    ) VALUES ($1,'econexo-plataforma','municipio','Misiones','Capital',
                              'Posadas','provincial',true)
                    ON CONFLICT (slug) DO UPDATE SET
                        name=EXCLUDED.name, is_active=true,
                        access_status='approved', updated_at=now()
                    RETURNING id
                    """,
                    settings.platform_admin_organization.strip() or "EcoNexo Plataforma",
                )
                user = await conn.fetchrow(
                    """
                    INSERT INTO users (
                        org_id, email, name, role, password_hash, auth_provider,
                        email_verified, terms_accepted_at, legal_version,
                        must_change_password, password_changed_at
                    ) VALUES (
                        $1,$2,$3,'admin',$4,'password',true,now(),'platform-admin-rc.5',
                        $5,NULL
                    )
                    RETURNING id, org_id, must_change_password, password_changed_at
                    """,
                    org_id,
                    email,
                    settings.platform_admin_name.strip() or "Administrador General EcoNexo",
                    hash_secret(password),
                    settings.platform_admin_force_password_change,
                )
                created = True
            else:
                reset_existing = bool(
                    settings.platform_admin_reset_initial_password
                    and user["password_changed_at"] is None
                )
                if reset_existing:
                    await conn.execute(
                        """
                        UPDATE users SET role='admin', is_active=true,
                            name=COALESCE(NULLIF(name,''),$2), password_hash=$3,
                            auth_provider='password', must_change_password=$4,
                            password_changed_at=NULL, updated_at=now()
                        WHERE id=$1
                        """,
                        user["id"],
                        settings.platform_admin_name.strip() or "Administrador General EcoNexo",
                        hash_secret(password),
                        settings.platform_admin_force_password_change,
                    )
                else:
                    await conn.execute(
                        """
                        UPDATE users SET role='admin', is_active=true,
                            name=COALESCE(NULLIF(name,''),$2), updated_at=now()
                        WHERE id=$1
                        """,
                        user["id"],
                        settings.platform_admin_name.strip() or "Administrador General EcoNexo",
                    )
                await conn.execute(
                    "UPDATE organizations SET is_active=true, updated_at=now() WHERE id=$1",
                    user["org_id"],
                )

            await seed_plan_catalog(conn)
            await ensure_subscription(
                user["org_id"], user["id"], plan_key="enterprise", conn=conn
            )
            await conn.execute(
                """
                UPDATE organization_subscriptions SET
                    plan_key='enterprise', status='active', expires_at=NULL,
                    auto_renew=false, activation_source='platform_bootstrap',
                    activated_by=$2, updated_at=now()
                WHERE org_id=$1
                """,
                user["org_id"],
                user["id"],
            )
            action = (
                "bootstrap_create" if created
                else "bootstrap_reset" if reset_existing
                else "bootstrap_verify"
            )
            await conn.execute(
                """
                INSERT INTO audit_events (org_id,user_id,action,resource,resource_id,metadata)
                VALUES ($1,$2,$3,'platform_admin',$2,
                        jsonb_build_object('email',$4,'bootstrap',true))
                """,
                user["org_id"],
                user["id"],
                action,
                email,
            )

    await sync_modules(user["org_id"], user["id"])
    state = "creado" if created else "restablecido" if reset_existing else "verificado"
    log.info("Administrador general %s: %s", state, email)
