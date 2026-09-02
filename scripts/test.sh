#!/usr/bin/env bash
# OceanEmbed — run local module tests (backend + ml + data-engineering).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec pytest "$@"