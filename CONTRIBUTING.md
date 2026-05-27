# Contributing

Thanks for your interest in codex-pool.

## Development setup

```bash
uv sync
cp .env.example .env
cd web && npm install && npm run build && cd ..
uv run codex-pool-admin --reload --port 8790
```

## Pull requests

1. Open an issue for large changes when possible.
2. Keep PRs focused; match existing code style.
3. Do not commit `.env`, credentials, or `web/dist/`.

## Reporting issues

Include: OS, Python version, how you run the server, relevant `.env` keys (redact secrets), and logs or curl examples.
