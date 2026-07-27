# EcoNexo Mobile

Aplicación móvil Expo/React Native para Android e iOS. Comparte la API, PostgreSQL/PostGIS, usuarios, módulos y auditoría de la plataforma web.

## Funciones incluidas

- Inicio de sesión y registro por email.
- Acceso opcional con Google OAuth.
- Centro de comando móvil con KPIs, alertas y dispositivos.
- Módulo licenciado **Focos de incendio forestal y humo**.
- Mapa nativo con nodos, alertas y señales térmicas.
- Contexto meteorológico y de calidad del aire mediante Open-Meteo/CAMS.
- **Alerta IA** explicable, con fórmulas SpaceAI visibles.
- Distribución revisada por WhatsApp, Telegram o el menú del sistema.
- Formulario de reporte comunitario/institucional con ubicación, cámara o galería.
- Sesión persistente protegida con `expo-secure-store`.
- Sin rastreo de ubicación en segundo plano.

## Requisitos

- Node.js 20.19 o superior.
- npm.
- Expo Go para pruebas rápidas, o EAS CLI para builds instalables.
- API EcoNexo accesible desde el dispositivo.

## Configuración

```powershell
cd apps\mobile
Copy-Item .env.example .env
```

Editá `.env`:

```env
# Celular físico: usar la IP LAN de la PC, no localhost.
EXPO_PUBLIC_API_URL=http://192.168.0.25:8000
EXPO_PUBLIC_DEMO_MODE=false

# Opcional. El login por email funciona si quedan vacíos.
EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=
EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID=
EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID=
```

Para conocer la IP local de Windows:

```powershell
ipconfig
```

El celular y la PC deben estar en la misma red. También hay que permitir el puerto 8000 en el firewall local.

## Ejecutar en desarrollo

```powershell
npm install
npx expo install --fix
npm run start:clear
```

Escaneá el QR con Expo Go.

Casos habituales de URL de API:

```text
Android Emulator: http://10.0.2.2:8000
iOS Simulator:     http://127.0.0.1:8000
Celular físico:    http://IP-DE-LA-PC:8000
API productiva:    https://api.tudominio.com
```

## Modo demo autónomo

```env
EXPO_PUBLIC_DEMO_MODE=true
```

En este modo la app incluye datos de muestra y no necesita PostgreSQL ni FastAPI. Open-Meteo puede seguir consultarse cuando hay internet.

## Google OAuth

Google es opcional. Para habilitarlo se necesitan clientes OAuth para Web, Android e iOS. La API debe aceptar las audiences correspondientes:

```env
GOOGLE_CLIENT_ID=CLIENTE_WEB
GOOGLE_CLIENT_IDS=CLIENTE_WEB,CLIENTE_ANDROID,CLIENTE_IOS
```

En la app:

```env
EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=CLIENTE_WEB
EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID=CLIENTE_ANDROID
EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID=CLIENTE_IOS
```

No se almacena la contraseña de Google. La app obtiene un ID token y la API vuelve a verificar firma, expiración, issuer, email validado y audience.

## Build con EAS

Instalación inicial:

```powershell
npm install -g eas-cli
eas login
eas build:configure
```

El comando `eas build:configure` reemplaza el `projectId` de ejemplo en `app.json`.

Android de prueba:

```powershell
npm run build:android:preview
```

Android para Play Store:

```powershell
npm run build:android:production
```

iOS de prueba o producción:

```powershell
npm run build:ios:preview
npm run build:ios:production
```

## Verificaciones

```powershell
npm run typecheck
npm run doctor
```

## Seguridad operativa

- No publicar una URL `http://localhost:8000` dentro de un build distribuido.
- En producción usar HTTPS para la API.
- El módulo de fuego genera lecturas preventivas: una señal térmica no equivale a un incendio confirmado.
- WhatsApp y Telegram siempre se abren después de la revisión humana del mensaje.
- Una emergencia debe comunicarse por los canales oficiales; el formulario no sustituye una llamada al 911.
