# anubis-mcp-server-ubuntu

Local Model Context Protocol server for NeuralNexus. Exposes folders on a user's machine and connects to `api.neuralnexus.site` through an **outbound relay** — no Cloudflare account, port forwarding, or inbound firewall rules.

## One-click install

```bash
./install.sh
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
./install.sh
```

Or:

```bash
python -m src.daemon setup --non-interactive --api-key sk-... --watch /path/to/data --start
```

## Commands

| Command | Purpose |
|---------|---------|
| `./install.sh` | Install dependencies and start (runs setup on first launch) |
| `python -m src.daemon setup` | Interactive first-time configuration |
| `python -m src.daemon start` | Run MCP + outbound relay |
| `python -m src.daemon status` | Show saved configuration |
| `python -m src.daemon configure` | Change settings later |

Config is stored in `~/.config/neuralnexus-mcp/`.

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

## Local development

Run MCP without the daemon:

```bash
source .venv/bin/activate
MCP_REQUIRE_DEVICE_AUTH=false python -m src.server.app
```

## Resources

- https://docs.langchain.com/oss/python/langchain/mcp
- https://gofastmcp.com/getting-started/quickstart
