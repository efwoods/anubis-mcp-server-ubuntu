#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install Python 3.11+ and re-run ./install.sh" >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

echo "NeuralNexus MCP installed."
echo "Starting daemon (setup runs automatically on first launch)..."
echo

exec .venv/bin/python -m src.daemon start "$@"
