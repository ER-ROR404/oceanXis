#!/usr/bin/env bash
# OceanEmbed — deploy current build to staging.
# NOTE: pre-build stage — infrastructure/terraform + CI release pipeline land in the coding phase.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d infrastructure/terraform/environments/staging ]]; then
  echo "Staging terraform not yet provisioned (pre-build stage)." >&2
  echo "See docs/07-operations/deployment.md for the intended flow." >&2
  exit 1
fi