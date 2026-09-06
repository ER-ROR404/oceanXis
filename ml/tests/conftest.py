"""Shared test fixtures for the ML suite."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def tiny_region(tmp_path):
    """Tiny synthetic region store: [10 days, 7ch, 2x2] at 0.25°; (0,0)=land."""
    n_time, n_ch, n_dep, H, W = 10, 7, 15, 2, 2
    time = pd.date_range("2024-01-01", periods=n_time, freq="D")
    lat = np.array([5.0, 5.25])
    lon = np.array([45.0, 45.25])

    rng = np.random.default_rng(7)
    x = rng.normal(size=(n_time, n_ch, H, W)).astype(np.float32)
    y = 20.0 + rng.normal(scale=2.0, size=(n_time, n_dep, H, W)).astype(np.float32)
    mask = np.array([[0, 1], [1, 1]], dtype=np.float32)  # (0,0) is land

    import xarray as xr
    xr.DataArray(
        x, dims=("time", "channel", "lat", "lon"),
        coords={"time": time, "lat": lat, "lon": lon},
    ).to_zarr(str(tmp_path / "X.zarr"))
    xr.DataArray(
        y, dims=("time", "depth", "lat", "lon"),
        coords={"time": time, "lat": lat, "lon": lon},
    ).to_zarr(str(tmp_path / "Y.zarr"))
    xr.DataArray(
        mask, dims=("lat", "lon"), coords={"lat": lat, "lon": lon},
    ).to_zarr(str(tmp_path / "mask.zarr"))

    stats = {
        f"channel_{c}": {"mean": float(np.mean(x[:, c])), "std": float(np.std(x[:, c]) or 1.0)}
        for c in range(n_ch)
    }
    (tmp_path / "normalization_stats.json").write_text(json.dumps(stats))
    return tmp_path
