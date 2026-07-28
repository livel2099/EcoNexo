#!/usr/bin/env python3
"""Auditoria reproducible de EcoNexo para CI y pre-deploy.

Uso recomendado:
    python scripts/audit-system.py
    python scripts/audit-system.py --build-web --json-report audit-result.json

El chequeo no usa credenciales productivas ni realiza llamadas reales a Copernicus.
Las integraciones externas se verifican mediante contratos y pruebas con MockTransport.
"""
from __future__ import annotations

import argparse
import compileall
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "out",
}
TEXT_SUFFIXES = {
    ".css", ".env", ".html", ".js", ".json", ".jsonc", ".md", ".mjs",
    ".py", ".sh", ".sql", ".toml", ".ts", ".tsx", ".txt", ".yaml", ".yml",
}
CONFLICT_PATTERN = re.compile(r"^(<<<<<<<|=======|>>>>>>>)", re.MULTILINE)
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


class AuditFailure(RuntimeError):
    pass


def iter_source_files() -> Iterable[Path]:
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name.startswith(".env"):
            yield path


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    merged = os.environ.copy()
    if env:
        merged.update(env)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
        "output": completed.stdout.rstrip(),
    }


def check_conflicts() -> dict[str, Any]:
    matches: list[str] = []
    for path in iter_source_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if CONFLICT_PATTERN.search(text):
            matches.append(path.relative_to(ROOT).as_posix())
    if matches:
        raise AuditFailure("Marcadores Git sin resolver: " + ", ".join(matches))
    return {"files_scanned": sum(1 for _ in iter_source_files())}


def check_secret_hygiene() -> dict[str, Any]:
    actual_env = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob(".env")
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts)
    ]
    private_keys: list[str] = []
    for path in iter_source_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PRIVATE_KEY_PATTERN.search(text):
            private_keys.append(path.relative_to(ROOT).as_posix())
    if actual_env:
        raise AuditFailure("Archivos .env reales dentro del proyecto: " + ", ".join(actual_env))
    if private_keys:
        raise AuditFailure("Claves privadas embebidas: " + ", ".join(private_keys))
    return {"actual_env_files": 0, "private_keys": 0}


def check_migrations() -> dict[str, Any]:
    api_dir = ROOT / "apps/api/migrations"
    infra_dir = ROOT / "infra/db/migrations"
    api = {path.name: path.read_bytes() for path in api_dir.glob("*.sql")}
    infra = {path.name: path.read_bytes() for path in infra_dir.glob("*.sql")}
    if set(api) != set(infra):
        only_api = sorted(set(api) - set(infra))
        only_infra = sorted(set(infra) - set(api))
        raise AuditFailure(f"Migraciones desincronizadas. Solo API={only_api}; solo infra={only_infra}")
    mismatched = sorted(name for name in api if api[name] != infra[name])
    if mismatched:
        raise AuditFailure("Migraciones con contenido diferente: " + ", ".join(mismatched))
    required = "15_copernicus_process_defaults_and_pipeline_guards.sql"
    if required not in api:
        raise AuditFailure(f"Falta {required}")
    sql = api[required].decode("utf-8")
    required_tokens = (
        "copernicus_use_system_default",
        "ALTER COLUMN copernicus_enabled SET DEFAULT true",
        "uq_pipeline_runs_one_running_per_org",
    )
    missing = [token for token in required_tokens if token not in sql]
    if missing:
        raise AuditFailure("Migracion 15 incompleta: " + ", ".join(missing))
    return {"count": len(api), "latest": required}


def check_structured_files() -> dict[str, Any]:
    checked_json: list[str] = []
    for path in (
        ROOT / "apps/web/package.json",
        ROOT / "apps/web/package-lock.json",
        ROOT / "apps/mobile/app.json",
        ROOT / "apps/mobile/package.json",
    ):
        json.loads(path.read_text(encoding="utf-8"))
        checked_json.append(path.relative_to(ROOT).as_posix())

    checked_yaml: list[str] = []
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise AuditFailure("PyYAML es necesario para validar render.yaml") from exc
    for path in (ROOT / "render.yaml", ROOT / "render.production.yaml"):
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or "services" not in value:
            raise AuditFailure(f"Blueprint invalido: {path.name}")
        checked_yaml.append(path.relative_to(ROOT).as_posix())
    return {"json": checked_json, "yaml": checked_yaml}



def check_shell_scripts() -> dict[str, Any]:
    shell = shutil.which("sh")
    if not shell:
        raise AuditFailure("sh no está disponible")
    scripts = [
        path for path in ROOT.rglob("*.sh")
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts)
    ]
    for path in scripts:
        result = run([shell, "-n", str(path)])
        if result["returncode"] != 0:
            raise AuditFailure(f"Shell inválido en {path.relative_to(ROOT)}: {result['output']}")
    return {"count": len(scripts)}


def check_node_services() -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        raise AuditFailure("node no está disponible")
    roots = [ROOT / "services", ROOT / "simulator"]
    scripts = [
        path for base in roots for path in base.rglob("*.js")
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts)
    ]
    for path in scripts:
        result = run([node, "--check", str(path)])
        if result["returncode"] != 0:
            raise AuditFailure(f"JavaScript inválido en {path.relative_to(ROOT)}: {result['output']}")
    return {"count": len(scripts)}

def check_python_compile() -> dict[str, Any]:
    targets = [ROOT / "apps/api/app", ROOT / "services/satellite/app"]
    ok = all(compileall.compile_dir(str(path), quiet=1, force=True) for path in targets)
    if not ok:
        raise AuditFailure("Falló compileall")
    return {"targets": [path.relative_to(ROOT).as_posix() for path in targets]}


def check_api_tests() -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "-q", "apps/api/tests"]
    result = run(command)
    if result["returncode"] != 0:
        raise AuditFailure(result["output"] or "Fallaron los tests de API")
    return result


def check_routes() -> dict[str, Any]:
    code = (
        "import json; from app.main import app; "
        "paths={getattr(r,'path','') for r in app.routes}; "
        "required={'/copernicus/status','/copernicus/test','/copernicus/image',"
        "'/pipeline/settings','/pipeline/run','/platform/summary'}; "
        "missing=required-paths; "
        "assert not missing, missing; "
        "print(json.dumps({'objects':len(app.routes),'unique':len(paths),"
        "'documented':sum(bool(getattr(r,'include_in_schema',False)) for r in app.routes),"
        "'required':sorted(required)}))"
    )
    existing = os.environ.get("PYTHONPATH", "")
    pythonpath = os.pathsep.join(
        value for value in (existing, str(ROOT / "apps/api")) if value
    )
    env: dict[str, str] = {"PYTHONPATH": pythonpath}
    result = run([sys.executable, "-c", code], env=env)
    if result["returncode"] != 0:
        raise AuditFailure(result["output"] or "No se pudo construir FastAPI")
    try:
        route_summary = json.loads(result["output"].splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise AuditFailure("La auditoría de rutas no devolvió JSON válido") from exc
    return {**result, "routes": route_summary}


def check_web_typecheck() -> dict[str, Any]:
    npm = shutil.which("npm")
    if not npm:
        raise AuditFailure("npm no está disponible")
    result = run([npm, "run", "typecheck"], cwd=ROOT / "apps/web")
    if result["returncode"] != 0:
        raise AuditFailure(result["output"] or "Falló TypeScript")
    return result


def check_web_build() -> dict[str, Any]:
    npm = shutil.which("npm")
    if not npm:
        raise AuditFailure("npm no está disponible")
    env = {
        "NEXT_PUBLIC_API_URL": "https://econexo-api.example.invalid",
        "NEXT_PUBLIC_WS_URL": "wss://econexo-api.example.invalid",
        "NEXT_PUBLIC_DEMO_MODE": "false",
        "NEXT_PUBLIC_STATIC_EXPORT": "true",
    }
    result = run([npm, "run", "build:cloudflare:production"], cwd=ROOT / "apps/web", env=env)
    if result["returncode"] != 0:
        raise AuditFailure(result["output"] or "Falló el build web")
    return result


def execute_check(name: str, function, report: dict[str, Any]) -> None:
    started = time.monotonic()
    print(f"[AUDIT] {name}...", flush=True)
    try:
        detail = function()
    except Exception as exc:
        report["checks"][name] = {
            "ok": False,
            "duration_seconds": round(time.monotonic() - started, 3),
            "error": str(exc),
        }
        print(f"[FAIL] {name}: {exc}", flush=True)
        report["ok"] = False
    else:
        report["checks"][name] = {
            "ok": True,
            "duration_seconds": round(time.monotonic() - started, 3),
            "detail": detail,
        }
        print(f"[ OK ] {name}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoria de EcoNexo")
    parser.add_argument("--build-web", action="store_true", help="ejecuta el build estático de Next.js")
    parser.add_argument("--skip-tests", action="store_true", help="omite pytest")
    parser.add_argument("--skip-typecheck", action="store_true", help="omite TypeScript")
    parser.add_argument("--json-report", type=Path, help="guarda el resultado estructurado")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "project": "EcoNexo",
        "release": "1.0.0-rc.6.2",
        "ok": True,
        "checks": {},
    }
    checks = [
        ("conflictos_git", check_conflicts),
        ("higiene_secretos", check_secret_hygiene),
        ("migraciones", check_migrations),
        ("json_yaml", check_structured_files),
        ("shell_syntax", check_shell_scripts),
        ("node_services_syntax", check_node_services),
        ("python_compile", check_python_compile),
        ("fastapi_routes", check_routes),
    ]
    if not args.skip_tests:
        checks.append(("api_tests", check_api_tests))
    if not args.skip_typecheck:
        checks.append(("web_typecheck", check_web_typecheck))
    if args.build_web:
        checks.append(("web_build", check_web_build))

    for name, function in checks:
        execute_check(name, function, report)

    if args.json_report:
        destination = args.json_report
        if not destination.is_absolute():
            destination = ROOT / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Reporte JSON: {destination}")

    print("AUDITORIA APROBADA" if report["ok"] else "AUDITORIA CON ERRORES")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
