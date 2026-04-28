#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing virtualenv python at $PYTHON_BIN"
  echo "Rebuild the environment before starting the service."
  exit 1
fi

cd "$ROOT_DIR"
echo "Using python: $PYTHON_BIN"
exec "$PYTHON_BIN" -m uvicorn services.port.api.main:app --host 127.0.0.1 --port 8002
