# Suscripciones, límites y mensajes administrativos

## Objetivo

EcoNexo incorpora control comercial por organización y una bandeja administrativa de accesos. Cada inicio de sesión correcto registra un mensaje visible en **Admin Core > Mensajes**, con usuario, proveedor de identidad, fecha, agente de usuario, origen e IP parcialmente anonimizada. La notificación no reemplaza una solución SIEM ni expone la dirección IP completa.

## Planes comerciales

Los precios se trasladan del plan de negocios entregado. Los límites numéricos de usuarios, dispositivos, geocercas, reglas, informes y capas son una parametrización operativa inicial y pueden modificarse por contrato desde `custom_entitlements`.

| Plan | Precio de referencia | Vigencia/base comercial | Alcance principal |
|---|---:|---|---|
| Sandbox calificado | Sin cargo | 14 días | Evaluación limitada; no es una prueba abierta irrestricta. |
| Diagnóstico territorial | USD 2.000-4.000 | 30 días | Mapa base, lectura de riesgo y propuesta de piloto. |
| Piloto 8 semanas | USD 18.000-35.000 | 56 días | Dashboard, 3 capas críticas, validación, reportes y capacitación. |
| SaaS Municipal | USD 800-1.500/mes | Recurrente | 1 municipio, alertas base, reportes mensuales y soporte limitado. |
| SaaS Provincia / Pro | USD 3.500-8.000/mes | Recurrente | Múltiples zonas, reportes quincenales, usuarios internos y playbook. |
| Enterprise minero/energético | USD 12.000+/mes | Recurrente | SLA, API, integraciones, auditoría, modelos y evidencia personalizada. |
| Academia EcoNexo | USD 2.000-6.000/cohorte | 45 días iniciales | Capacitación, manuales, certificación interna y simulacros. |

## Límites operativos predeterminados

Los límites se guardan en `subscription_plans.entitlements`. No están codificados como una afirmación contractual inmutable: el administrador comercial puede ampliarlos por organización. Al alcanzar un límite, la API responde `402 Payment Required` con una explicación y no crea el recurso.

Se controlan:

- usuarios activos;
- dispositivos;
- geocercas;
- reglas;
- informes creados en el mes;
- cantidad de capas críticas y municipios informados en el panel;
- acceso a API, exportación de auditoría, SLA y modelos personalizados;
- módulos `core`, `fire_smoke` y `forestry_pests`.

## Flujo de licencia

1. Una organización nueva recibe **Sandbox calificado** por 14 días.
2. El administrador abre **Admin Core > Suscripción** y selecciona un plan.
3. La solicitud llega a la bandeja global de los emails configurados en `PLATFORM_ADMIN_EMAILS`.
4. El administrador comercial revisa alcance y contrato, y activa el plan.
5. La organización recibe un mensaje interno con el nuevo estado y se sincronizan los módulos habilitados.
6. Las organizaciones existentes al aplicar la migración 11 reciben transitoriamente `pilot_8_weeks` durante 56 días para evitar un bloqueo inmediato. Esto debe revisarse antes del lanzamiento.

No se incluye cobro automático. La activación es manual y está pensada para acompañar diagnóstico pago, piloto contratado y SaaS negociado. Un gateway de pago requerirá facturación, impuestos, medios de pago, conciliación, reintentos y tratamiento de mora.

## Administrador comercial de plataforma

Configurar en `.env`:

```env
PLATFORM_ADMIN_EMAILS=miguel@livel.pro,comercial@econexo.com.ar
SALES_EMAIL=comercial@econexo.com.ar
```

Los emails deben corresponder a usuarios EcoNexo activos. Quienes estén en esa lista pueden ver solicitudes de todas las organizaciones y aprobar licencias desde **Admin Core > Suscripción**.

## Mensajes de login

Los eventos exitosos de acceso por contraseña o Google generan `admin_notifications`. Cada administrador mantiene su propio estado de lectura en `admin_notification_reads`. La bandeja y el contador consultan novedades cada 30 segundos. La IP se almacena enmascarada, por ejemplo `192.168.1.x`.

## Migración

Sobre una base que ya tiene las migraciones 01-10:

```powershell
docker compose exec -T postgis psql `
  -U econexo `
  -d econexo `
  -v ON_ERROR_STOP=1 `
  -f /docker-entrypoint-initdb.d/11_subscriptions_and_admin_login_notifications.sql

docker compose up -d --build --force-recreate api web
```

Verificar en Swagger:

- `GET /subscriptions/plans`
- `GET /subscriptions/me`
- `POST /subscriptions/request-change`
- `GET /admin/notifications`
- `GET /admin/notifications/unread-count`

## Tablas nuevas

- `subscription_plans`
- `organization_subscriptions`
- `subscription_events`
- `license_requests`
- `admin_notifications`
- `admin_notification_reads`
