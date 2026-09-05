#!/usr/bin/env python3
"""Historical download: chunked bounded-period downloads to data/processed/.

Per Phase 2 of the implementation plan, downloads 1–2 years of data for each
surface input + GLORYS target, chunked by year to manage volume and network.

Usage:
    python scripts/download_historical.py --region bay_of_bengal --start 2024-01-01 --end 2024-12-31
    python scripts/download_historical.py --region bay_of_bengal --start 2023-01-01 --end 2024-12-31

Output structure:
    data/processed/{region}/{variable}/{dataset_id}_{variable}_{date_range}.nc
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "data-engineering" / "src"))

from oceanembed_data.catalog import (
    DatasetCatalog,
    CANONICAL_INPUT_CHANNELS,
    GLORYS_DOWNLOAD_MAX_DEPTH_M,
)
from oceanembed_data.copernicus import CopernicusClient
from oceanembed_data.regions import RegionRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("download_historical")

# Default output directory
DEFAULT_OUTPUT_DIR = Path("data/processed")


def date_range_chunks(
    start: str, end: str, chunk_months: int = 3
) -> list[tuple[str, str]]:
    """Split a date range into chunks of N months.

    Args:
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).
        chunk_months: Months per chunk (default 3 = quarterly).

    Returns:
        List of (start, end) date string pairs.
    """
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    chunks = []
    current = start_dt

    while current <= end_dt:
        chunk_end = min(
            current + timedelta(days=chunk_months * 30) - timedelta(days=1),
            end_dt,
        )
        chunks.append((current.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        current = chunk_end + timedelta(days=1)

    return chunks


def download_dataset(
    client: CopernicusClient,
    catalog_entry,
    region_bounds,
    start_date: str,
    end_date: str,
    output_dir: Path,
    chunk_months: int = 3,
) -> list[dict]:
    """Download a single dataset in chunks.

    Args:
        client: Copernicus client.
        catalog_entry: DatasetEntry from the catalog.
        region_bounds: RegionBounds for subsetting.
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).
        output_dir: Base output directory.
        chunk_months: Months per download chunk.

    Returns:
        List of download result dicts.
    """
    chunks = date_range_chunks(start_date, end_date, chunk_months)
    results = []

    # Build output subdirectory
    var_dir = output_dir / catalog_entry.name
    var_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Downloading %s (%s) — %d chunks from %s to %s",
        catalog_entry.name,
        catalog_entry.dataset_id,
        len(chunks),
        start_date,
        end_date,
    )

    for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
        logger.info("  Chunk %d/%d: %s → %s", i, len(chunks), chunk_start, chunk_end)

        result = client.subset(
            dataset_id=catalog_entry.dataset_id,
            variable=catalog_entry.variable,
            region_bounds=region_bounds,
            start_date=chunk_start,
            end_date=chunk_end,
            output_dir=str(var_dir),
        )

        if result.success:
            logger.info("    ✓ Downloaded: %s", result.output_path)
        else:
            logger.error("    ✗ Failed: %s", result.error)

        results.append({
            "variable": catalog_entry.name,
            "dataset_id": catalog_entry.dataset_id,
            "chunk_start": chunk_start,
            "chunk_end": chunk_end,
            "success": result.success,
            "output_path": str(result.output_path) if result.output_path else None,
            "error": result.error,
        })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Download historical Copernicus Marine data in chunks."
    )
    parser.add_argument(
        "--region",
        required=True,
        help="Region ID (e.g. bay_of_bengal, arabian_sea)",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory (default: data/processed)",
    )
    parser.add_argument(
        "--chunk-months",
        type=int,
        default=3,
        help="Months per download chunk (default: 3)",
    )
    parser.add_argument(
        "--skip-inputs",
        action="store_true",
        help="Skip surface input downloads (re-download GLORYS only)",
    )
    parser.add_argument(
        "--skip-glorys",
        action="store_true",
        help="Skip GLORYS target download",
    )
    parser.add_argument(
        "--skip-argo",
        action="store_true",
        help="Skip ARGO validation download",
    )

    args = parser.parse_args()

    # Load config
    catalog = DatasetCatalog.from_yaml(_project_root / "config" / "datasets.yaml")
    registry = RegionRegistry.from_yaml(_project_root / "config" / "regions.yaml")
    region = registry.get(args.region)
    logger.info("Region: %s", region)

    # Connect to Copernicus
    client = CopernicusClient.from_env()

    # Output directory
    output_dir = Path(args.output_dir) / args.region
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download all inputs
    all_results = []
    if not args.skip_inputs:
        for channel in CANONICAL_INPUT_CHANNELS:
            entry = catalog.entries.get(channel)
            if entry is None:
                logger.warning("Channel '%s' not in catalog — skipping", channel)
                continue

            results = download_dataset(
                client=client,
                catalog_entry=entry,
                region_bounds=region,
                start_date=args.start,
                end_date=args.end,
                output_dir=output_dir,
                chunk_months=args.chunk_months,
            )
            all_results.extend(results)

    # Download GLORYS target
    if not args.skip_glorys:
        glorys = catalog.training_target()
        # GLORYS needs depth range
        glorys_dir = output_dir / "glorys_temperature"
        glorys_dir.mkdir(parents=True, exist_ok=True)

        chunks = date_range_chunks(args.start, args.end, args.chunk_months)
        for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
            logger.info(
                "GLORYS chunk %d/%d: %s → %s", i, len(chunks), chunk_start, chunk_end
            )
            result = client.subset(
                dataset_id=glorys.dataset_id,
                variable=glorys.variable,
                region_bounds=region,
                start_date=chunk_start,
                end_date=chunk_end,
                minimum_depth=0.0,
                maximum_depth=GLORYS_DOWNLOAD_MAX_DEPTH_M,
                output_dir=str(glorys_dir),
            )
            if result.success:
                logger.info("  ✓ Downloaded: %s", result.output_path)
            else:
                logger.error("  ✗ Failed: %s", result.error)

            all_results.append({
                "variable": "glorys_temperature",
                "dataset_id": glorys.dataset_id,
                "chunk_start": chunk_start,
                "chunk_end": chunk_end,
                "success": result.success,
                "output_path": str(result.output_path) if result.output_path else None,
                "error": result.error,
            })

    # Summary
    succeeded = sum(1 for r in all_results if r["success"])
    failed = sum(1 for r in all_results if not r["success"])
    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE: %d succeeded, %d failed", succeeded, failed)
    if failed > 0:
        logger.warning("Failed downloads:")
        for r in all_results:
            if not r["success"]:
                logger.warning("  %s [%s→%s]: %s", r["variable"], r["chunk_start"], r["chunk_end"], r["error"])
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
