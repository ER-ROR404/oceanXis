"""Harmonize Copernicus products onto the 0.25° canonical grid.

Responsibilities:
- Regrid all inputs to 0.25° regular lat/lon grid
- Select 15 canonical depths from GLORYS's 35 native levels
- Extract surface values from multi-depth datasets (currents at 0m)
- Preserve channel ordering (Golden Rule 17) and depth ordering (Golden Rule 18)
- Create land/sea validity masks

Usage:
    harmonized = harmonize_surface_input(ds, variable="analysed_sst", region=bounds)
    target = harmonize_glorys_target(ds, region=bounds)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import xarray as xr

from .catalog import CANONICAL_DEPTHS_M, CANONICAL_INPUT_CHANNELS
from .regions import RegionBounds

logger = logging.getLogger(__name__)

# Canonical 0.25° grid for the North Indian Ocean domain
CANONICAL_RESOLUTION = 0.25  # degrees


def make_target_grid(
    region: RegionBounds,
    resolution: float = CANONICAL_RESOLUTION,
) -> tuple[np.ndarray, np.ndarray]:
    """Create target latitude/longitude arrays at the canonical resolution.

    Args:
        region: Geographic bounding box.
        resolution: Grid spacing in degrees (default 0.25).

    Returns:
        Tuple of (lat_array, lon_array).
    """
    lat = np.arange(
        region.lat_min,
        region.lat_max + resolution / 2,  # include endpoint
        resolution,
    )
    lon = np.arange(
        region.lon_min,
        region.lon_max + resolution / 2,
        resolution,
    )
    return lat, lon


def select_canonical_depths(depth_array: np.ndarray) -> np.ndarray:
    """Select the 15 canonical depth indices nearest to our standard depths.

    Args:
        depth_array: Native depth coordinates from the dataset.

    Returns:
        Array of 15 integer indices into depth_array.
    """
    indices = []
    for target_depth in CANONICAL_DEPTHS_M:
        idx = int(abs(depth_array - target_depth).argmin())
        indices.append(idx)
    return np.array(indices)


def harmonize_surface_input(
    ds: xr.Dataset,
    variable: str,
    region: RegionBounds,
    depth_level: Optional[int] = None,
) -> xr.DataArray:
    """Regrid a surface input variable to the canonical 0.25° grid.

    Handles:
    - Different native resolutions (0.05°, 0.083°, 0.125°, 0.25°)
    - Multi-depth datasets (extract surface or specified depth)
    - NaN at coastline edges (expected, not filled)

    Args:
        ds: Open xarray Dataset containing the variable.
        variable: Variable name (e.g. "analysed_sst", "uo", "sla").
        region: Target geographic bounds.
        depth_level: If the variable has a depth dimension, extract this
                     index (0 = surface). If None and depth dim exists, uses 0.

    Returns:
        DataArray regridded to [time, lat, lon] at 0.25°.
    """
    # Extract the variable
    da = ds[variable]

    # Handle depth dimension — extract surface or specified level
    if "depth" in da.dims:
        if depth_level is None:
            depth_level = 0
        da = da.isel(depth=depth_level)
        logger.info("Extracted depth level %d for %s", depth_level, variable)

    # Identify lat/lon dimension names (vary across products)
    lat_dim = _find_dim(da, ["latitude", "lat"])
    lon_dim = _find_dim(da, ["longitude", "lon"])

    if lat_dim is None or lon_dim is None:
        raise ValueError(
            f"Could not find lat/lon dimensions in {variable}. "
            f"Available dims: {list(da.dims)}"
        )

    # Create target grid
    target_lat, target_lon = make_target_grid(region)

    # Regrid via linear interpolation
    regridded = da.interp(
        {lat_dim: target_lat, lon_dim: target_lon},
        method="linear",
    )

    logger.info(
        "Regridded %s: %s -> %s",
        variable,
        {d: da.sizes[d] for d in da.dims},
        {d: regridded.sizes[d] for d in regridded.dims},
    )

    return regridded


def harmonize_glorys_target(
    ds: xr.Dataset,
    region: RegionBounds,
) -> xr.DataArray:
    """Regrid GLORYS temperature to canonical 15-depth, 0.25° grid.

    Steps:
    1. Select 15 canonical depths from GLORYS's 35 native levels
    2. Regrid spatially to 0.25° grid

    Args:
        ds: Open xarray Dataset with thetao variable.
        region: Target geographic bounds.

    Returns:
        DataArray of shape [time, depth=15, lat, lon] at 0.25°.
    """
    thetao = ds["thetao"]

    # Step 1: Select canonical depths
    depth_indices = select_canonical_depths(ds.depth.values)
    selected_depths = ds.depth.values[depth_indices]
    thetao = thetao.isel(depth=depth_indices)

    logger.info(
        "Selected %d canonical depths from %d native levels",
        len(depth_indices),
        len(ds.depth.values),
    )
    logger.info(
        "Canonical depths (nearest): %s",
        [f"{d:.1f}m" for d in selected_depths],
    )

    # Step 2: Regrid spatially
    lat_dim = _find_dim(thetao, ["latitude", "lat"])
    lon_dim = _find_dim(thetao, ["longitude", "lon"])
    target_lat, target_lon = make_target_grid(region)

    regridded = thetao.interp(
        {lat_dim: target_lat, lon_dim: target_lon},
        method="linear",
    )

    logger.info(
        "Regridded GLORYS thetao: -> %s",
        {d: regridded.sizes[d] for d in regridded.dims},
    )

    return regridded


def build_validity_mask(
    harmonized_inputs: list[xr.DataArray],
    harmonized_target: Optional[xr.DataArray] = None,
) -> xr.DataArray:
    """Build a combined land/sea validity mask.

    A cell is valid (True) if it is ocean in ALL inputs AND (optionally) the target.

    Args:
        harmonized_inputs: List of regridded input DataArrays [time, lat, lon].
        harmonized_target: Rehashed GLORYS target [time, depth, lat, lon] (optional).

    Returns:
        Boolean DataArray of shape [lat, lon] — True where all data is valid.
    """
    # Start with all-True mask
    # Use the first input's lat/lon for spatial coordinates
    ref = harmonized_inputs[0]
    lat_dim = _find_dim(ref, ["latitude", "lat"])
    lon_dim = _find_dim(ref, ["longitude", "lon"])

    mask = xr.ones_like(ref.isel({ref.dims[0]: 0}), dtype=bool)

    # AND with each input (across time — any NaN at any time = invalid)
    for i, inp in enumerate(harmonized_inputs):
        # Collapse time dimension: cell is valid if NOT all-NaN across time
        valid = inp.notnull().any(dim=inp.dims[0])
        mask = mask & valid
        logger.debug("Input %d validity: %d/%d cells valid", i, int(valid.sum()), mask.size)

    # AND with target if provided
    if harmonized_target is not None:
        # Collapse time + depth: valid if any valid value exists
        valid = harmonized_target.notnull().any(dim=harmonized_target.dims[:2])
        mask = mask & valid
        logger.debug("Target validity: %d/%d cells valid", int(valid.sum()), mask.size)

    valid_count = int(mask.sum())
    total_count = mask.size
    logger.info(
        "Validity mask: %d/%d cells valid (%.1f%%)",
        valid_count,
        total_count,
        100.0 * valid_count / total_count,
    )

    return mask


def _find_dim(da: xr.DataArray, candidates: list[str]) -> Optional[str]:
    """Find a dimension name from a list of candidates.

    Args:
        da: DataArray to search.
        candidates: Possible dimension names.

    Returns:
        First matching dimension name, or None.
    """
    for name in candidates:
        if name in da.dims:
            return name
    return None
