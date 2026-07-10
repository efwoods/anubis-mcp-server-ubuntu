#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=scripts/lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/lib.sh"

usage() {
  cat <<EOF
NeuralNexus MCP manager

Usage:
  ./neuralnexus-mcp.sh                    Interactive menu
  ./neuralnexus-mcp.sh install            Install deps and start systemd service
  ./neuralnexus-mcp.sh start              Enable and start the service
  ./neuralnexus-mcp.sh stop               Stop the service
  ./neuralnexus-mcp.sh restart            Restart the service
  ./neuralnexus-mcp.sh status             Show service and config status
  ./neuralnexus-mcp.sh logs               Follow service logs
  ./neuralnexus-mcp.sh uninstall          Remove systemd service
  ./neuralnexus-mcp.sh uninstall --purge  Also remove .venv and config

Scripts (also runnable directly):
  ./scripts/install.sh
  ./scripts/stop.sh
  ./scripts/uninstall.sh

Local development (separate service, uses .env.dev):
  ./scripts/dev.sh start
  ./scripts/dev.sh stop
EOF
}

cmd_install() {
  exec "$SCRIPTS_DIR/install.sh" "$@"
}

cmd_start() {
  require_systemd_user
  if ! service_is_installed; then
    echo "Service is not installed. Run ./neuralnexus-mcp.sh install first." >&2
    exit 1
  fi
  install_systemd_unit
  start_service
  echo "Started ${SERVICE_NAME}."
}

cmd_stop() {
  exec "$SCRIPTS_DIR/stop.sh"
}

cmd_restart() {
  require_systemd_user
  if ! service_is_installed; then
    echo "Service is not installed. Run ./neuralnexus-mcp.sh install first." >&2
    exit 1
  fi
  systemctl --user restart "$SERVICE_NAME"
  echo "Restarted ${SERVICE_NAME}."
}

cmd_status() {
  show_service_status
}

cmd_logs() {
  require_systemd_user
  exec journalctl --user -u "$SERVICE_NAME" -f
}

cmd_uninstall() {
  exec "$SCRIPTS_DIR/uninstall.sh" "$@"
}

interactive_menu() {
  while true; do
    echo
    echo "NeuralNexus MCP"
    echo "  1) Install"
    echo "  2) Start"
    echo "  3) Stop"
    echo "  4) Restart"
    echo "  5) Status"
    echo "  6) Logs"
    echo "  7) Uninstall"
    echo "  8) Exit"
    echo
    read -r -p "Choose an option [1-8]: " choice
    case "$choice" in
      1) cmd_install ;;
      2) cmd_start ;;
      3) cmd_stop ;;
      4) cmd_restart ;;
      5) cmd_status ;;
      6) cmd_logs ;;
      7) cmd_uninstall ;;
      8) exit 0 ;;
      *)
        echo "Invalid choice."
        ;;
    esac
  done
}

if [[ $# -eq 0 ]]; then
  if [[ -t 0 ]]; then
    interactive_menu
  else
    usage
    exit 1
  fi
fi

case "$1" in
  install) shift; cmd_install "$@" ;;
  start) cmd_start ;;
  stop) cmd_stop ;;
  restart) cmd_restart ;;
  status) cmd_status ;;
  logs) cmd_logs ;;
  uninstall) shift; cmd_uninstall "$@" ;;
  -h | --help | help) usage ;;
  *)
    echo "Unknown command: $1" >&2
    usage >&2
    exit 1
    ;;
esac
