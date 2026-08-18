# EcoNexoFoI

EcoNexoFoI es la red gratuita de investigación integrada a la plataforma oficial de EcoNexo. Vive en `/red-investigacion`; las cuentas comunitarias no ingresan al centro de comando institucional y las cuentas institucionales pueden abrir ambos espacios.

## Acceso

Desde `/login` existen tres opciones: ingresar con una cuenta existente, crear una organización o crear una cuenta gratuita de EcoNexoFoI. El alta gratuita usa `POST /auth/community/register`, crea un perfil profesional dentro de la organización comunitaria compartida y devuelve una sesión con `account_type=community`.

## Funciones implementadas

- publicaciones de investigación, preguntas y propuestas;
- comunidades temáticas, seguimiento de personas, favoritos y reacciones;
- comentarios y perfiles profesionales;
- búsqueda y filtros por comunidad, seguidos o guardados;
- adjuntos PDF, DOC/DOCX, CSV, PNG, JPG y WebP de hasta 15 MB;
- logo SVG propio y diseño responsive con la paleta EcoNexoFoI.

## Backend y datos

La migración `16_econexofoi_research_network.sql` se ejecuta con el mecanismo habitual de migraciones. Está duplicada y sincronizada en `apps/api/migrations` e `infra/db/migrations`.

Cuando `S3_ENABLED=true`, los adjuntos usan el almacenamiento S3 compatible configurado. Cuando está deshabilitado —como en el Blueprint gratuito de Render— se guardan en PostgreSQL y se descargan mediante una ruta autenticada. Para una instalación de alto volumen se recomienda habilitar R2 o S3.

## Despliegue

El Blueprint `render.yaml` ya ejecuta migraciones antes de iniciar FastAPI y compila el frontend con `NEXT_PUBLIC_DEMO_MODE=false`. No requiere variables nuevas para el plan inicial gratuito. Google continúa siendo opcional y sólo se habilita al configurar el mismo Client ID en backend y frontend.