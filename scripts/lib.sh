#!/usr/bin/env bash
# Shared helpers for NeuralNexus MCP install/manage scripts.

MCP_MODE="prod"
SERVICE_NAME=""
ENV_FILE=""
DEFAULT_CONFIG_DIR=""

_resolve_repo_paths() {
  local source="${BASH_SOURCE[2]:-${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}}"
  SCRIPT_DIR="$(cd "$(dirname "$source")" && pwd)"
  if [[ "$(basename "$SCRIPT_DIR")" == "scripts" ]]; then
    SCRIPTS_DIR="$SCRIPT_DIR"
    ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
  else
    ROOT_DIR="$SCRIPT_DIR"
    SCRIPTS_DIR="$ROOT_DIR/scripts"
  fi
}

init_mcp_mode() {
  local mode="${1:-prod}"
  MCP_MODE="$mode"
  if [[ "$MCP_MODE" == "dev" ]]; then
    SERVICE_NAME="neuralnexus-mcp-dev.service"
    ENV_FILE="${ROOT_DIR}/.env.dev"
    DEFAULT_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/neuralnexus-mcp-dev"
  else
    SERVICE_NAME="neuralnexus-mcp.service"
    ENV_FILE="${ROOT_DIR}/.env"
    DEFAULT_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/neuralnexus-mcp"
  fi
  CONFIG_DIR="${NEURALNEXUS_MCP_CONFIG_DIR:-$DEFAULT_CONFIG_DIR}"

  # Unit path is mode-specific and must be recomputed whenever the mode
  # changes, otherwise a dev invocation would write to the production unit.
  UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  UNIT_PATH="${UNIT_DIR}/${SERVICE_NAME}"
}

_resolve_repo_paths
init_mcp_mode prod

require_python3() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required. Install Python 3.11+ and re-run." >&2
    exit 1
  fi
}

require_systemd_user() {
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl is required for service management." >&2
    exit 1
  fi
  if ! systemctl --user status >/dev/null 2>&1; then
    echo "Could not connect to the systemd user session." >&2
    echo "Ensure you are logged in and \$XDG_RUNTIME_DIR is set." >&2
    exit 1
  fi
}

require_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "Missing ${ENV_FILE}." >&2
    if [[ "$MCP_MODE" == "dev" ]]; then
      echo "Copy .env.dev.example to .env.dev and adjust for local Anubis." >&2
    fi
    exit 1
  fi
}

load_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  elif [[ "$MCP_MODE" == "dev" ]]; then
    require_env_file
  fi
  CONFIG_DIR="${NEURALNEXUS_MCP_CONFIG_DIR:-$DEFAULT_CONFIG_DIR}"
}

install_dependencies() {
  require_python3
  cd "$ROOT_DIR"

  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
  fi

  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt -q
}

is_first_run() {
  load_env_file
  "${ROOT_DIR}/.venv/bin/python" -c "from src.daemon.setup import is_first_run; import sys; sys.exit(0 if is_first_run() else 1)"
}

run_first_run_setup() {
  load_env_file
  if ! is_first_run; then
    return 0
  fi

  echo "First run — configuring daemon (${MCP_MODE})..."
  if [[ -t 0 ]]; then
    "${ROOT_DIR}/.venv/bin/python" -m src.daemon setup "$@"
  elif [[ -n "${NEURALNEXUS_API_KEY:-}" ]]; then
    "${ROOT_DIR}/.venv/bin/python" -m src.daemon setup --non-interactive "$@"
  else
    echo "First run requires an interactive terminal or NEURALNEXUS_API_KEY." >&2
    return 1
  fi
}

apply_env_to_config() {
  load_env_file
  if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
    return 0
  fi

  local args=()
  if [[ -n "${NEURALNEXUS_API_BASE_URL:-}" ]]; then
    args+=(--api-base-url "$NEURALNEXUS_API_BASE_URL")
  fi
  if [[ -n "${PORT:-}" ]]; then
    args+=(--port "$PORT")
  fi
  if [[ ${#args[@]} -gt 0 ]]; then
    "${ROOT_DIR}/.venv/bin/python" -m src.daemon configure "${args[@]}"
  fi
}

install_systemd_unit() {
  load_env_file
  local description="NeuralNexus MCP daemon"
  if [[ "$MCP_MODE" == "dev" ]]; then
    description="NeuralNexus MCP daemon (dev)"
  fi

  # Resolve the config dir to an absolute path here. systemd's EnvironmentFile
  # does not perform tilde or variable expansion, so a value like
  # "~/.config/neuralnexus-mcp-dev" in .env.dev would otherwise be created
  # literally under the working directory. Inject the expanded path directly.
  local config_dir="${CONFIG_DIR/#\~/$HOME}"

  mkdir -p "$UNIT_DIR"
  cat >"$UNIT_PATH" <<EOF
[Unit]
Description=${description}
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${ROOT_DIR}
ExecStart=${ROOT_DIR}/.venv/bin/python -m src.daemon start
ExecStop=/bin/kill -TERM \$MAINPID
Restart=on-failure
RestartSec=5
EnvironmentFile=-${ENV_FILE}
Environment=NEURALNEXUS_MCP_CONFIG_DIR=${config_dir}

[Install]
WantedBy=default.target
EOF
}

remove_systemd_unit() {
  if [[ -f "$UNIT_PATH" ]]; then
    rm -f "$UNIT_PATH"
  fi
  systemctl --user daemon-reload
}

service_is_installed() {
  [[ -f "$UNIT_PATH" ]]
}

start_service() {
  require_systemd_user
  systemctl --user daemon-reload
  systemctl --user enable --now "$SERVICE_NAME"
}

stop_service() {
  require_systemd_user
  if service_is_installed; then
    systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true
    return 0
  fi

  stop_foreground_daemon
}

stop_foreground_daemon() {
  load_env_file
  local port pid
  port="$("${ROOT_DIR}/.venv/bin/python" -c "from src.daemon.config import DaemonConfig; print(DaemonConfig.load().local_port)" 2>/dev/null || echo "${PORT:-8000}")"
  pid="$(lsof -ti ":${port}" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    echo "No NeuralNexus MCP daemon (${MCP_MODE}) found on port ${port}."
    return 0
  fi
  echo "Stopping ${MCP_MODE} process on port ${port} (PID ${pid})..."
  kill -TERM $pid 2>/dev/null || true
  sleep 2
  if kill -0 $pid 2>/dev/null; then
    echo "Process did not exit; sending SIGKILL..."
    kill -KILL $pid 2>/dev/null || true
  fi
}

install_and_start_service() {
  run_first_run_setup "$@"
  apply_env_to_config
  install_systemd_unit
  start_service
}

show_service_status() {
  require_systemd_user
  echo "Mode: ${MCP_MODE}"
  echo "Env:  ${ENV_FILE}"
  echo "Config: ${CONFIG_DIR}"
  echo
  if service_is_installed; then
    systemctl --user status "$SERVICE_NAME" --no-pager || true
    echo
  else
    echo "Systemd unit not installed (${UNIT_PATH})."
    echo
  fi
  if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
    load_env_file
    "${ROOT_DIR}/.venv/bin/python" -m src.daemon status || true
  fi
}
