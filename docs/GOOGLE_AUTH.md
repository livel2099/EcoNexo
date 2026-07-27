# Google Identity Services — configuración y flujo

## Objetivo

Google Identity Services es un proveedor opcional. La home de EcoNexo permite **ingresar** o **crear una organización** por email aunque `GOOGLE_CLIENT_ID` esté vacío. Cuando Google está habilitado, el navegador recibe un ID token; la API lo verifica y emite el JWT propio de EcoNexo. La contraseña de Google nunca pasa por EcoNexo.

## Configuración

1. En Google Cloud Console, crear/seleccionar un proyecto.
2. Configurar la OAuth consent screen, nombre, dominios, enlaces de privacidad/términos y contactos.
3. Crear un OAuth Client ID de tipo **Web application**.
4. Agregar JavaScript origins exactos:
   - `http://localhost:3000`
   - `https://app.econexo.example`
5. Configurar `GOOGLE_CLIENT_ID` en `.env` y secretos/config de producción.
6. Reconstruir la web: las variables `NEXT_PUBLIC_*` se incorporan durante `next build`.

No agregar secretos de cliente al frontend: Google Identity Services para este flujo utiliza el client ID público.

## Verificación backend

`POST /auth/google` valida:

- firma del token;
- audiencia igual a `GOOGLE_CLIENT_ID`;
- emisor permitido;
- expiración;
- `email_verified=true`;
- existencia de `sub`, email y nombre.

El `sub` se guarda como identificador estable. El email se usa para comunicación y vinculación inicial, no como identificador único externo permanente.

## Registro

El payload incluye:

```json
{
  "credential": "GOOGLE_ID_TOKEN",
  "mode": "register",
  "organization_name": "Municipalidad de ejemplo",
  "vertical": "municipio",
  "terms_accepted": true,
  "legal_version": "2026-07-23"
}
```

La API crea organización y usuario en la misma transacción. El primer usuario queda como `admin`. Antes de abrir autoservicio productivo, decidir uno de estos modelos:

- dominio permitido y verificación del cargo;
- alta sujeta a aprobación de EcoNexo;
- código de invitación/contrato;
- organización en estado `pending` hasta validación.

El prototipo crea la organización en forma inmediata para facilitar la demo.

## Login

En `mode=login`, la cuenta debe existir o haber sido vinculada por email verificado. La API actualiza último acceso y emite una sesión EcoNexo.

## Pendientes productivos

- política de baja/desvinculación de Google;
- invitaciones, transferencia de ownership y recuperación de administrador;
- MFA/step-up para acciones sensibles;
- revocación de sesiones y refresh tokens rotativos;
- auditoría de login, IP, dispositivo y anomalías;
- aprobación de la pantalla de consentimiento si Google la requiere;
- pruebas con dominios organizacionales y cuentas sin imagen/nombre.
