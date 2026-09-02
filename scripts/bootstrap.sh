#!/usr/bin/env bash
# OceanEmbed — initial dev-environment bootstrap.
# Creates the three logical Python environments and installs module deps.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v uv >/dev/null 2>&1 || { echo "uv is required (https://docs.astral.sh/uv)." >&2; exit 1; }

uv python install 3.11
uv venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
uv pip install -e . \
  -e backend \
  -e ml \
  -e data-engineering

echo "==> Dev environment ready. Activate: source .venv/bin/activate"