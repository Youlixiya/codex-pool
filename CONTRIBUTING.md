# Contributing

Thanks for your interest in codex-pool.

## Development setup

```bash
uv sync
cp .env.example .env
uv run codex-pool-admin --reload --port 8790
```

The repo ships a pre-built admin UI in `web/dist`. To work on the frontend:

```bash
cd web && npm install && npm run dev   # http://127.0.0.1:5173
# After UI changes:
npm run build
```

## Pull requests

1. Open an issue for large changes when possible.
2. Keep PRs focused; match existing code style.
3. Do not commit `.env` or credentials.
4. If you change `web/`, run `npm run build` and include updated `web/dist/` in the PR.

## Reporting issues

Include: OS, Python version, how you run the server, relevant `.env` keys (redact secrets), and logs or curl examples.
