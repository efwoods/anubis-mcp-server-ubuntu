# NeuralNexus MCP (Ubuntu)

Share folders on your Ubuntu machine with [NeuralNexus](https://neuralnexus.site) to allow your Avatar to read and analyze your local files from your Desktop! Have on demand health analytics from Apple Health! Learn detailed insights in seconds! Receive alerts and notifications based on this health data in the future!

This app runs a small **Model Context Protocol (MCP)** server on your computer and connects to `api.neuralnexus.site` over an **outbound** connection. You do **not** need:

- a Cloudflare account
- port forwarding
- inbound firewall rules
- a public IP

Your files stay on your machine. The API reaches them only through the secure relay you open outward.

---

## Who this is for

| Audience | What you get |
|----------|----------------|
| **Users** | One-command install, pick a folder, leave it running in the background |
| **Developers** | Local MCP + relay against production or a local Anubis API |

---

## Requirements

- Ubuntu (or similar Linux with **systemd**)
- **Python 3.11+**
- A NeuralNexus account and API key (`sk-...`) from Account settings [Signup Here](https://api.neuralnexus.site/docs#POST/signup)
- Network access to `api.neuralnexus.site` (HTTPS / WSS)

---

## Quick start (users)

### 1. Get the project

```bash
git clone <this-repo-url>
cd anubis-mcp-server-ubuntu
```

### 2. Install

```bash
./neuralnexus-mcp.sh install
```

On first launch you will be asked for:

1. **API key** — your NeuralNexus `sk-...` key  
2. **Folder to share** — a directory the AI may read (a sensible default is suggested when available, e.g. Health Auto Export data)

### 3. Confirm it is running

```bash
./neuralnexus-mcp.sh status
```

That is it. The daemon:

- listens on `127.0.0.1` only (not exposed to the internet)
- opens an outbound WebSocket to `wss://api.neuralnexus.site/mcp/relay`
- registers with NeuralNexus using your API key
- proxies tool calls from the API to your local MCP server

After install it runs as a **systemd user service** (`neuralnexus-mcp.service`) and starts when you login.

---

## Day-to-day commands

Run with no arguments for an interactive menu:

```bash
./neuralnexus-mcp.sh
```

Or use commands directly:

| Command | What it does |
|---------|----------------|
| `./neuralnexus-mcp.sh install` | Install dependencies, first-time setup, enable the service |
| `./neuralnexus-mcp.sh start` | Start the service |
| `./neuralnexus-mcp.sh stop` | Stop the service |
| `./neuralnexus-mczp.sh status` | Show service and config status |
| `./neuralnexus-mcp.sh logs` | Follow live logs |
| `./neuralnexus-mcp.sh uninstall` | Remove the systemd service |
| `./neuralnexus-mcp.sh uninstall --purge` | Also remove `.venv` and saved config |

Equivalent scripts:

```bash
./scripts/install.sh
./scripts/stop.sh
./scripts/uninstall.sh
./scripts/uninstall.sh --purge
```

### Logs

```bash
./neuralnexus-mcp.sh logs
# or
journalctl --user -u neuralnexus-mcp.service -f
```

### Keep running after logout

User services stop and restart when you logout/login. To keep MCP running after logout, run the following command:

```bash
loginctl enable-linger $USER
```

### Share more folders

You can share any number of folders. The easiest way is the manager script,
which updates the config and restarts the service for you:

```bash
./neuralnexus-mcp.sh folders                          # list shared folders
./neuralnexus-mcp.sh add-folder ~/Documents ~/Downloads
./neuralnexus-mcp.sh remove-folder ~/Downloads
```

The same options are available under "Shared folders" in the interactive menu
(`./neuralnexus-mcp.sh`).

### Change settings later

```bash
# Activate the venv first if needed
source .venv/bin/activate

python -m src.daemon configure --watch /replace/all/folders
python -m src.daemon configure --add-watch /path/to/another/folder
python -m src.daemon configure --remove-watch /path/to/another/folder
python -m src.daemon status
python -m src.daemon login --api-key sk-...
```

Config lives in `~/.config/neuralnexus-mcp/`.  
Optional production overrides can go in `.env` at the repo root (see `.env.example`).

---

## Non-interactive / scripted install

Useful for automation or headless machines:

```bash
export NEURALNEXUS_API_KEY=sk-...
export NEURALNEXUS_WATCH_FOLDER="/path/to/your/data"
./scripts/install.sh
```

Or:

```bash
source .venv/bin/activate   # after deps are installed
python -m src.daemon setup --non-interactive \
  --api-key sk-... \
  --watch /path/to/data \
  --start
```

---

## How it works (simple picture)

```
Your PC                         NeuralNexus API
┌─────────────────────┐         ┌──────────────────────┐
│ Local MCP (127.0.0.1)│◄───────│  Outbound WebSocket  │
│ Shared folder(s)     │  relay │  api.neuralnexus.site │
└─────────────────────┘         └──────────────────────┘
         ▲
         │ only localhost
         │ (not open to the internet)
```

1. You choose which folder(s) to share.  
2. MCP serves tools over HTTP on localhost.  
3. The daemon keeps an outbound relay open to the API.  
4. When NeuralNexus needs your files, the API sends requests through that relay only.

### Connection modes (Developer Instructions)

| Mode | When to use |
|------|-------------|
| `relay` (default option) | Normal use — outbound WebSocket only |
| `local` | Development on the same machine as the API |
| `tunnel` | Advanced — optional Cloudflare tunnel if you already use one |

Switch modes:

```bash
source .venv/bin/activate
python -m src.daemon configure --connection-mode tunnel --tunnel-mode auto
```

The `relay` option automatically works without configuration.

---

## Local development (developers)

Dev mode is **separate** from production: different systemd unit, config directory, port, and env file. It does **not** modify production `.env` or `~/.config/neuralnexus-mcp/`.

Production and dev can run at the same time.

### Setup

```bash
cp .env.dev.example .env.dev
# Edit .env.dev — defaults point at a local Anubis API
```

Defaults in `.env.dev.example`:

| Setting | Default |
|---------|---------|
| API | `http://localhost:8123` |
| MCP port | `9990` |
| Config dir | `~/.config/neuralnexus-mcp-dev` |
| Service | `neuralnexus-mcp-dev.service` |

Optional non-interactive keys in `.env.dev`:

```bash
# NEURALNEXUS_API_KEY=sk-...
# NEURALNEXUS_WATCH_FOLDER=/path/to/test/data
```

### Development helper scripts:

```bash
./scripts/dev.sh start
./scripts/dev.sh status
./scripts/dev.sh logs
./scripts/dev.sh stop
./scripts/dev.sh restart
```

### Foreground MCP only (no daemon / relay)

```bash
source .venv/bin/activate
MCP_REQUIRE_DEVICE_AUTH=false python -m src.server.app
```

For full daemon + relay against a local Anubis instance, prefer `./scripts/dev.sh`.

### Daemon CLI (advanced)

```bash
source .venv/bin/activate

python -m src.daemon setup          # interactive first-time config
python -m src.daemon start          # MCP + relay in the foreground
python -m src.daemon status
python -m src.daemon configure
python -m src.daemon login
```

---

## API contract (Anubis / backend developers)

The local daemon expects these endpoints on the API:

| Endpoint | Purpose |
|----------|---------|
| `WSS /mcp/relay` | Outbound relay; API sends `proxy` messages, daemon returns `proxy_response` |
| `POST /mcp/register` | HTTP registration / pending consent |
| `POST /mcp/heartbeat` | Keep-alive (every ~30s) |
| `POST /mcp/unregister` | Clean shutdown |

### Relay registration (WebSocket)

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

### HTTP registration (`connection_mode: relay`)

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

---

## Uninstall

```bash
# Remove the service only (keep venv + config)
./neuralnexus-mcp.sh uninstall

# Remove service, virtualenv, and config
./neuralnexus-mcp.sh uninstall --purge
```

Dev service (if you used it):

```bash
./scripts/dev.sh stop
# then remove the unit if needed via the same uninstall flow after switching context,
# or: systemctl --user disable --now neuralnexus-mcp-dev.service
```

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Install asks for API key / folder every time | Check that `~/.config/neuralnexus-mcp/` was written and is readable |
| Service will not start | `./neuralnexus-mcp.sh status` and `./neuralnexus-mcp.sh logs` |
| `systemctl --user` errors | Ensure you are logged in and `$XDG_RUNTIME_DIR` is set |
| Stops after logout | `loginctl enable-linger $USER` |
| Dev vs prod confusion | Prod: `./neuralnexus-mcp.sh` + `.env` + `~/.config/neuralnexus-mcp/` · Dev: `./scripts/dev.sh` + `.env.dev` + `~/.config/neuralnexus-mcp-dev/` |
| Python missing | Install Python 3.11+ and re-run install |

---

## Project layout (high overview)

```
neuralnexus-mcp.sh     # Main user entrypoint (menu + commands)
scripts/               # install, stop, uninstall, dev helpers
src/daemon/            # Setup, relay, registration, systemd lifecycle
src/server/            # Local MCP HTTP server
.env.example           # Optional production overrides
.env.dev.example       # Local Anubis / dev template
```

---

## Reference Documentation

- [LangChain MCP docs](https://docs.langchain.com/oss/python/langchain/mcp)
- [FastMCP quickstart](https://gofastmcp.com/getting-started/quickstart)
