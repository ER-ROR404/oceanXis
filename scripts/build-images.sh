#!/usr/bin/env bash
# OceanEmbed — build application Docker images.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Build order mirrors infrastructure/docker (backend, ml-inference, frontend).
docker build -f infrastructure/docker/backend.Dockerfile -t oceanembed-backend:local . "$@"
echo "==> Images built (backend). ml-inference/frontend follow the same pattern."