#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

echo "[1/6] Buscando conflictos Git..."
if grep -R -nE '^(<<<<<<<|=======|>>>>>>>)' apps services infra \
  --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=out --exclude-dir=__pycache__; then
  echo "Hay marcadores de conflicto sin resolver." >&2
  exit 1
fi

echo "[2/6] Compilando Python..."
python -m compileall -q apps/api/app services/satellite/app

echo "[3/6] Verificando migracion 14..."
cmp infra/db/migrations/14_telemetry_pipeline_and_map.sql \
  apps/api/migrations/14_telemetry_pipeline_and_map.sql

echo "[4/6] TypeScript..."
(cd apps/web && npm run typecheck)

echo "[5/6] Validando YAML..."
python - <<'PY'
import pathlib, yaml
for name in ('render.yaml', 'render.production.yaml'):
    yaml.safe_load(pathlib.Path(name).read_text())
print('YAML OK')
PY

echo "[6/6] Estado Git..."
git status --short || true

echo "Preflight aprobado."
