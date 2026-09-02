#!/usr/bin/env bash
# OceanEmbed — developer setup: symlink git hooks, install env, sanity-check.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "No .venv yet — running scripts/bootstrap.sh"
  bash scripts/bootstrap.sh
fi

python scripts/verify-environment.py
echo "==> Developer setup OK."