#!/usr/bin/env bash
# One-shot production deploy: build frontend in Docker, start MySQL + Redis + app.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f .env.prod.example ]]; then
    cp .env.prod.example "$ENV_FILE"
    echo "Created $ENV_FILE from .env.prod.example"
    echo "Edit $ENV_FILE (JWT_SECRET, passwords, PUBLIC_URL) then re-run this script."
    exit 1
  fi
  echo "Missing $ENV_FILE — copy .env.prod.example first." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

for var in MYSQL_ROOT_PASSWORD MYSQL_PASSWORD JWT_SECRET ADMIN_PASSWORD; do
  case "${!var:-}" in
    change-me*|""|"YOUR_"*)
      echo "Set $var in $ENV_FILE before deploying." >&2
      exit 1
      ;;
  esac
done

if [[ "${PUBLIC_URL:-}" == *"example.com"* ]] || [[ "${PUBLIC_URL:-}" == *"YOUR_"* ]]; then
  echo "Set PUBLIC_URL and CORS_ORIGINS in $ENV_FILE to your domain or IP (e.g. http://pool.example.com)." >&2
  exit 1
fi

if [[ "${APP_HTTP_PORT:-80}" == "80" ]] && command -v ss >/dev/null 2>&1; then
  if ss -tln | grep -q ':80 '; then
    echo "Warning: host port 80 is already in use. Stop the other service or set APP_HTTP_PORT in $ENV_FILE." >&2
  fi
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed." >&2
  exit 1
fi

COMPOSE=(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE")

echo "==> Building and starting production stack..."
"${COMPOSE[@]}" build --pull
"${COMPOSE[@]}" up -d

echo ""
echo "==> Waiting for app health..."
for _ in $(seq 1 60); do
  if "${COMPOSE[@]}" ps --status running app 2>/dev/null | grep -q healthy; then
    break
  fi
  if curl -sf "http://127.0.0.1:${APP_HTTP_PORT:-80}/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

PORT="${APP_HTTP_PORT:-80}"
echo ""
echo "Deployed."
echo "  Admin + API + Codex proxy: ${PUBLIC_URL:-http://127.0.0.1:$PORT}"
echo "  Health:                    http://127.0.0.1:$PORT/healthz"
echo "  Admin user:                ${ADMIN_USERNAME:-admin}"
echo ""
echo "Logs:  ${COMPOSE[*]} logs -f app"
echo "Stop:  ${COMPOSE[*]} down"
