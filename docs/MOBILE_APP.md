# Aplicación móvil EcoNexo

## Alcance funcional

La aplicación móvil es un cliente nativo del backend EcoNexo. No duplica la base: usa las mismas organizaciones, usuarios, dispositivos, alertas, reportes, módulos y snapshots ambientales que la plataforma web.

### Navegación principal

1. **Inicio:** KPIs, estado de la red, alertas priorizadas y acciones operativas.
2. **Fuego:** licencia independiente para focos de incendio forestal y humo, mapa nativo, lenguaje ciudadano, contexto de viento/aire y comunicación controlada.
3. **Alerta IA:** score integrado, nivel R0-R5, dominios, evidencia, fórmulas y mensajes para WhatsApp/Telegram.
4. **Reportar:** ubicación, foto, descripción, tipo de incidente y moderación posterior.
5. **Cuenta:** organización, sesión, API, módulos licenciados y cierre seguro.

## Arquitectura

```text
Expo / React Native
  ├─ SecureStore: sesión JWT
  ├─ AuthSession: Google OAuth opcional
  ├─ react-native-maps: mapa nativo
  ├─ expo-location: ubicación bajo demanda
  ├─ expo-image-picker: cámara y galería
  └─ Fetch HTTPS
       ├─ FastAPI EcoNexo
       ├─ PostgreSQL + PostGIS
       ├─ MinIO/S3
       └─ Open-Meteo/CAMS + detecciones satelitales persistidas
```

## Privacidad

La app no solicita ubicación permanente. El permiso se pide únicamente cuando el usuario selecciona “Usar mi ubicación actual” en un reporte. No hay geolocalización en segundo plano.

Las fotografías son opcionales y se cargan a almacenamiento privado. El backend valida firma real del archivo, tamaño y tipo MIME antes de persistirlo.

## Autenticación

Email/password está disponible siempre. Google puede habilitarse de forma independiente por plataforma. La API admite una lista explícita de audiences para evitar aceptar tokens emitidos para aplicaciones no autorizadas.

## Distribución

Se incluyen perfiles EAS `preview` y `production`. Antes de publicar en tiendas deben completarse:

- identificadores definitivos de Apple/Google;
- política de privacidad pública;
- ficha de seguridad de datos;
- iconos y screenshots finales;
- URL HTTPS de API;
- pruebas en equipos físicos;
- revisión de permisos;
- términos comerciales de la licencia Fuego & Humo.
