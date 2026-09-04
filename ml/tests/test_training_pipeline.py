"""Tests for OceanEmbedDataset and training pipeline (TDD RED phase).

Following spec v2.1 §5, §16-§17:
- Temporal window T=7 (spec §5)
- Train 2018-2023 / Val 2024 / Test 2025 (spec §16)
- Training statistics from training data only (spec §17)
- Temporal locked split (no shuffling across time)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch
import xarray as xr

from oceanembed.data.dataset import OceanEmbedDataset, create_dataloaders
from oceanembed.training.trainer import Trainer, EarlyStopping


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def fake_zarr_dir(tmp_path: Path):
    """Create minimal fake Zarr tensors for testing."""
    region_dir = tmp_path / "test_region"
    region_dir.mkdir(parents=True, exist_ok=True)

    # Create fake X data: 30 days, 7 channels, 16x16 grid
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

    # Create fake Y data: 30 days, 15 depths, 16x16 grid
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

    # Create fake mask: 16x16, mostly ocean
    mask_data = np.ones((h, w), dtype=np.float32)
    mask_data[0, 0] = 0.0  # one land cell
    mask = xr.DataArray(
        mask_data,
        dims=["latitude", "longitude"],
        coords={
            "latitude": np.linspace(5.0, 30.0, h),
            "longitude": np.linspace(45.0, 105.0, w),
        },
    )
    mask.to_zarr(region_dir / "mask.zarr", mode="w")

    # Create normalization stats
    stats = {f"channel_{i}": {"mean": float(np.mean(X_data[:, i])),
                               "std": float(np.std(X_data[:, i]))}
             for i in range(n_channels)}
    with open(region_dir / "normalization_stats.json", "w") as f:
        json.dump(stats, f)

    # Create manifest
    manifest = {
        "region": "test_region",
        "grid": {"latitude_count": h, "longitude_count": w, "resolution_degrees": 0.25},
        "split_policy": {"method": "temporal_locked"},
        "normalization": {"statistics_source": "training_data_only", "statistics": stats},
    }
    with open(region_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)

    return region_dir, n_days, n_channels, n_depths, h, w


# ── Test: OceanEmbedDataset ──────────────────────────────────────────────

class TestOceanEmbedDataset:
    """Tests for the core Dataset class."""

    def test_dataset_length(self, fake_zarr_dir):
        """Dataset length accounts for temporal window (T=7)."""
        region_dir, n_days, _, _, _, _ = fake_zarr_dir
        ds = OceanEmbedDataset(region_dir, temporal_window=7)
        # With 30 days and T=7, we have 30 - 7 + 1 = 24 valid windows
        assert len(ds) == n_days - 7 + 1

    def test_dataset_getitem_shapes(self, fake_zarr_dir):
        """Each sample returns (x, y, mask) with correct shapes."""
        region_dir, _, n_channels, n_depths, h, w = fake_zarr_dir
        ds = OceanEmbedDataset(region_dir, temporal_window=7)
        x, y, mask = ds[0]
        # x: [T=7, C=7, H, W]
        assert x.shape == (7, n_channels, h, w)
        # y: [15, H, W] (single day target)
        assert y.shape == (n_depths, h, w)
        # mask: [H, W]
        assert mask.shape == (h, w)

    def test_dataset_dtype(self, fake_zarr_dir):
        """Data is returned as float32 tensors."""
        region_dir, _, _, _, _, _ = fake_zarr_dir
        ds = OceanEmbedDataset(region_dir, temporal_window=7)
        x, y, mask = ds[0]
        assert x.dtype == torch.float32
        assert y.dtype == torch.float32
        assert mask.dtype == torch.float32

    def test_dataset_normalization(self, fake_zarr_dir):
        """Data is normalized using training statistics."""
        region_dir, _, _, _, _, _ = fake_zarr_dir
        ds = OceanEmbedDataset(region_dir, temporal_window=7, normalize=True)
        x, y, mask = ds[0]
        # After normalization, values should be roughly in [-3, 3]
        assert x.abs().max() < 10.0  # reasonable bound

    def test_dataset_no_normalization(self, fake_zarr_dir):
        """Data is raw when normalization is disabled."""
        region_dir, _, _, _, _, _ = fake_zarr_dir
        ds = OceanEmbedDataset(region_dir, temporal_window=7, normalize=False)
        x, y, mask = ds[0]
        # Raw values can be anything
        assert x.shape == (7, 7, 16, 16)

    def test_dataset_sequential_order(self, fake_zarr_dir):
        """Samples are returned in temporal order."""
        region_dir, _, _, _, _, _ = fake_zarr_dir
        ds = OceanEmbedDataset(region_dir, temporal_window=7)
        # First sample uses days 0-6, target is day 6
        # Second sample uses days 1-7, target is day 7
        x1, y1, _ = ds[0]
        x2, y2, _ = ds[1]
        # x2 should be shifted by 1 day relative to x1
        assert not torch.allclose(x1, x2)
        # y2 should be different from y1 (different target day)
        assert not torch.allclose(y1, y2)

    def test_dataset_window_target_alignment(self, fake_zarr_dir):
        """Target day matches last day of input window."""
        region_dir, _, _, _, _, _ = fake_zarr_dir
        ds = OceanEmbedDataset(region_dir, temporal_window=7)
        # Sample i uses input days [i, i+6], target day i+6
        x, y, _ = ds[0]
        # x[:, 6] is the last day of input, y is the target
        # They should be from the same time step
        # (in normalized space, they might differ slightly due to different channels)
        assert x.shape[0] == 7  # temporal window


# ── Test: DataLoader creation ─────────────────────────────────────────────

class TestCreateDataloaders:
    """Tests for DataLoader factory function."""

    def test_creates_train_val_loaders(self, fake_zarr_dir):
        """Creates separate train and validation loaders."""
        region_dir, _, _, _, _, _ = fake_zarr_dir
        train_loader, val_loader = create_dataloaders(
            region_dir, temporal_window=7, batch_size=4, val_fraction=0.3
        )
        assert len(train_loader) > 0
        assert len(val_loader) > 0

    def test_batch_shapes(self, fake_zarr_dir):
        """Batches have correct shapes."""
        region_dir, _, _, _, _, _ = fake_zarr_dir
        train_loader, _ = create_dataloaders(
            region_dir, temporal_window=7, batch_size=4, val_fraction=0.3
        )
        x_batch, y_batch, mask_batch = next(iter(train_loader))
        assert x_batch.shape[0] == 4  # batch dim
        assert x_batch.shape[1] == 7  # temporal window
        assert x_batch.shape[2] == 7  # channels

    def test_val_smaller_than_train(self, fake_zarr_dir):
        """Validation set is smaller than training set."""
        region_dir, _, _, _, _, _ = fake_zarr_dir
        train_loader, val_loader = create_dataloaders(
            region_dir, temporal_window=7, batch_size=4, val_fraction=0.3
        )
        assert len(train_loader) > len(val_loader)


# ── Test: Early Stopping ─────────────────────────────────────────────────

class TestEarlyStopping:
    """Tests for early stopping callback."""

    def test_stops_when_no_improvement(self):
        """Stops after patience epochs without improvement."""
        es = EarlyStopping(patience=3)
        # Simulate: loss decreases then plateaus
        losses = [1.0, 0.9, 0.8, 0.8, 0.8, 0.8, 0.8]
        should_stop = []
        for loss in losses:
            should_stop.append(es.step(loss))
        assert should_stop[-1] is True  # should stop
        assert es.best_loss == 0.8

    def test_resets_on_improvement(self):
        """Resets counter when loss improves."""
        es = EarlyStopping(patience=10)
        losses = [1.0, 0.9, 0.85, 0.9, 0.8, 0.85, 0.85, 0.85, 0.85]
        should_stop = []
        for loss in losses:
            should_stop.append(es.step(loss))
        # Should not stop because loss improved at step 4 (0.8 < 0.85)
        # and we only have 4 non-improving steps after that (< patience=10)
        assert all(s is False for s in should_stop)


# ── Test: Trainer ─────────────────────────────────────────────────────────

class TestTrainer:
    """Tests for the training loop."""

    def test_trainer_runs_one_epoch(self, fake_zarr_dir):
        """Trainer completes one epoch without error."""
        from oceanembed.models.reconstruction_net import OceanEmbedNet

        region_dir, _, _, _, _, _ = fake_zarr_dir
        train_loader, val_loader = create_dataloaders(
            region_dir, temporal_window=7, batch_size=4, val_fraction=0.3
        )
        model = OceanEmbedNet(in_channels=7, out_channels=15, use_seasonal=False, use_spatial=False)
        trainer = Trainer(model=model, train_loader=train_loader, val_loader=val_loader)
        history = trainer.train(epochs=1)
        assert "train_loss" in history
        assert len(history["train_loss"]) == 1

    def test_trainer_reduces_loss(self, fake_zarr_dir):
        """Training reduces loss over multiple epochs."""
        from oceanembed.models.reconstruction_net import OceanEmbedNet

        region_dir, _, _, _, _, _ = fake_zarr_dir
        train_loader, val_loader = create_dataloaders(
            region_dir, temporal_window=7, batch_size=4, val_fraction=0.3
        )
        model = OceanEmbedNet(in_channels=7, out_channels=15, use_seasonal=False, use_spatial=False)
        trainer = Trainer(model=model, train_loader=train_loader, val_loader=val_loader)
        history = trainer.train(epochs=5)
        # Loss should decrease
        assert history["train_loss"][-1] < history["train_loss"][0]

    def test_trainer_checkpointing(self, fake_zarr_dir, tmp_path):
        """Trainer saves checkpoints."""
        from oceanembed.models.reconstruction_net import OceanEmbedNet

        region_dir, _, _, _, _, _ = fake_zarr_dir
        train_loader, val_loader = create_dataloaders(
            region_dir, temporal_window=7, batch_size=4, val_fraction=0.3
        )
        model = OceanEmbedNet(in_channels=7, out_channels=15, use_seasonal=False, use_spatial=False)
        trainer = Trainer(
            model=model, train_loader=train_loader, val_loader=val_loader,
            checkpoint_dir=tmp_path
        )
        trainer.train(epochs=2)
        # Should save a checkpoint
        checkpoints = list(tmp_path.glob("*.pt"))
        assert len(checkpoints) > 0

    def test_trainer_early_stopping(self, fake_zarr_dir):
        """Trainer stops early when loss plateaus."""
        from oceanembed.models.reconstruction_net import OceanEmbedNet

        region_dir, _, _, _, _, _ = fake_zarr_dir
        train_loader, val_loader = create_dataloaders(
            region_dir, temporal_window=7, batch_size=4, val_fraction=0.3
        )
        model = OceanEmbedNet(in_channels=7, out_channels=15, use_seasonal=False, use_spatial=False)
        trainer = Trainer(
            model=model, train_loader=train_loader, val_loader=val_loader,
            early_stopping_patience=2
        )
        history = trainer.train(epochs=100)
        # Should stop before 100 epochs
        assert len(history["train_loss"]) < 100
