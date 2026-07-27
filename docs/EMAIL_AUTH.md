# Login y registro por email

EcoNexo puede utilizarse sin Google Cloud Console. El onboarding principal crea una organización y su primer usuario administrador mediante email y contraseña.

## Flujo

1. Abrir `http://localhost:3000`.
2. Seleccionar **Crear organización**.
3. Completar organización, vertical, nombre del administrador, email y contraseña.
4. Aceptar Términos y Política de Privacidad.
5. El frontend invoca `POST /auth/register`.
6. La API crea organización y administrador dentro de una transacción, registra auditoría y devuelve el JWT de sesión.

La contraseña debe tener al menos 8 caracteres, una letra y un número. Se almacena exclusivamente como hash Argon2.

## Google opcional

Para trabajar sin Google:

```env
GOOGLE_CLIENT_ID=
```

La interfaz oculta el botón de Google y muestra `Registro por email habilitado · Google OAuth desactivado`.

## Verificación local

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

Respuesta esperada:

```json
{"status":"ok","service":"econexo-api"}
```

Para confirmar que la ruta de registro está expuesta, abrir `http://localhost:8000/docs` y buscar `POST /auth/register`.

## Errores diferenciados

- **Credenciales inválidas:** la API está accesible, pero email o contraseña no coinciden.
- **API sin conexión:** la aplicación no puede alcanzar `NEXT_PUBLIC_API_URL`; revisar contenedores, puerto 8000 y CORS.
- **Ya existe una cuenta:** usar la pestaña Ingresar.
- **Error de columnas/tablas:** aplicar migraciones 02, 03 y 04 en orden.

En desarrollo se aceptan tanto `http://localhost:3000` como `http://127.0.0.1:3000` para evitar falsos errores CORS.
