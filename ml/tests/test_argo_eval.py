"""Tests for ARGO independent validation (evaluation-policy LOCKED, RULE 9).

Covers: profile→canonical-depth interpolation, per-depth scoring math,
date→time-index mapping, nearest-cell lookup, the OceanEmbedDataset window
helper, and the end-to-end ArgoValidator on tiny synthetic zarr fixtures.
Never fabricate: profiles that do not match (off-domain, land cell,
out-of-window) are reported as unmatched, not filled.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
import torch
from oceanembed.data.dataset import OceanEmbedDataset
from oceanembed.evaluation.argo import (
    CANONICAL_DEPTHS_M,
    ArgoProfile,
    ArgoValidator,
    date_to_time_index,
    find_nearest_cell,
    interp_to_canonical,
    score_profiles,
)

# ─────────────────────────────────────────────────────────────────────────────
# Interpolation helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestInterpToCanonical:
    def test_canonical_constants_match_contract(self):
        """LOCKED ordering from contracts/ml/model-output.schema.json."""
        assert list(CANONICAL_DEPTHS_M) == [
            0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000,
        ]

    def test_exact_level_hit(self):
        depths = np.array([0.0, 20.0, 50.0, 200.0, 1000.0])
        temps = np.array([29.0, 20.0, 14.0, 9.0, 4.0])
        out = interp_to_canonical(depths, temps)
        assert out[0] == pytest.approx(29.0)   # 0 m exact
        assert out[3] == pytest.approx(20.0)   # 20 m exact
        # 30 m sits between 20 m (20.0) and 50 m (14.0): 20 + (10/30)*(14-20)
        assert out[4] == pytest.approx(18.0)
        # 300 m between 200 m (9.0) and 1000 m (4.0): 9 + (100/800)*(4-9)
        assert out[11] == pytest.approx(8.375)
        assert out[14] == pytest.approx(4.0)   # 1000 m exact

    def test_between_depths_linear(self):
        depths = np.array([0.0, 30.0, 50.0])
        temps = np.array([30.0, 20.0, 10.0])
        out = interp_to_canonical(depths, temps)
        # index 2 = 10 m between 0 m (30.0) and 30 m (20.0): 30 + (10/30)*(20-30)
        assert out[2] == pytest.approx(30.0 - 10.0 / 30.0 * 10.0)
        # index 3 = 20 m interpolated; index 4 = 30 m exact sample → 20.0
        assert out[3] == pytest.approx(30.0 - 20.0 / 30.0 * 10.0)
        assert out[4] == pytest.approx(20.0)

    def test_out_of_range_is_nan(self):
        depths = np.array([20.0, 50.0])
        temps = np.array([25.0, 15.0])
        out = interp_to_canonical(depths, temps)
        # 0 m and 5 m are ABOVE the shallowest measurement → NaN
        assert math.isnan(out[0])
        assert math.isnan(out[1])
        # below 50 m (75..1000) also NaN
        assert math.isnan(out[6])
        assert math.isnan(out[14])

    def test_nan_levels_ignored(self):
        depths = np.array([0.0, 10.0, 20.0, 50.0])
        temps = np.array([30.0, np.nan, 25.0, 15.0])
        out = interp_to_canonical(depths, temps)
        # NaN level dropped: 10 m lands between 0 (30.0) and 20 (25.0) → 27.5
        assert out[2] == pytest.approx(27.5)
        assert out[3] == pytest.approx(25.0)

    def test_duplicate_depths_averaged(self):
        depths = np.array([0.0, 0.0, 50.0])
        temps = np.array([30.0, 28.0, 10.0])
        out = interp_to_canonical(depths, temps)
        # duplicate 0 m levels (30, 28) → mean 29; 10 m: 29 + (10/50)*(10-29)
        assert out[0] == pytest.approx(29.0)
        assert out[2] == pytest.approx(29.0 + 10.0 / 50.0 * (10.0 - 29.0))

    def test_single_finite_point_all_nan(self):
        depths = np.array([0.0, 5.0])
        temps = np.array([30.0, np.nan])
        out = interp_to_canonical(depths, temps)
        assert np.all(np.isnan(out))

    def test_empty_input_all_nan(self):
        out = interp_to_canonical(np.array([]), np.array([]))
        assert np.all(np.isnan(out))


class TestFindNearestCell:
    def test_exact_hit(self):
        lats = np.array([5.0, 5.25, 5.5])
        lons = np.array([45.0, 45.25])
        assert find_nearest_cell(5.25, 45.0, lats, lons) == (1, 0)

    def test_nearest_between_grid_points(self):
        lats = np.array([5.0, 5.25])
        lons = np.array([45.0, 45.25])
        # 5.12 → lat row 0 (|5.12-5.0|=0.12 < |5.12-5.25|=0.13)
        # 45.13 → lon col 1 (|45.13-45.25|=0.12 < |45.13-45.0|=0.13)
        assert find_nearest_cell(5.12, 45.13, lats, lons) == (0, 1)


class TestDateToTimeIndex:
    def test_exact_date(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D").values
        assert date_to_time_index(dates, np.datetime64("2024-01-08")) == 7

    def test_within_one_day_gap_matches(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D").values
        # profile at 2024-01-08 13:00 → 0.54d to 01-08, 0.46d to 01-09
        # → closest day is 01-09 (index 8)
        assert date_to_time_index(dates, np.datetime64("2024-01-08T13:00")) == 8

    def test_far_outside_returns_none(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D").values
        assert date_to_time_index(dates, np.datetime64("2024-02-01")) is None

    def test_before_start_returns_none(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D").values
        assert date_to_time_index(dates, np.datetime64("2023-12-30")) is None


# ─────────────────────────────────────────────────────────────────────────────
# Scoring math
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreProfiles:
    def test_perfect_prediction(self):
        preds = np.full((2, 15), np.nan)
        obs = np.full((2, 15), np.nan)
        for d in range(15):
            preds[:, d] = d + 1.0
            obs[:, d] = d + 1.0
        m = score_profiles(preds, obs)
        assert m["rmse"] == pytest.approx(0.0)
        assert m["bias"] == pytest.approx(0.0)
        assert m["corr"] == pytest.approx(1.0)
        assert m["n_total"] == 30
        assert m["rmse_depth_3"] == pytest.approx(0.0)

    def test_constant_offset_hand_computed(self):
        preds = np.full((1, 15), 26.0)
        obs = np.full((1, 15), 25.0)  # obs colder by 1
        obs[0, 5] = np.nan  # depth 5 (75 m) invalid → drop
        m = score_profiles(preds, obs)
        assert m["n_total"] == 14
        assert m["bias"] == pytest.approx(1.0)
        assert m["rmse"] == pytest.approx(1.0)
        assert m["n_depth_5"] == 0
        assert math.isnan(m["rmse_depth_5"])

    def test_corr_nan_when_constant(self):
        # constant predictions → undefined correlation → NaN, not a fake number
        preds = np.full((3, 15), 20.0)
        obs = np.array([[20.0 + i] * 15 for i in range(3)])
        m = score_profiles(preds, obs)
        assert math.isnan(m["corr"])
        assert m["rmse"] == pytest.approx(np.sqrt(np.mean(np.arange(3.0) ** 2)))

    def test_corr_needs_two_points(self):
        preds = np.full((1, 15), 20.0)
        obs = np.full((1, 15), 19.0)
        m = score_profiles(preds, obs)
        assert math.isnan(m["corr"])  # single profile → corr undefined


# ─────────────────────────────────────────────────────────────────────────────
# Dataset window helper
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildWindow:
    def test_matches_getitem_contract(self, tiny_region):
        ds = OceanEmbedDataset(tiny_region, temporal_window=7, normalize=True)
        # window ending at t corresponds to sample idx = t - T + 1
        x_from_getitem = ds[1][0]  # idx=1 → window days [1..7] → t=7
        x_from_window = ds.build_window(7)
        assert torch.allclose(x_from_getitem, x_from_window)

    def test_rejects_too_early_index(self, tiny_region):
        ds = OceanEmbedDataset(tiny_region, temporal_window=7, normalize=True)
        with pytest.raises(IndexError):
            ds.build_window(5)  # t < T-1


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end ArgoValidator on synthetic data
# ─────────────────────────────────────────────────────────────────────────────

class FakeModel:
    """Stands in for OceanEmbedNet: returns fixed per-depth temps (degC)."""

    def __init__(self, temps: np.ndarray):
        self.temps = np.asarray(temps, float)

    def to(self, device):  # noqa: A003 - interface parity
        return self

    def eval(self):
        return self

    def __call__(self, x: torch.Tensor):
        H, W = x.shape[3], x.shape[4]
        mu = np.broadcast_to(self.temps[:, None, None], (15, H, W)).copy()
        mu_t = torch.as_tensor(mu, dtype=torch.float32).unsqueeze(0)
        return mu_t, torch.zeros_like(mu_t)


def _profile(source_id, date, depth_hi, temps_at_hi):
    """Profile with two levels: 0 m (28.0) and depth_hi (temp_at_hi)."""
    return ArgoProfile(
        source_id=source_id,
        date=np.datetime64(date),
        lat=5.0,
        lon=45.25,  # ocean cell (0,1)
        depths_m=np.array([0.0, depth_hi], dtype=float),
        temps_c=np.array([28.0, temps_at_hi], dtype=float),
    )


class TestArgoValidator:
    def test_matches_and_scores(self, tiny_region):
        ds = OceanEmbedDataset(tiny_region, temporal_window=7, normalize=True)
        # Model predicts 28.0 everywhere; profiles shallow enough to leave
        # deep canonical depths NaN (reported honestly, not scored).
        model = FakeModel(np.full(15, 28.0))
        validator = ArgoValidator(ds, model)

        profiles = [
            _profile("wmo1_001", "2024-01-08", depth_hi=50.0, temps_at_hi=28.0),  # hit
            _profile("wmo2_001", "2024-01-09", depth_hi=100.0, temps_at_hi=28.0),  # hit
        ]
        report, records = validator.validate(profiles)

        assert report["n_profiles"] == 2
        assert report["n_matched"] == 2
        assert report["n_unmatched"] == 0
        # Observed at 0 m = 28.0 for both, prediction 28.0 → perfect at depth 0
        assert report["n_depth_0"] == 2
        assert report["rmse_depth_0"] == pytest.approx(0.0)
        # Depth 14 (1000 m): both profiles stop at 100 m → honest NaN
        assert report["n_depth_14"] == 0
        assert math.isnan(report["rmse_depth_14"])

    def test_perfect_but_biased_profile(self, tiny_region):
        ds = OceanEmbedDataset(tiny_region, temporal_window=7, normalize=True)
        model = FakeModel(np.full(15, 30.0))  # predicts 30.0
        profiles = [_profile("wmo9_001", "2024-01-08", depth_hi=50.0, temps_at_hi=28.0)]
        report, _ = validator_report(ds, model, profiles)
        # obs: 0m=28.0, 50m=28.0 → interp at 10..30 = 28.0; pred 30.0 → bias +2
        assert report["n_matched"] == 1
        assert report["bias_depth_0"] == pytest.approx(2.0)
        assert report["rmse_depth_0"] == pytest.approx(2.0)

    def test_out_of_window_unmatched(self, tiny_region):
        ds = OceanEmbedDataset(tiny_region, temporal_window=7, normalize=True)
        model = FakeModel(np.full(15, 28.0))
        # 2024-01-03 → t=2 < T-1=6 → cannot build the 7-day window
        too_early = _profile("wmo3_001", "2024-01-03", depth_hi=50.0, temps_at_hi=28.0)
        # 2024-02-01 → beyond the dataset range
        too_late = _profile("wmo4_001", "2024-02-01", depth_hi=50.0, temps_at_hi=28.0)
        report, records = ArgoValidator(ds, model).validate([too_early, too_late])
        assert report["n_profiles"] == 2
        assert report["n_matched"] == 0
        assert report["n_unmatched"] == 2  # honest zero, never fabricated
        assert records[0]["matched"] is False

    def test_land_cell_unmatched(self, tiny_region):
        ds = OceanEmbedDataset(tiny_region, temporal_window=7, normalize=True)
        model = FakeModel(np.full(15, 28.0))
        land_profile = ArgoProfile(
            source_id="wmo5_001",
            date=np.datetime64("2024-01-08"),
            lat=5.0,   # (0,0) → mask == 0 (land)
            lon=45.0,
            depths_m=np.array([0.0, 50.0]),
            temps_c=np.array([28.0, 28.0]),
        )
        report, records = ArgoValidator(ds, model).validate([land_profile])
        assert report["n_matched"] == 0
        assert report["n_unmatched"] == 1
        assert records[0]["reason"] == "land"

    def test_per_depth_metrics_summary_present(self, tiny_region):
        ds = OceanEmbedDataset(tiny_region, temporal_window=7, normalize=True)
        model = FakeModel(np.full(15, 28.0))
        profiles = [_profile("wmo6_001", "2024-01-08", depth_hi=50.0, temps_at_hi=28.0)]
        report, _ = ArgoValidator(ds, model).validate(profiles)
        for d in range(15):
            assert f"rmse_depth_{d}" in report
            assert f"bias_depth_{d}" in report
            assert f"corr_depth_{d}" in report
            assert f"n_depth_{d}" in report


def validator_report(ds, model, profiles):
    return ArgoValidator(ds, model).validate(profiles)
