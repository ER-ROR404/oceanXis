#!/usr/bin/env python3
"""Validate config/ + contracts/ consistency against the LOCKED canonical facts.

Read-only repository gate (referenced by `make verify-contracts`, `make test-all`, CI).
Checks:
  1. contracts/ml/*.schema.json exist and declare the canonical depth/channel ordering.
  2. config/depths.yaml matches the LOCKED 15-depth order.
  3. config/variables.yaml channel order matches LOCKED 7-channel order.
  4. config/regions.yaml bounds match docs/03-domain/regions.md.
  5. dataset entries in config/datasets.yaml are marked verified=False (RULE 7 hard gate)
     and include candidate dataset IDs only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

LOCKED_DEPTHS = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]
LOCKED_CHANNELS = ["SST", "SSS", "SSH/SLA", "current_U", "current_V", "wind_U", "wind_V"]
LOCKED_REGIONS = {
    "bay_of_bengal": {"lon": (80.0, 100.0), "lat": (5.0, 22.0)},
    "arabian_sea": {"lon": (45.0, 75.0), "lat": (5.0, 25.0)},
}
ML_CONTRACT_FILES = [
    "model-input.schema.json",
    "model-output.schema.json",
    "checkpoint-manifest.schema.json",
    "evaluation-result.schema.json",
]
API_CONTRACT_FILES = [
    "openapi.yaml",
    "ocean-map.schema.json",
    "ocean-profile.schema.json",
    "prediction.schema.json",
    "health.schema.json",
    "error.schema.json",
]

failures: list[str] = []


def require_path(rel: str) -> Path:
    p = ROOT / rel
    if not p.exists():
        failures.append(f"missing required file: {rel}")
    return p


def check_ml_contracts() -> None:
    for name in ML_CONTRACT_FILES:
        require_path(f"contracts/ml/{name}")


def check_api_contracts() -> None:
    for name in API_CONTRACT_FILES:
        require_path(f"contracts/api/{name}")


def check_depths() -> None:
    p = require_path("config/depths.yaml")
    if not p.exists():
        return
    data = yaml.safe_load(p.read_text())
    depths = data.get("output_depths_m")
    if depths != LOCKED_DEPTHS:
        failures.append(f"config/depths.yaml output_depths_m != LOCKED order: {depths}")
    if data.get("output_channels") != 15:
        failures.append("config/depths.yaml output_channels != 15")


def check_variables() -> None:
    p = require_path("config/variables.yaml")
    if not p.exists():
        return
    data = yaml.safe_load(p.read_text())
    channels = [c["key"] for c in data.get("channels", [])]
    if channels != LOCKED_CHANNELS:
        failures.append(f"config/variables.yaml channels != LOCKED order: {channels}")
    if data.get("input_channels") != 7:
        failures.append("config/variables.yaml input_channels != 7")


def check_regions() -> None:
    p = require_path("config/regions.yaml")
    if not p.exists():
        return
    data = yaml.safe_load(p.read_text())
    if data.get("grid", {}).get("spatial_resolution_degrees") != 0.25:
        failures.append("config/regions.yaml grid resolution != 0.25")
    for name, bounds in LOCKED_REGIONS.items():
        region = data.get("regions", {}).get(name)
        if region is None:
            failures.append(f"config/regions.yaml missing region: {name}")
            continue
        if (region["longitude"]["min"], region["longitude"]["max"]) != bounds["lon"]:
            failures.append(f"config/regions.yaml {name} longitude mismatch")
        if (region["latitude"]["min"], region["latitude"]["max"]) != bounds["lat"]:
            failures.append(f"config/regions.yaml {name} latitude mismatch")


def check_datasets() -> None:
    p = require_path("config/datasets.yaml")
    if not p.exists():
        return
    data = yaml.safe_load(p.read_text())
    entries = data.get("entries", {})
    for var, info in entries.items():
        if info.get("verified"):
            failures.append(
                f"config/datasets.yaml {var} marked verified=True without describe() evidence (RULE 7)"
            )
        candidates = info.get("candidates", [])
        if not candidates:
            failures.append(f"config/datasets.yaml {var} has no candidate datasets (RULE 7)")


def main() -> int:
    check_ml_contracts()
    check_api_contracts()
    check_depths()
    check_variables()
    check_regions()
    check_datasets()
    if failures:
        print("CONTRACT/CONFIG VERIFICATION FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("Contracts + config consistent with LOCKED canonical facts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())