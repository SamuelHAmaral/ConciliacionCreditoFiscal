#!/usr/bin/env bash
# Kowalski / Linux entry. Windows equivalent: run_cabo.bat
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ ! -f "src/pipeline/run_reconciliation.py" ]; then
  echo "No se encuentra el proyecto. Ejecute este archivo desde la raiz del repositorio." >&2
  exit 1
fi

export PYTHONPATH="${ROOT}/src:${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "${ROOT}/scripts/cabo_runner.py" "$@"
fi
exec python "${ROOT}/scripts/cabo_runner.py" "$@"
