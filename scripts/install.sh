#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
init_mcp_mode prod
cd "$ROOT_DIR"

load_env_file
install_dependencies
install_and_start_service "$@"

echo "NeuralNexus MCP installed."
echo
echo "NeuralNexus MCP is running as a background service."
echo
echo "  Manage:  ./neuralnexus-mcp.sh"
echo "  Status:  ./neuralnexus-mcp.sh status"
echo "  Stop:    ./scripts/stop.sh"
echo "  Logs:    journalctl --user -u ${SERVICE_NAME} -f"
echo
echo "The service starts automatically on login. To keep it running after logout:"
echo "  loginctl enable-linger \$USER"
echo
echo "Local development against Anubis uses a separate dev service:"
echo "  cp .env.dev.example .env.dev && ./scripts/dev.sh start"
