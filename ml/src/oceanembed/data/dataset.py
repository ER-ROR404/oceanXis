"""PyTorch Dataset for OceanEmbed Zarr tensors.

Following spec v2.1 §5, §16-§17:
- Temporal window T=7 (spec §5)
- Train 2018-2023 / Val 2024 / Test 2025 (spec §16)
- Training statistics from training data only (spec §17)
- Temporal locked split — no shuffling across time

Tensor layout (from Phase 2 harmonization):
  X.zarr: [time, channel, latitude, longitude] — 7 surface channels
  Y.zarr: [time, depth, latitude, longitude] — 15 depth temperatures
  mask.zarr: [latitude, longitude] — ocean validity mask
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
import xarray as xr
from torch.utils.data import DataLoader, Dataset


class OceanEmbedDataset(Dataset):
    """Dataset for OceanEmbed surface→subsurface reconstruction.

    Each sample returns:
      - x: [T, C, H, W] — T-day window of C surface channels
      - y: [D, H, W] — D depth temperatures for the target day
      - mask: [H, W] — ocean validity mask (1=ocean, 0=land)
    """

    def __init__(
        self,
        region_dir: str | Path,
        temporal_window: int = 7,
        normalize: bool = True,
        day_of_year_encoding: bool = False,
    ) -> None:
        """Initialize dataset.

        Args:
            region_dir: Path to region directory containing X.zarr, Y.zarr, mask.zarr.
            temporal_window: Number of input timesteps (T=7 per spec §5).
            normalize: Whether to apply z-score normalization.
            day_of_year_encoding: Whether to include day-of-year info.
        """
        self.region_dir = Path(region_dir)
        self.T = temporal_window
        self.normalize = normalize
        self.day_of_year_encoding = day_of_year_encoding

        # Load Zarr arrays
        self.X = xr.open_zarr(self.region_dir / "X.zarr")["__xarray_dataarray_variable__"]
        self.Y = xr.open_zarr(self.region_dir / "Y.zarr")["__xarray_dataarray_variable__"]
        self.mask = xr.open_zarr(self.region_dir / "mask.zarr")["__xarray_dataarray_variable__"]

        # Get dimensions
        self.n_time = self.X.shape[0]
        self.n_channels = self.X.shape[1]
        self.n_depths = self.Y.shape[1]
        self.H = self.X.shape[2]
        self.W = self.X.shape[3]

        # Load normalization statistics
        self.norm_stats = None
        if normalize:
            self._load_normalization_stats()

        # Valid sample indices (temporal window must fit)
        self.n_samples = self.n_time - self.T + 1

    def _load_normalization_stats(self) -> None:
        """Load z-score normalization statistics from manifest."""
        stats_path = self.region_dir / "normalization_stats.json"
        if not stats_path.exists():
            # Fallback: try manifest.json
            manifest_path = self.region_dir / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)
                self.norm_stats = manifest.get("normalization", {}).get("statistics", {})
            else:
                self.norm_stats = {}
        else:
            with open(stats_path) as f:
                self.norm_stats = json.load(f)

    def __len__(self) -> int:
        return self.n_samples

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Get a single sample.

        Args:
            idx: Sample index (0 to n_samples-1).

        Returns:
            x: [T, C, H, W] input window.
            y: [D, H, W] target temperatures.
            mask: [H, W] ocean validity mask.
        """
        # Input window: days [idx, idx+T-1]
        # Target day: idx+T-1 (last day of window)
        x_slice = self.X.isel(time=slice(idx, idx + self.T)).values  # [T, C, H, W]
        y_day = idx + self.T - 1
        y_slice = self.Y.isel(time=y_day).values  # [D, H, W]
        mask_vals = self.mask.values  # [H, W]

        # Normalize input channels
        if self.normalize and self.norm_stats:
            x_slice = self._normalize_x(x_slice)

        # Convert to tensors
        x_tensor = torch.from_numpy(x_slice.copy()).float()
        y_tensor = torch.from_numpy(y_slice.copy()).float()
        mask_tensor = torch.from_numpy(mask_vals.copy()).float()

        return x_tensor, y_tensor, mask_tensor

    def _normalize_x(self, x: np.ndarray) -> np.ndarray:
        """Apply z-score normalization per channel.

        Uses training statistics only (spec v2.1 §17).
        Land cells (NaN) are zero-filled after z-scoring so the conv encoder
        never sees NaN (which would spread across the whole feature map).
        """
        x_norm = x.copy()
        for c in range(self.n_channels):
            key = f"channel_{c}"
            if key in self.norm_stats:
                mean = self.norm_stats[key]["mean"]
                std = self.norm_stats[key]["std"]
                if std > 1e-8:
                    x_norm[:, c] = (x[:, c] - mean) / std
        # NaN -> 0 (neutral after z-score); mask handles land at loss time
        return np.nan_to_num(x_norm, nan=0.0)

    def get_day_of_year(self, idx: int) -> int:
        """Get day-of-year for a sample (for seasonal encoding)."""
        # If time coords are actual dates, extract day-of-year
        try:
            time_val = self.X.time.values[idx + self.T - 1]
            return int(np.datetime64(time_val, "D") - np.datetime64(str(time_val)[:4] + "-01-01", "D")) + 1
        except Exception:
            return idx % 365 + 1


def create_dataloaders(
    region_dir: str | Path,
    temporal_window: int = 7,
    batch_size: int = 8,
    normalize: bool = True,
    val_fraction: float = 0.2,
    num_workers: int = 0,
) -> tuple[DataLoader, DataLoader]:
    """Create train/validation DataLoaders with temporal split.

    Following spec v2.1 §16: temporal_locked split.
    Training data comes first, validation data comes after (no shuffling across time).

    Args:
        region_dir: Path to region directory.
        temporal_window: Input window size (default: 7).
        batch_size: Batch size.
        normalize: Whether to normalize.
        val_fraction: Fraction of data for validation.
        num_workers: Number of data loading workers.

    Returns:
        (train_loader, val_loader) tuple.
    """
    full_dataset = OceanEmbedDataset(region_dir, temporal_window=temporal_window, normalize=normalize)

    # Temporal split: first portion for training, last portion for validation
    n_total = len(full_dataset)
    n_val = max(1, int(n_total * val_fraction))
    n_train = n_total - n_val

    train_dataset = torch.utils.data.Subset(full_dataset, list(range(n_train)))
    val_dataset = torch.utils.data.Subset(full_dataset, list(range(n_train, n_total)))

    # Temporal split: NO shuffling (spec v2.1 §17)
    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers,
    )

    return train_loader, val_loader
