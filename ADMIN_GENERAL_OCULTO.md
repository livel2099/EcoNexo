# EcoNexo — Administrador general oculto

Versión: `1.0.0-rc.5-render`

## Alcance

La ruta privada es:

```text
https://TU-FRONTEND/plataforma
```

No se publica en el menú, el sitemap ni Swagger. La seguridad no depende de que la URL sea difícil de adivinar: todos los endpoints `/platform/*` requieren JWT válido, rol `admin`, organización activa y correo incluido en `PLATFORM_ADMIN_EMAILS`.

Funciones incluidas:

- resumen global de organizaciones y usuarios;
- búsqueda global de usuarios;
- cambio de rol y activación/baja lógica;
- restablecimiento de contraseña temporal con cambio obligatorio;
- activación y suspensión de organizaciones;
- consola de licencias existente;
- auditoría global;
- creación automática y segura del administrador inicial.

## Variables de Render — API

Agregar en `EcoNexo API > Environment`:

```env
PLATFORM_ADMIN_EMAILS=econexoargentina@gmail.com
PLATFORM_ADMIN_BOOTSTRAP_ENABLED=true
PLATFORM_ADMIN_INITIAL_PASSWORD=REEMPLAZAR_CONTRASENA_TEMPORAL_SEGURA
PLATFORM_ADMIN_FORCE_PASSWORD_CHANGE=true
PLATFORM_ADMIN_RESET_INITIAL_PASSWORD=true
PLATFORM_ADMIN_NAME=Administrador General EcoNexo
PLATFORM_ADMIN_ORGANIZATION=EcoNexo Plataforma
```

La contraseña temporal debe tener al menos 12 caracteres, una letra y un número. No debe llevar el prefijo `NEXT_PUBLIC_`.

Generación recomendada en PowerShell:

```powershell
python -c "import secrets; print('EcoNexo-' + secrets.token_urlsafe(24) + '-9')"
```

`PLATFORM_ADMIN_RESET_INITIAL_PASSWORD=true` permite tomar una cuenta existente cuyo campo `password_changed_at` todavía sea nulo. Después del primer cambio de contraseña, los reinicios no vuelven a sobrescribirla.

## Primer ingreso

1. Desplegar API con migraciones habilitadas.
2. Desplegar nuevamente el frontend.
3. Ingresar con:

```text
Correo: econexoargentina@gmail.com
Contraseña: valor de PLATFORM_ADMIN_INITIAL_PASSWORD
```

4. EcoNexo redirige a `/cambiar-contrasena`.
5. Crear una contraseña privada de al menos 12 caracteres.
6. El sistema redirige a `/plataforma`.
7. Después de verificar el acceso, cambiar en Render:

```env
PLATFORM_ADMIN_BOOTSTRAP_ENABLED=false
PLATFORM_ADMIN_INITIAL_PASSWORD=
PLATFORM_ADMIN_RESET_INITIAL_PASSWORD=false
```

La autorización general seguirá funcionando por `PLATFORM_ADMIN_EMAILS`; estas tres variables solo controlan la creación o toma inicial de la cuenta.

## Migración

Se agregan:

```text
12_platform_admin_console.sql
13_platform_admin_organization_status.sql
```

Columnas nuevas:

- `organizations.is_active`;
- `users.must_change_password`;
- `users.password_changed_at`.

En Render Free, mantener:

```env
RUN_MIGRATIONS_ON_START=true
```

En planes con Pre-Deploy:

```text
python -m app.migrate
```

## Variables del frontend

En `econexo-web > Environment`:

```env
NEXT_PUBLIC_API_URL=https://econexo.onrender.com
NEXT_PUBLIC_WS_URL=wss://econexo.onrender.com
NEXT_PUBLIC_DEMO_MODE=false
NEXT_PUBLIC_STATIC_EXPORT=true
```

Después de cambiarlas usar `Clear build cache & deploy`, porque `NEXT_PUBLIC_*` se incorpora durante el build.

## Seguridad aplicada

- Argon2 para contraseñas;
- contraseña inicial fuera del repositorio;
- cambio obligatorio antes de usar la API;
- baja lógica de usuarios y organizaciones;
- protección contra auto-desactivación del administrador general;
- auditoría de cambios globales;
- rutas de plataforma excluidas de OpenAPI;
- ruta web con `noindex`;
- almacenamiento de sesión tolerante a bloqueos de navegador.
