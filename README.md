# anubis-mcp-server-ubuntu

Local Model Context Protocol server for NeuralNexus. Exposes folders on a user's machine and connects to `api.neuralnexus.site` through an **outbound relay** — no Cloudflare account, port forwarding, or inbound firewall rules.

## One-click install

```bash
./neuralnexus-mcp.sh install
```

Or directly:

```bash
./scripts/install.sh
```

On first launch you will be asked for:

1. **API key** — your NeuralNexus `sk-...` key from Account settings
2. **Folder to share** — defaults to a sensible path when available (e.g. Health Auto Export data)

The daemon then:

- runs MCP on `127.0.0.1` only (not exposed to the internet)
- opens an outbound WebSocket to `wss://api.neuralnexus.site/mcp/relay`
- registers presence with `POST /mcp/register` using your `API-KEY`
- proxies API tool calls to the local MCP server over that connection

No Cloudflare or router configuration is required.

### Non-interactive install

For scripted installs, set environment variables before running:

```bash
export NEURALNEXUS_API_KEY=sk-...
export NEURALNEXUS_WATCH_FOLDER="/path/to/your/data"
./scripts/install.sh
```

Or:

```bash
python -m src.daemon setup --non-interactive --api-key sk-... --watch /path/to/data --start
```

## Commands

| Command | Purpose |
|---------|---------|
| `./neuralnexus-mcp.sh` | Interactive menu (install, start, stop, status, logs, uninstall) |
| `./neuralnexus-mcp.sh install` | Install dependencies, run first-time setup, enable systemd service |
| `./scripts/install.sh` | Same as install command above |
| `./scripts/stop.sh` | Stop the background service (SIGTERM) |
| `./scripts/uninstall.sh` | Disable and remove the systemd service |
| `./scripts/uninstall.sh --purge` | Also remove `.venv` and config |
| `python -m src.daemon setup` | Interactive first-time configuration |
| `python -m src.daemon start` | Run MCP + outbound relay in the foreground |
| `python -m src.daemon status` | Show saved configuration |
| `python -m src.daemon configure` | Change settings later |

After install, the daemon runs as a **systemd user service** (`neuralnexus-mcp.service`) and starts on login.

```bash
./neuralnexus-mcp.sh status
./neuralnexus-mcp.sh logs
journalctl --user -u neuralnexus-mcp.service -f
```

To keep the service running after logout:

```bash
loginctl enable-linger $USER
```

Config is stored in `~/.config/neuralnexus-mcp/`. Optional production overrides can go in `.env` at the repo root (loaded by the systemd unit).

### Local development (Anubis test server)

Dev mode is separate from production: different systemd unit, config directory, port, and env file. It does not modify `.env`.

```bash
cp .env.dev.example .env.dev
# edit .env.dev — default API is http://localhost:8123, MCP port 9990
./scripts/dev.sh start
./scripts/dev.sh status
./scripts/dev.sh logs
./scripts/dev.sh stop
```

Production (`./neuralnexus-mcp.sh`) and dev (`./scripts/dev.sh`) can run at the same time without conflicting.

## Connection modes

| Mode | When to use |
|------|-------------|
| `relay` (default) | Normal users — outbound WebSocket only |
| `local` | Development on the same machine as the API |
| `tunnel` | Advanced — optional Cloudflare tunnel if you already use one |

Switch modes:

```bash
python -m src.daemon configure --connection-mode tunnel --tunnel-mode auto
```

## API contract (Anubis side)

The local daemon expects these API endpoints:

| Endpoint | Purpose |
|----------|---------|
| `WSS /mcp/relay` | Outbound relay; API sends `proxy` messages, daemon returns `proxy_response` |
| `POST /mcp/register` | HTTP registration fallback / pending consent |
| `POST /mcp/heartbeat` | Keep-alive every 30s |
| `POST /mcp/unregister` | Clean shutdown |

Relay registration message (WebSocket):

```json
{
  "type": "register",
  "connection_mode": "relay",
  "device_id": "...",
  "device_secret": "mcp_dev_...",
  "server_name": "Ubuntu-OS-Filesystem",
  "transport": "streamable_http",
  "allowed_roots": ["/absolute/path"],
  "local_mcp_url": "http://127.0.0.1:8000"
}
```

HTTP registration (`connection_mode: relay`):

```json
{
  "connection_mode": "relay",
  "transport": "relay",
  "mcp_url": "https://api.neuralnexus.site/mcp/relay/<device_id>",
  "device_secret": "mcp_dev_...",
  "device_id": "...",
  "allowed_roots": ["/absolute/path"],
  "server_name": "Ubuntu-OS-Filesystem"
}
```

## Local development (foreground, no daemon)

Run MCP without the daemon:

```bash
source .venv/bin/activate
MCP_REQUIRE_DEVICE_AUTH=false python -m src.server.app
```

For full daemon + relay testing against a local Anubis instance, use `./scripts/dev.sh` (see above).

## Resources

- https://docs.langchain.com/oss/python/langchain/mcp
- https://gofastmcp.com/getting-started/quickstart
