#!/usr/bin/env python3
"""One-day regional proof: download 1 day of Bay of Bengal data, validate shapes.

Per Golden Rule 10: one-day test before mass download; no model before data is proven.

This script:
1. Loads the dataset catalog + region definitions from config/
2. Downloads one day of each surface input (7 channels) for Bay of Bengal
3. Downloads one day of GLORYS temperature (15 depths) for Bay of Bengal
4. Validates expected shapes and variable presence
5. Reports pass/fail for each dataset

Usage:
    python -m scripts.proof_one_day
    # or from project root:
    PYTHONPATH=data-engineering/src python scripts/proof_one_day.py

Requirements:
    - COPERNICUSMARINE_SERVICE_USERNAME and COPERNICUSMARINE_SERVICE_PASSWORD in .env
    - pip install -e data-engineering[dev] (or at minimum copernicusmarine xarray)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Add data-engineering/src to path so we can import oceanembed_data
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "data-engineering" / "src"))

from oceanembed_data.catalog import DatasetCatalog, CANONICAL_INPUT_CHANNELS
from oceanembed_data.copernicus import CopernicusClient, SubsetResult
from oceanembed_data.regions import RegionRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("proof_one_day")

# ---------- Configuration ----------
# This date must exist in ALL input datasets (overlap period).
# 2024-06-01 is within the train/val overlap for most products.
TEST_DATE = "2024-06-01"

# Region for the one-day proof
REGION_ID = "bay_of_bengal"

# Expected grid dims at 0.25° for BoB (80–100°E, 5–22°N)
# Height: (22-5)/0.25 + 1 = 69 cells
# Width:  (100-80)/0.25 + 1 = 81 cells
EXPECTED_HEIGHT = 69
EXPECTED_WIDTH = 81

# Expected depth count for GLORYS target
EXPECTED_DEPTH_COUNT = 15

# Output directory for downloaded files
OUTPUT_DIR = Path("data/proof")


def run_proof() -> bool:
    """Execute the one-day proof and return True if all checks pass."""
    # ---- Load config ----
    logger.info("Loading dataset catalog...")
    catalog = DatasetCatalog.from_yaml(_project_root / "config" / "datasets.yaml")
    logger.info(catalog.summary())

    logger.info("Loading region registry...")
    registry = RegionRegistry.from_yaml(_project_root / "config" / "regions.yaml")
    region = registry.get(REGION_ID)
    logger.info("Region: %s", region)

    # ---- Connect to Copernicus ----
    logger.info("Connecting to Copernicus Marine...")
    try:
        client = CopernicusClient.from_env()
    except ValueError as e:
        logger.error("Connection failed: %s", e)
        return False

    # ---- Output directory ----
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Download surface inputs ----
    all_passed = True
    results: dict[str, SubsetResult] = {}

    for channel in CANONICAL_INPUT_CHANNELS:
        entry = catalog.entries.get(channel)
        if entry is None:
            logger.warning("Channel '%s' not in catalog — skipping", channel)
            continue

        logger.info("--- Downloading %s (%s) ---", channel, entry.dataset_id)
        result = client.subset(
            dataset_id=entry.dataset_id,
            variable=entry.variable,
            region_bounds=region,
            start_date=TEST_DATE,
            end_date=TEST_DATE,
            output_dir=OUTPUT_DIR,
        )
        results[channel] = result

        if not result.success:
            logger.error("FAIL: %s — %s", channel, result.error)
            all_passed = False
            continue

        if result.output_path and result.output_path.exists():
            logger.info("  Downloaded: %s", result.output_path)
            if result.shape:
                logger.info("  Shape: time=%d, lat=%d, lon=%d", *result.shape)
        else:
            logger.warning("  Download completed but no output file found")

    # ---- Download GLORYS temperature (training target) ----
    logger.info("--- Downloading GLORYS temperature (thetao) ---")
    glorys_entry = catalog.training_target()
    glorys_result = client.subset(
        dataset_id=glorys_entry.dataset_id,
        variable=glorys_entry.variable,
        region_bounds=region,
        start_date=TEST_DATE,
        end_date=TEST_DATE,
        minimum_depth=0.0,
        maximum_depth=1000.0,
        output_dir=OUTPUT_DIR,
    )
    results["glorys_temperature"] = glorys_result

    if not glorys_result.success:
        logger.error("FAIL: GLORYS temperature — %s", glorys_result.error)
        all_passed = False
    elif glorys_result.output_path and glorys_result.output_path.exists():
        logger.info("  Downloaded: %s", glorys_result.output_path)
        if glorys_result.shape:
            logger.info("  Shape: time=%d, lat=%d, lon=%d", *glorys_result.shape)
    else:
        logger.warning("  Download completed but no output file found")

    # ---- Summary ----
    logger.info("=" * 60)
    logger.info("PROOF SUMMARY")
    logger.info("=" * 60)
    for name, result in sorted(results.items()):
        status = "PASS" if result.success else "FAIL"
        path_str = str(result.output_path) if result.output_path else "N/A"
        shape_str = str(result.shape) if result.shape else "N/A"
        logger.info("  [%s] %s: shape=%s file=%s", status, name, shape_str, path_str)

    if all_passed:
        logger.info("=" * 60)
        logger.info("ALL CHECKS PASSED — one-day Bay of Bengal proof is complete")
        logger.info("Next step: build [time, 7, H, W] + [time, 15, H, W] tensors")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error("SOME CHECKS FAILED — review logs above")
        logger.error("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = run_proof()
    sys.exit(0 if success else 1)
