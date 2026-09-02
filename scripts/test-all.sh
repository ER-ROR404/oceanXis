#!/usr/bin/env bash
# OceanEmbed — full test + lint + contract verification gate.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Lint"
make lint

echo "==> Tests (backend + ml + data-engineering)"
make test

echo "==> Contract/config verification"
python scripts/verify-contracts.py

echo "==> All gates passed."