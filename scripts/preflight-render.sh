#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

python scripts/audit-system.py

echo "Preflight Render aprobado."
echo "Build recomendado: npm ci && npm run typecheck && npm run build:cloudflare:production"
