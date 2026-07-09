# Application UX

## One-click install

```bash
./install.sh
```

Follow-up questions on first run only:

- NeuralNexus API key (`sk-...`)
- Folder to share (default suggested when found)

## Implemented

- Outbound relay to API (default, no Cloudflare)
- Optional Cloudflare tunnel (`configure --connection-mode tunnel`)
- Bearer device auth on local `/mcp`
- SSE discovery at `/discovery` (local/tunnel modes)

API-side `WSS /mcp/relay` and `POST /mcp/*` still needed in Anubis.
