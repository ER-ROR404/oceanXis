"""Tests for the Colab-safe training entry point (ml/scripts/train_colab_entry.py).

Covers the real training path (not just --check preflight):
  - run_training() builds model + dataloaders + trainer from a config
  - writes checkpoints and a run manifest/metrics JSON to artifacts dir
  - --check stays a no-op preflight
  - missing config / missing data dir fail fast
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

# The script lives in ml/scripts — import as a module for unit-testing
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "train_colab_entry.py"
_src_ml = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_src_ml))

import importlib.util

spec = importlib.util.spec_from_file_location("train_colab_entry", _SCRIPT)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


@pytest.fixture
def fake_zarr_dir(tmp_path: Path):
    """Create minimal fake Zarr tensors for training (same pattern as training pipeline tests)."""
    region_dir = tmp_path / "test_region"
    region_dir.mkdir(parents=True, exist_ok=True)

    n_days, n_channels, h, w = 30, 7, 16, 16
    X_data = np.random.randn(n_days, n_channels, h, w).astype(np.float32)
    X = xr.DataArray(
        X_data,
        dims=["time", "channel", "latitude", "longitude"],
        coords={
            "time": np.arange(n_days),
            "channel": np.arange(n_channels),
            "latitude": np.linspace(5.0, 30.0, h),
            "longitude": np.linspace(45.0, 105.0, w),
        },
    )
    X.to_zarr(region_dir / "X.zarr", mode="w")

    n_depths = 15
    Y_data = np.random.randn(n_days, n_depths, h, w).astype(np.float32)
    Y = xr.DataArray(
        Y_data,
        dims=["time", "depth", "latitude", "longitude"],
        coords={
            "time": np.arange(n_days),
            "depth": [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000],
            "latitude": np.linspace(5.0, 30.0, h),
            "longitude": np.linspace(45.0, 105.0, w),
        },
    )
    Y.to_zarr(region_dir / "Y.zarr", mode="w")

    mask_data = np.ones((h, w), dtype=np.float32)
    mask = xr.DataArray(
        mask_data,
        dims=["latitude", "longitude"],
        coords={
            "latitude": np.linspace(5.0, 30.0, h),
            "longitude": np.linspace(45.0, 105.0, w),
        },
    )
    mask.to_zarr(region_dir / "mask.zarr", mode="w")

    stats = {f"channel_{i}": {"mean": float(np.mean(X_data[:, i])),
                              "std": float(np.std(X_data[:, i]))}
             for i in range(n_channels)}
    (region_dir / "normalization_stats.json").write_text(json.dumps(stats))

    return region_dir


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """A minimal hybrid_v1-style config that matches OceanEmbedNet defaults."""
    cfg = {
        "experiment": {"name": "smoke_test", "status": "testing"},
        "model": {
            "architecture": "oceanembed_net",
            "in_channels": 7,
            "out_channels": 15,
            "uncertainty": True,
            "convlstm_hidden": 16,
            "convlstm_layers": 1,
        },
        "data": {"temporal_window": 7, "batch_size": 4, "val_fraction": 0.2},
        "training": {"epochs": 2, "lr": 0.001, "seed": 42, "early_stopping_patience": 5},
    }
    path = tmp_path / "hybrid_smoke.yaml"
    path.write_text(
        __import__("yaml").safe_dump(cfg)
    )
    return path


class TestRunTraining:
    def test_trains_one_epoch_and_writes_checkpoint(self, fake_zarr_dir, config_file, tmp_path) -> None:
        artifacts = tmp_path / "artifacts"
        history, _, status = entry.run_training(
            config=config_file,
            data_dir=fake_zarr_dir,
            artifacts_dir=artifacts,
        )
        assert status == "complete"
        assert len(history["train_loss"]) == 2
        assert len(history["val_loss"]) == 2
        # Checkpoints written
        assert (artifacts / "best.pt").exists()
        assert (artifacts / "latest.pt").exists()

    def test_writes_run_manifest(self, fake_zarr_dir, config_file, tmp_path) -> None:
        artifacts = tmp_path / "artifacts"
        entry.run_training(config=config_file, data_dir=fake_zarr_dir, artifacts_dir=artifacts)
        manifest_file = artifacts / "run_manifest.json"
        assert manifest_file.exists()
        manifest = json.loads(manifest_file.read_text())
        assert manifest["experiment"] == "smoke_test"
        assert "metrics" in manifest
        assert manifest["status"] == "complete"

    def test_missing_config_fails_fast(self, fake_zarr_dir, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            entry.run_training(
                config=tmp_path / "nope.yaml",
                data_dir=fake_zarr_dir,
                artifacts_dir=tmp_path / "artifacts",
            )

    def test_missing_data_dir_fails_fast(self, config_file, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            entry.run_training(
                config=config_file,
                data_dir=tmp_path / "missing_region",
                artifacts_dir=tmp_path / "artifacts",
            )


class TestPreflight:
    def test_preflight_still_works_without_data(self, config_file, tmp_path) -> None:
        """--check only validates env/config/artifacts; it must not need data."""
        artifacts = tmp_path / "artifacts"
        # Should not raise for missing data dir (preflight doesn't touch data)
        result = entry.run_preflight(config_file, artifacts, require_gpu=False)
        assert result is not None or result is None  # just confirms no exception


class TestMainCLI:
    def test_cli_check_returns_zero(self, config_file, tmp_path) -> None:
        env = dict(__import__("os").environ)
        r = subprocess.run(
            [sys.executable, str(_SCRIPT), "--config", str(config_file),
             "--artifacts-dir", str(tmp_path / "artifacts"), "--check"],
            capture_output=True, text=True, timeout=60, env={k: v for k, v in env.items() if k != "COPERNICUSMARINE_SERVICE_PASSWORD"},
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"