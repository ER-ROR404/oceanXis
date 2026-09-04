#!/usr/bin/env python3
"""Generate dataset manifest: JSON metadata for built training datasets.

Creates a manifest file describing the dataset version, sources, dates,
normalization stats, and file locations. Per contracts/data/dataset-metadata.schema.json.

Usage:
    python scripts/generate_manifest.py --region bay_of_bengal --tensor-dir data/tensors/bay_of_bengal
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "data-engineering" / "src"))

from oceanembed_data.catalog import DatasetCatalog, CANONICAL_INPUT_CHANNELS
from oceanembed_data.regions import RegionRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("generate_manifest")


def file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_sha256(dir_path: Path) -> str:
    """Compute SHA-256 hash of all files in a directory."""
    h = hashlib.sha256()
    for f in sorted(dir_path.rglob("*")):
        if f.is_file():
            h.update(f.name.encode())
            h.update(file_sha256(f).encode())
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Generate dataset manifest.")
    parser.add_argument("--region", required=True, help="Region ID")
    parser.add_argument(
        "--tensor-dir",
        required=True,
        help="Path to built tensor directory",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Manifest output path (default: {tensor_dir}/manifest.json)",
    )

    args = parser.parse_args()

    tensor_dir = Path(args.tensor_dir)
    if not tensor_dir.exists():
        logger.error("Tensor directory not found: %s", tensor_dir)
        sys.exit(1)

    # Load catalog and region info
    catalog = DatasetCatalog.from_yaml(_project_root / "config" / "datasets.yaml")
    registry = RegionRegistry.from_yaml(_project_root / "config" / "regions.yaml")
    region = registry.get(args.region)

    # Load normalization stats if available
    norm_stats_path = tensor_dir / "normalization_stats.json"
    norm_stats = {}
    if norm_stats_path.exists():
        with open(norm_stats_path) as f:
            norm_stats = json.load(f)

    # Compute hashes
    hashes = {}
    for name in ["X.zarr", "Y.zarr", "mask.zarr", "training_dataset.nc"]:
        p = tensor_dir / name
        if p.exists():
            if p.is_dir():
                hashes[name] = dir_sha256(p)
            else:
                hashes[name] = file_sha256(p)

    # Build source entries
    sources = []
    for channel in CANONICAL_INPUT_CHANNELS:
        entry = catalog.entries.get(channel)
        if entry:
            sources.append({
                "variable": channel,
                "dataset_id": entry.dataset_id,
                "source": entry.source,
                "variable_name": entry.variable,
                "verified": entry.is_verified,
            })

    # GLORYS target
    glorys = catalog.training_target()
    sources.append({
        "variable": "glorys_temperature",
        "dataset_id": glorys.dataset_id,
        "source": glorys.source,
        "variable_name": glorys.variable,
        "verified": glorys.is_verified,
    })

    # Build manifest
    manifest = {
        "schema_version": "1.0.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "region": args.region,
        "region_bounds": {
            "lat_min": region.lat_min,
            "lat_max": region.lat_max,
            "lon_min": region.lon_min,
            "lon_max": region.lon_max,
        },
        "grid": {
            "resolution_degrees": 0.25,
            "latitude_count": 0,  # filled below
            "longitude_count": 0,
        },
        "sources": sources,
        "split_policy": {
            "method": "temporal_locked",
            "train": "2018-01-01..2023-12-31",
            "validation": "2024-01-01..2024-12-31",
            "test": "2025-01-01..2025-12-31",
        },
        "normalization": {
            "method": "zscore_per_channel",
            "statistics_source": "training_data_only",
            "statistics": norm_stats,
        },
        "files": hashes,
        "provenance": {
            "tool": "oceanembed-data",
            "version": "0.1.0",
            "harmonization": "linear_interpolation_to_0.25deg",
            "depth_selection": "nearest_neighbor_to_15_canonical_depths",
        },
    }

    # Try to read grid dimensions from tensor files
    try:
        import xarray as xr

        for name in ["X.zarr", "training_dataset.nc"]:
            p = tensor_dir / name
            if p.exists():
                ds = xr.open_dataset(p) if p.is_file() else xr.open_zarr(str(p))
                lat_dim = [d for d in ds.dims if d in ("latitude", "lat")]
                lon_dim = [d for d in ds.dims if d in ("longitude", "lon")]
                if lat_dim and lon_dim:
                    manifest["grid"]["latitude_count"] = ds.sizes[lat_dim[0]]
                    manifest["grid"]["longitude_count"] = ds.sizes[lon_dim[0]]
                ds.close()
                break
    except Exception as e:
        logger.warning("Could not read grid dimensions: %s", e)

    # Write manifest
    output_path = Path(args.output) if args.output else tensor_dir / "manifest.json"
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    logger.info("Manifest written to %s", output_path)
    logger.info("Sources: %d datasets", len(sources))
    logger.info("Files: %d hashes computed", len(hashes))


if __name__ == "__main__":
    main()
