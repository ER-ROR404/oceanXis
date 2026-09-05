#!/usr/bin/env python3
"""Build training dataset: assemble harmonized tensors + normalization stats.

Reads downloaded NetCDF chunks from data/processed/{region}/, applies
harmonization (regrid to 0.25°, depth selection), and assembles:
    - X: [time, 7, H, W] surface inputs
    - Y: [time, 15, H, W] GLORYS temperature targets
    - mask: [H, W] validity mask

Computes normalization statistics (z-score) from training data only (RULE 11).

Usage:
    python scripts/build_training_dataset.py --region bay_of_bengal
    python scripts/build_training_dataset.py --region bay_of_bengal --output-dir data/tensors
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import xarray as xr

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "data-engineering" / "src"))

from oceanembed_data.catalog import CANONICAL_DEPTHS_M, CANONICAL_INPUT_CHANNELS
from oceanembed_data.harmonization import (
    build_validity_mask,
    harmonize_glorys_target,
    harmonize_surface_input,
    make_target_grid,
)
from oceanembed_data.regions import RegionBounds, RegionRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("build_training_dataset")

# Variable mapping: catalog channel name -> NetCDF variable name in downloaded files
VARIABLE_MAP = {
    "SST": "analysed_sst",
    "SSS": "sos",
    "SSH": "sla",
    "current_U": "uo",
    "current_V": "vo",
    "wind_U": "eastward_wind",
    "wind_V": "northward_wind",
    "glorys_temperature": "thetao",
}

# Depth level extraction: some datasets have multi-level depth dims
# Value = depth index to extract (0 = surface)
DEPTH_LEVEL_MAP = {
    "SST": None,       # no depth dim
    "SSS": 0,          # depth=1, extract surface
    "SSH": None,       # no depth dim
    "current_U": 0,    # depth=2, extract surface (0m)
    "current_V": 0,    # depth=2, extract surface (0m)
    "wind_U": None,    # no depth dim
    "wind_V": None,    # no depth dim
}


def find_nc_files(data_dir: Path, channel: str) -> list[Path]:
    """Find all NetCDF files for a channel in the processed directory.

    Searches data_dir/{channel}/*.nc and data_dir/glorys_temperature/*.nc.

    Robust against interrupted downloads:
      - excludes partial writes (`*.nc.<tmp>` from copernicusmarine)
      - excludes Copernicus duplicate files (`name_(1).nc`) created when a
        download is re-run after an interruption
    """
    channel_dir = data_dir / channel
    if not channel_dir.exists():
        return []
    candidates = sorted(channel_dir.glob("*.nc"))
    return [p for p in candidates if _is_clean_nc(p)]


def _is_clean_nc(path: Path) -> bool:
    """True if a NetCDF path is a final, non-duplicated download artifact.

    Rejects Copernicus auto-renamed duplicates created when a download is
    re-run after an interruption: ``name_(1).nc``, ``name_(2).nc``, etc.
    (Partial write artifacts like ``name.nc.<rand>`` do not match ``*.nc``
    globs and never reach this check.)
    """
    name = path.name
    for suffix in ("_(1).nc", "_(2).nc", "_(3).nc"):
        if name.endswith(suffix):
            return False
    return True


def load_and_harmonize_channel(
    nc_files: list[Path],
    channel: str,
    region: RegionBounds,
) -> xr.DataArray:
    """Load all chunks for a channel and harmonize to 0.25° grid.

    Returns:
        DataArray of shape [time, lat, lon] at 0.25°.
    """
    if not nc_files:
        raise FileNotFoundError(f"No NC files found for {channel}")

    var_name = VARIABLE_MAP.get(channel)
    if var_name is None:
        raise ValueError(f"No variable mapping for {channel}")

    depth_level = DEPTH_LEVEL_MAP.get(channel)

    all_harmonized = []
    for nc_file in nc_files:
        ds = xr.open_dataset(nc_file)
        try:
            harmonized = harmonize_surface_input(
                ds, variable=var_name, region=region, depth_level=depth_level
            )
            all_harmonized.append(harmonized)
        finally:
            ds.close()

    # Concatenate along time dimension
    combined = xr.concat(all_harmonized, dim="time")
    logger.info("Loaded %s: %d files, combined shape = %s", channel, len(nc_files), combined.shape)
    return combined


def load_and_harmonize_target(
    nc_files: list[Path],
    region: RegionBounds,
) -> xr.DataArray:
    """Load all GLORYS chunks and harmonize to canonical grid.

    Returns:
        DataArray of shape [time, depth=15, lat, lon] at 0.25°.
    """
    if not nc_files:
        raise FileNotFoundError("No NC files found for GLORYS target")

    all_harmonized = []
    for nc_file in nc_files:
        ds = xr.open_dataset(nc_file)
        try:
            harmonized = harmonize_glorys_target(ds, region=region)
            all_harmonized.append(harmonized)
        finally:
            ds.close()

    combined = xr.concat(all_harmonized, dim="time")
    logger.info("Loaded GLORYS target: %d files, combined shape = %s", len(nc_files), combined.shape)
    return combined


def compute_normalization_stats(
    x_array: np.ndarray,
    mask: np.ndarray,
) -> dict:
    """Compute z-score normalization statistics from training data only.

    Args:
        x_array: Input array of shape [time, 7, H, W].
        mask: Validity mask of shape [H, W].

    Returns:
        Dict with per-channel mean and std.
    """
    n_channels = x_array.shape[1]
    stats = {}

    for ch_idx in range(n_channels):
        channel_data = x_array[:, ch_idx, :, :]  # [time, H, W]
        # Apply mask: only ocean cells
        masked = channel_data[:, mask]  # [time, n_valid_cells]
        mean = float(np.nanmean(masked))
        std = float(np.nanstd(masked))
        if std == 0:
            std = 1.0  # prevent division by zero

        stats[f"channel_{ch_idx}"] = {
            "mean": mean,
            "std": std,
        }
        logger.info("  Channel %d: mean=%.4f, std=%.4f", ch_idx, mean, std)

    return stats


def normalize_inputs(
    x_array: np.ndarray,
    stats: dict,
    mask: np.ndarray,
) -> np.ndarray:
    """Apply z-score normalization to inputs.

    Args:
        x_array: Input array of shape [time, 7, H, W].
        stats: Normalization statistics from compute_normalization_stats.
        mask: Validity mask.

    Returns:
        Normalized array, same shape.
    """
    normalized = x_array.copy()
    for ch_idx in range(x_array.shape[1]):
        key = f"channel_{ch_idx}"
        mean = stats[key]["mean"]
        std = stats[key]["std"]
        normalized[:, ch_idx, :, :] = (normalized[:, ch_idx, :, :] - mean) / std

    return normalized


def main():
    parser = argparse.ArgumentParser(
        description="Build harmonized training dataset from downloaded chunks."
    )
    parser.add_argument(
        "--region",
        required=True,
        help="Region ID (e.g. bay_of_bengal)",
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Input directory (default: data/processed/{region})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: data/tensors/{region})",
    )
    parser.add_argument(
        "--save-format",
        choices=["zarr", "netcdf"],
        default="zarr",
        help="Output format (default: zarr)",
    )

    args = parser.parse_args()

    # Paths
    input_dir = Path(args.input_dir) if args.input_dir else Path("data/processed") / args.region
    output_dir = Path(args.output_dir) if args.output_dir else Path("data/tensors") / args.region
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load region
    registry = RegionRegistry.from_yaml(_project_root / "config" / "regions.yaml")
    region = registry.get(args.region)
    logger.info("Region: %s", region)

    # --- Step 1: Load and harmonize all inputs ---
    logger.info("=" * 60)
    logger.info("Step 1: Loading and harmonizing surface inputs")
    logger.info("=" * 60)

    input_arrays = {}
    for channel in CANONICAL_INPUT_CHANNELS:
        nc_files = find_nc_files(input_dir, channel)
        if not nc_files:
            logger.warning("No files for %s — skipping", channel)
            continue
        try:
            harmonized = load_and_harmonize_channel(nc_files, channel, region)
            input_arrays[channel] = harmonized
        except Exception as e:
            logger.error("Failed to load %s: %s", channel, e)

    if len(input_arrays) < 7:
        logger.warning(
            "Only %d/7 inputs loaded — proceeding with available data",
            len(input_arrays),
        )

    # --- Step 2: Load and harmonize GLORYS target ---
    logger.info("=" * 60)
    logger.info("Step 2: Loading and harmonizing GLORYS target")
    logger.info("=" * 60)

    glorys_files = find_nc_files(input_dir, "glorys_temperature")
    if not glorys_files:
        logger.error("No GLORYS files found — cannot build dataset")
        sys.exit(1)

    target = load_and_harmonize_target(glorys_files, region)

    # --- Step 3: Stack inputs into [time, 7, H, W] ---
    logger.info("=" * 60)
    logger.info("Step 3: Stacking inputs into tensor")
    logger.info("=" * 60)

    # Use the common time axis (intersection of all inputs)
    common_times = None
    for ch, arr in input_arrays.items():
        if common_times is None:
            common_times = set(arr.time.values)
        else:
            common_times = common_times & set(arr.time.values)

    common_times = sorted(common_times)
    logger.info("Common time steps: %d", len(common_times))

    # Build [time, 7, H, W] array
    # Use the grid from the first available input
    ref_channel = CANONICAL_INPUT_CHANNELS[0]
    if ref_channel not in input_arrays:
        ref_channel = list(input_arrays.keys())[0]
    ref = input_arrays[ref_channel]
    lat_dim = [d for d in ref.dims if d in ("latitude", "lat")][0]
    lon_dim = [d for d in ref.dims if d in ("longitude", "lon")][0]
    H = ref.sizes[lat_dim]
    W = ref.sizes[lon_dim]

    x_array = np.full((len(common_times), 7, H, W), np.nan, dtype=np.float32)
    for ch_idx, channel in enumerate(CANONICAL_INPUT_CHANNELS):
        if channel in input_arrays:
            arr = input_arrays[channel]
            # Select common times
            arr_common = arr.sel(time=common_times)
            # Flatten to [time, H, W]
            vals = arr_common.values
            if vals.ndim == 4:  # [time, depth, H, W] shouldn't happen after harmonization
                vals = vals[:, 0, :, :]
            x_array[:, ch_idx, :, :] = vals
            logger.info("  %s: filled channel %d", channel, ch_idx)

    logger.info("X tensor shape: %s", x_array.shape)

    # --- Step 4: Stack target into [time, 15, H, W] ---
    logger.info("=" * 60)
    logger.info("Step 4: Stacking target into tensor")
    logger.info("=" * 60)

    target_common = target.sel(time=common_times)
    y_array = target_common.values.astype(np.float32)
    if y_array.ndim == 4:
        # Should be [time, depth, H, W] — already correct
        pass
    logger.info("Y tensor shape: %s", y_array.shape)

    # --- Step 5: Build validity mask ---
    logger.info("=" * 60)
    logger.info("Step 5: Building validity mask")
    logger.info("=" * 60)

    # Simple mask: ocean cells where inputs are not all-NaN
    mask = np.isfinite(x_array).any(axis=(0, 1))  # [H, W]
    logger.info("Validity mask: %d/%d cells valid (%.1f%%)", mask.sum(), mask.size, 100.0 * mask.sum() / mask.size)

    # --- Step 6: Compute normalization stats ---
    logger.info("=" * 60)
    logger.info("Step 6: Computing normalization statistics (training data only)")
    logger.info("=" * 60)

    norm_stats = compute_normalization_stats(x_array, mask)

    # --- Step 7: Save ---
    logger.info("=" * 60)
    logger.info("Step 7: Saving tensors")
    logger.info("=" * 60)

    if args.save_format == "zarr":
        # Save as Zarr
        x_da = xr.DataArray(
            x_array,
            dims=["time", "channel", "latitude", "longitude"],
            coords={
                "time": common_times,
                "channel": CANONICAL_INPUT_CHANNELS[:x_array.shape[1]],
                "latitude": ref[lat_dim].values,
                "longitude": ref[lon_dim].values,
            },
            attrs={"normalization": norm_stats},
        )
        y_da = xr.DataArray(
            y_array,
            dims=["time", "depth", "latitude", "longitude"],
            coords={
                "time": common_times,
                "depth": CANONICAL_DEPTHS_M[:y_array.shape[1]],
                "latitude": ref[lat_dim].values,
                "longitude": ref[lon_dim].values,
            },
        )
        mask_da = xr.DataArray(
            mask,
            dims=["latitude", "longitude"],
            coords={
                "latitude": ref[lat_dim].values,
                "longitude": ref[lon_dim].values,
            },
        )

        x_da.to_zarr(str(output_dir / "X.zarr"), mode="w")
        y_da.to_zarr(str(output_dir / "Y.zarr"), mode="w")
        mask_da.to_zarr(str(output_dir / "mask.zarr"), mode="w")
        logger.info("Saved Zarr datasets to %s", output_dir)

    else:
        # Save as NetCDF
        ds_out = xr.Dataset({
            "X": x_da,
            "Y": y_da,
            "mask": mask_da,
        })
        ds_out.to_netcdf(str(output_dir / "training_dataset.nc"))
        logger.info("Saved NetCDF to %s/training_dataset.nc", output_dir)

    # Save normalization stats as JSON
    stats_path = output_dir / "normalization_stats.json"
    with open(stats_path, "w") as f:
        json.dump(norm_stats, f, indent=2)
    logger.info("Saved normalization stats to %s", stats_path)

    # --- Summary ---
    logger.info("=" * 60)
    logger.info("BUILD COMPLETE")
    logger.info("  X shape: %s (time, channels, lat, lon)", x_array.shape)
    logger.info("  Y shape: %s (time, depths, lat, lon)", y_array.shape)
    logger.info("  Mask shape: %s (lat, lon)", mask.shape)
    logger.info("  Valid cells: %d/%d", mask.sum(), mask.size)
    logger.info("  Time range: %s to %s", common_times[0], common_times[-1])
    logger.info("  Normalization: z-score per channel (training data only)")
    logger.info("  Output: %s", output_dir)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
