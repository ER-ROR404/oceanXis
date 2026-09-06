"""Demo cache builder tests (plan Step 2.3).

build -> reload -> shapes; masked (land) counts stable; manifest fields
present. The cache is the offline fallback_demo path: NaN land must round-trip
and the manifest must be honest about what produced it.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from oceanembed.serving.build_demo_cache import build_demo_cache

N_TIME, N_CH, N_DEP, H, W = 12, 7, 15, 8, 8


@pytest.fixture
def out_dir(tmp_path) -> str:
    return str(tmp_path / "demo_cache")


def test_build_reload_shapes(
    serving_region, checkpoint_path, cfg, out_dir
) -> None:
    """Dates after the 7-day window boundary become valid npz maps."""
    manifest = build_demo_cache(
        region_dir=str(serving_region),
        checkpoint_path=checkpoint_path,
        cfg=cfg,
        start="2024-01-08",
        end="2024-01-11",
        step_days=1,
        region_id="bay_of_bengal",
        out_dir=out_dir,
    )
    assert manifest["n_dates"] == 4
    assert manifest["n_lat"] == H and manifest["n_lon"] == W

    for date in ["2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11"]:
        with np.load(f"{out_dir}/bay_of_bengal/{date}.npz", allow_pickle=True) as z:
            assert z["mu"].shape == (N_DEP, H, W)
            assert z["log_var"].shape == (N_DEP, H, W)
            assert z["mu"].dtype == np.float32


def test_land_cell_is_nan_after_roundtrip(
    serving_region, checkpoint_path, cfg, out_dir
) -> None:
    build_demo_cache(
        region_dir=str(serving_region),
        checkpoint_path=checkpoint_path,
        cfg=cfg,
        start="2024-01-08",
        end="2024-01-08",
        step_days=1,
        region_id="bay_of_bengal",
        out_dir=out_dir,
    )
    with np.load(f"{out_dir}/bay_of_bengal/2024-01-08.npz", allow_pickle=True) as z:
        # Synthetic land cell at (0,0) -> NaN (never 0.0).
        assert np.isnan(z["mu"][:, 0, 0]).all()
        assert np.isfinite(z["mu"][0, 1, 1])


def test_window_boundary_dates_are_skipped_not_crash(
    serving_region, checkpoint_path, cfg, out_dir
) -> None:
    """predict raises inside the window boundary; the builder must skip."""
    manifest = build_demo_cache(
        region_dir=str(serving_region),
        checkpoint_path=checkpoint_path,
        cfg=cfg,
        start="2024-01-01",  # t=0..5 are inside the 7-day window
        end="2024-01-12",
        step_days=1,
        region_id="bay_of_bengal",
        out_dir=out_dir,
    )
    assert json.loads(Path(f"{out_dir}/manifest.json").read_text())["region"] == "bay_of_bengal"  # file written
    assert manifest["n_dates"] == 6  # only 2024-01-07..2024-01-12 valid
    assert manifest["masked_land_count"] == 1  # (0,0) from the synthetic mask


def test_coordinates_and_manifest_fields(
    serving_region, checkpoint_path, cfg, out_dir
) -> None:
    build_demo_cache(
        region_dir=str(serving_region),
        checkpoint_path=checkpoint_path,
        cfg=cfg,
        start="2024-01-08",
        end="2024-01-08",
        step_days=1,
        region_id="bay_of_bengal",
        out_dir=out_dir,
    )
    coords = json.loads(Path(f"{out_dir}/bay_of_bengal/coordinates.json").read_text())
    assert len(coords["lat"]) == H and len(coords["lon"]) == W
    assert coords["depths_m"] == [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]

    manifest = json.loads(Path(f"{out_dir}/manifest.json").read_text())
    for key in ("region", "model_version", "date_start", "date_end", "n_dates",
                "epoch", "val_loss", "grid", "masked_land_count",
                "channel_status", "format_version"):
        assert key in manifest, f"manifest missing: {key}"
    assert manifest["region"] == "bay_of_bengal"
    assert all(v == "available" for v in manifest["channel_status"].values())


def test_step_filters_dates(
    serving_region, checkpoint_path, cfg, out_dir
) -> None:
    manifest = build_demo_cache(
        region_dir=str(serving_region),
        checkpoint_path=checkpoint_path,
        cfg=cfg,
        start="2024-01-07",
        end="2024-01-12",
        step_days=2,
        region_id="bay_of_bengal",
        out_dir=out_dir,
    )
    assert manifest["n_dates"] == 3  # 07, 09, 11
    manifest_dates = json.loads(Path(f"{out_dir}/manifest.json").read_text())["dates"]
    assert [d.rsplit("-", 1)[-1] for d in manifest_dates] == ["07", "09", "11"]


def test_missing_region_error(serving_region, checkpoint_path, cfg, out_dir) -> None:
    """An empty/absent region store fails loudly, never fabricates a cache."""
    import shutil

    empty = serving_region / "gone"
    shutil.rmtree(empty, ignore_errors=True)
    with pytest.raises(FileNotFoundError):
        build_demo_cache(
            region_dir=str(empty),
            checkpoint_path=checkpoint_path,
            cfg=cfg,
            start="2024-01-08",
            end="2024-01-08",
            step_days=1,
            region_id="bay_of_bengal",
            out_dir=out_dir,
        )
