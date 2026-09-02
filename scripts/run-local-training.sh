#!/usr/bin/env bash
# OceanEmbed — run a small reproducible local training experiment.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d data/processed ]]; then
  echo "No processed training data found. Build the one-day regional dataset first:" >&2
  echo "  python data-engineering/scripts/download_region.py --help" >&2
  echo "(see docs/04-data/preprocessing-pipeline.md)" >&2
  exit 1
fi
python ml/scripts/train.py --config ml/configs/baseline.yaml "$@"