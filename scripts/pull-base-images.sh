#!/usr/bin/env bash
set -euo pipefail

# Pull base images before `docker compose build`.
# Tries docker.io first, then docker.1ms.run mirror (common in CN).

images=(
  "python:3.12-slim"
  "node:22-alpine"
  "nginx:alpine"
)

pull_one() {
  local img="$1"
  echo "==> pulling ${img}"
  if docker pull "${img}"; then
    return 0
  fi
  local name="${img#*/}"
  local mirror="docker.1ms.run/library/${name}"
  echo "    retry via ${mirror}"
  docker pull "${mirror}"
  docker tag "${mirror}" "${img}"
}

for img in "${images[@]}"; do
  pull_one "${img}" || {
    echo "FAILED: ${img}" >&2
    echo "Fix Docker registry mirror in Docker Desktop, or set in .env.docker:" >&2
    echo "  PYTHON_BASE_IMAGE=docker.1ms.run/library/python:3.12-slim" >&2
    exit 1
  }
done

echo "All base images ready."
