<div align="center">

# codex-pool

**Self-hosted Codex CLI proxy pool with a web admin — one port for management, API, and `/v1` forwarding.**

[中文文档](./README.zh-CN.md) · [Report a bug](https://github.com/Youlixiya/codex-pool/issues) · [Discussions](https://github.com/Youlixiya/codex-pool/discussions)

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

</div>

---

## Why codex-pool?

[Codex CLI](https://github.com/openai/codex) talks to upstream models through a configurable `base_url`. **codex-pool** sits in the middle: you manage upstream accounts and API keys in a browser, while developers point Codex at a single local endpoint. The proxy handles **routing, failover, usage metering, and billing estimates**.

Ideal for individuals and small teams who want a lightweight account pool without operating a full API gateway stack.

## Features

| Area | What you get |
|------|----------------|
| **Single process** | Admin UI, REST API, and OpenAI-compatible `/v1` proxy on one port |
| **Multi-tenant** | Per-user registration, upstream pools, and API keys |
| **Upstream pool** | Multiple accounts per user; automatic failover on errors |
| **Usage & billing** | Token usage and cost estimates (`BILLING_*`) |
| **ChatGPT OAuth** | Browser-based upstream authorization (PKCE, same flow as Codex CLI) |
| **Quota dashboard** | 5-hour / weekly limits from ChatGPT usage API |
| **Local data** | Default data directory `~/.codex-pool/` (database and OAuth tokens) |
| **Small VPS friendly** | Runs comfortably on 2 vCPU / 2 GB RAM |

## Routes

| Path | Purpose |
|------|---------|
| `/` | Vue admin (requires `web/dist`) |
| `/api/v1/*` | Auth, upstreams, API keys, dashboard |
| `/v1/*` | Codex CLI proxy (OpenAI-compatible) |
| `/healthz` | Health check |

## Quick start

**Requirements:** Python 3.12+, [uv](https://github.com/astral-sh/uv), Node.js 18+ (build frontend once).

```bash
git clone https://github.com/Youlixiya/codex-pool.git
cd codex-pool

uv sync
cp .env.example .env
# Edit JWT_SECRET, ADMIN_PASSWORD, CORS_ORIGINS

cd web && npm install && npm run build && cd ..

uv run codex-pool-admin --reload --port 8790
```

Open **http://127.0.0.1:8790** — sign in with the admin account from `.env`, or **Register** a new user.

### Frontend dev (optional)

```bash
# Terminal 1
uv run codex-pool-admin --reload --port 8790

# Terminal 2 — Vite HMR, proxies /api and /v1 to 8790
cd web && npm run dev
```

Visit **http://127.0.0.1:5173** for hot reload.

## Codex CLI

Add to `~/.codex/config.toml`:

```toml
model = "gpt-5.3-codex"
model_provider = "codex-pool"

[model_providers.codex-pool]
name = "OpenAI"
base_url = "http://127.0.0.1:8790/v1"
wire_api = "responses"
env_key = "CODEX_POOL_API_KEY"
```

```bash
export CODEX_POOL_API_KEY="sk-cp-<key-from-admin-console>"
codex
```

Verify:

```bash
curl http://127.0.0.1:8790/healthz
curl -H "Authorization: Bearer sk-cp-<your-key>" http://127.0.0.1:8790/v1/models
```

## Production deployment

On a Linux VPS (example: 2 vCPU / 2 GB):

```bash
git clone https://github.com/Youlixiya/codex-pool.git && cd codex-pool
uv sync
cp .env.example .env
# Set JWT_SECRET, ADMIN_PASSWORD, CORS_ORIGINS=https://your-domain

cd web && npm install && npm run build && cd ..

uv run codex-pool-admin --host 0.0.0.0 --port 8790 --log-level info
```

- **Data directory:** `~/.codex-pool/` (`codex_pool.db`, `auth/` for OAuth tokens)
- **systemd:** see [scripts/codex-pool.service.example](./scripts/codex-pool.service.example)
- Put **Nginx / Caddy** in front for TLS; bind `--port 80` only if you accept running as root

## Configuration (`.env`)

Copy from [`.env.example`](./.env.example). Do not commit `.env`.

| Variable | Description |
|----------|-------------|
| `JWT_SECRET` | Signs admin session tokens |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Bootstrap admin (created on first start) |
| `CORS_ORIGINS` | Allowed origins for the admin UI |
| `DATABASE_URL` | Optional; default `~/.codex-pool/codex_pool.db` |
| `BILLING_*` | Per-million-token prices; usage and cost tracking |
| `CHATGPT_*` | OAuth callback port and auth directory |
| `WEB_DIST` | Override path to built frontend |

## ChatGPT OAuth upstream

1. Admin → **Upstreams** → type **chatgpt (OAuth)** → **Open browser authorization**
2. PKCE flow; tokens saved under `~/.codex-pool/auth/<name>.json`
3. **Port 1455** must be free on the machine running authorization (configurable via `CHATGPT_OAUTH_CALLBACK_PORT`)

## Contributing

Issues and PRs are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

[MIT](./LICENSE) © contributors
