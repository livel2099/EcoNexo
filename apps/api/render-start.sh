#!/bin/sh
# Arranque en Render. Cada paso se anuncia antes de correr: un "Exited with
# status 1" sin contexto no permite distinguir una configuracion invalida de
# una base inalcanzable o de un fallo de uvicorn, y cada diagnostico equivocado
# cuesta un deploy completo.
set -eu

echo "[econexo] paso 1/3 - validando configuracion"
if ! python -m app.check_config; then
  echo "[econexo] FALLO en el paso 1 (configuracion). No se intenta conectar a la base." >&2
  exit 1
fi

echo "[econexo] paso 2/3 - migraciones (RUN_MIGRATIONS_ON_START=${RUN_MIGRATIONS_ON_START:-false})"
if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
  if ! python -m app.migrate; then
    echo "[econexo] FALLO en el paso 2 (migraciones). Ver el host que reporta la linea 'Conectando a'." >&2
    exit 1
  fi
else
  echo "[econexo] migraciones omitidas por configuracion"
fi

echo "[econexo] paso 3/3 - iniciando uvicorn en el puerto ${PORT:-8000}"
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
