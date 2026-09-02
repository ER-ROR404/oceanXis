#!/usr/bin/env python3
"""Report dataset verification status from config/datasets.yaml.

Read-only tool. Does NOT call Copernicus. Reflects the RULE 7 hard gate:
every dataset entry stays `verified: false` until a live `copernicusmarine.describe()`
confirms the dataset_id and the registry is updated (docs/04-data/dataset-registry.md).

Referenced by `make verify-datasets`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    datasets_path = ROOT / "config" / "datasets.yaml"
    data = yaml.safe_load(datasets_path.read_text())
    entries = data.get("entries", {})
    print(f"{'Variable':<18} {'Role':<16} {'Candidates':<8} {'Verified'}")
    print("-" * 70)
    all_verified = True
    for var, info in entries.items():
        verified = bool(info.get("verified"))
        all_verified &= verified
        print(
            f"{var:<18} {info.get('role', '?'):<16} "
            f"{len(info.get('candidates', [])):<8} {'YES' if verified else 'NO'}"
        )
    print("-" * 70)
    if all_verified:
        print("All datasets verified (registry populated).")
        return 0
    print(
        "Some datasets are UNVERIFIED. Run the copernicusmarine.describe() proof "
        "(docs/04-data/dataset-registry.md) and update config/datasets.yaml + "
        "docs/04-data/dataset-registry.md together (RULE 7)."
    )
    return 0 if "--check" not in sys.argv else (0 if all_verified else 1)


if __name__ == "__main__":
    raise SystemExit(main())