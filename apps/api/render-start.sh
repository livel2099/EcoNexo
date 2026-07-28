#!/bin/sh
set -eu

python -m app.check_config

if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
  python -m app.migrate
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
