#!/usr/bin/env bash
# OceanEmbed — deploy approved release to production.
# NOTE: pre-build stage — production hardening lands in the coding phase.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Production deployment is not enabled yet (pre-build stage)." >&2
echo "See docs/07-operations/deployment.md and infrastructure/terraform." >&2
exit 1