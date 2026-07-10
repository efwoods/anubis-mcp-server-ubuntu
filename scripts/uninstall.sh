#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
cd "$ROOT_DIR"

PURGE=0
for arg in "$@"; do
  case "$arg" in
    --purge)
      PURGE=1
      ;;
    -h | --help)
      echo "Usage: ./scripts/uninstall.sh [--purge]"
      echo
      echo "  --purge  Also remove .venv and config in ${CONFIG_DIR}"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      echo "Usage: ./scripts/uninstall.sh [--purge]" >&2
      exit 1
      ;;
  esac
done

if service_is_installed; then
  require_systemd_user
  echo "Stopping and disabling ${SERVICE_NAME}..."
  systemctl --user disable --now "$SERVICE_NAME" 2>/dev/null || true
fi

if [[ -f "$UNIT_PATH" ]]; then
  echo "Removing systemd unit..."
  remove_systemd_unit
fi

if [[ "$PURGE" -eq 1 ]]; then
  if [[ -d "${ROOT_DIR}/.venv" ]]; then
    echo "Removing virtual environment..."
    rm -rf "${ROOT_DIR}/.venv"
  fi
  if [[ -d "$CONFIG_DIR" ]]; then
    echo "Removing configuration in ${CONFIG_DIR}..."
    rm -rf "$CONFIG_DIR"
  fi
  echo "Purge complete."
else
  echo "Uninstalled service. Virtual environment and config were kept."
  echo "Run ./scripts/uninstall.sh --purge to remove them."
fi

echo "NeuralNexus MCP uninstalled."
