#!/usr/bin/env bash
# OceanEmbed — start the local stack (backend + frontend + dependencies).
# WARNING: requires a validated .env (Copernicus credentials) and verified datasets.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example and fill in Copernicus credentials first." >&2
  exit 1
fi

python scripts/verify-environment.py
docker compose -f docker-compose.yml up --build