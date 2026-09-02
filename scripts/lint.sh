#!/usr/bin/env bash
# OceanEmbed — run repository-wide linting and formatting checks.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> ruff check"
ruff check backend ml data-engineering scripts
echo "==> ruff format --check"
ruff format --check backend ml data-engineering scripts
echo "==> OK"