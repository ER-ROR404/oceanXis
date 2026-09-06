"""Shared fixtures for the serving test suite (ml/tests/unit/serving/)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
import torch

N_TIME, N_CH, N_DEP, H, W = 12, 7, 15, 8, 8
LAT0, LON0 = 5.0, 45.0


@pytest.fixture
def serving_region(tmp_path):
    """Synthetic tensor store: [12 days, 7ch, 15 depths, 8x8]; (0,0)=land."""
    time = pd.date_range("2024-01-01", periods=N_TIME, freq="D")
    lat = LAT0 + 0.25 * np.arange(H)
    lon = LON0 + 0.25 * np.arange(W)

    rng = np.random.default_rng(7)
    x = rng.normal(size=(N_TIME, N_CH, H, W)).astype(np.float32)
    y = 20.0 + rng.normal(scale=2.0, size=(N_TIME, N_DEP, H, W)).astype(np.float32)
    mask = np.ones((H, W), dtype=np.float32)
    mask[0, 0] = 0.0  # single land cell

    import xarray as xr

    xr.DataArray(
        x,
        dims=("time", "channel", "latitude", "longitude"),
        coords={"time": time, "latitude": lat, "longitude": lon},
    ).to_zarr(str(tmp_path / "X.zarr"))
    xr.DataArray(
        y,
        dims=("time", "depth", "latitude", "longitude"),
        coords={"time": time, "latitude": lat, "longitude": lon},
    ).to_zarr(str(tmp_path / "Y.zarr"))
    xr.DataArray(
        mask,
        dims=("latitude", "longitude"),
        coords={"latitude": lat, "longitude": lon},
    ).to_zarr(str(tmp_path / "mask.zarr"))

    stats = {
        f"channel_{c}": {"mean": float(np.mean(x[:, c])), "std": float(np.std(x[:, c]) or 1.0)}
        for c in range(N_CH)
    }
    (tmp_path / "normalization_stats.json").write_text(json.dumps(stats))
    return tmp_path


@pytest.fixture
def checkpoint_path(serving_region) -> str:
    """A real best-model checkpoint matching the serving config."""
    from oceanembed.models.reconstruction_net import OceanEmbedNet

    model = OceanEmbedNet(
        in_channels=N_CH,
        out_channels=N_DEP,
        use_seasonal=True,
        use_spatial=True,
        convlstm_hidden=8,
        convlstm_layers=1,
    )
    path = serving_region / "best.pt"
    torch.save(
        {
            "best_model_state": {k: v.clone() for k, v in model.state_dict().items()},
            "model_state_dict": model.state_dict(),
            "epoch": 3,
            "val_loss": 1.0,
            "history": {"train_loss": [], "val_loss": []},
        },
        path,
    )
    return str(path)


@pytest.fixture
def cfg() -> dict:
    return {
        "architecture": "oceanembed_net",
        "in_channels": N_CH,
        "out_channels": N_DEP,
        "uncertainty": True,
        "convlstm_hidden": 8,
        "convlstm_layers": 1,
        "use_seasonal": True,
        "use_spatial": True,
    }
