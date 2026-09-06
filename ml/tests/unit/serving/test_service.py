"""InferenceService core tests.

RULES: model is called with model(x) and NO coords (verified 2026-09-06 —
trainer.py:109/138 and argo.py:232 both call self.model(x...) with no
day_of_year/lat/lon; coord encoder + input_proj were never trained).
Regression guard asserts this stays true.
"""

from __future__ import annotations

import math

import pytest
import torch
from oceanembed.serving.service import InferenceService, LoadedModel

N_TIME, N_CH, N_DEP, H, W = 12, 7, 15, 8, 8
LAT0, LON0 = 5.0, 45.0


class TestInferenceService:
    def test_available_dates_from_time_coord(self, serving_region, cfg):
        service = InferenceService(region_dir=serving_region, cfg=cfg)
        dates = service.available_dates()
        assert len(dates) == N_TIME
        assert dates[0] == "2024-01-01"
        assert dates[-1] == "2024-01-12"

    def test_predict_returns_mu_logvar_and_masks_land(
        self, serving_region, checkpoint_path, cfg
    ):
        service = InferenceService(region_dir=serving_region, checkpoint_path=checkpoint_path, cfg=cfg)
        mu, log_var, mask = service.predict("2024-01-12")
        assert tuple(mu.shape) == (N_DEP, H, W)
        assert tuple(log_var.shape) == (N_DEP, H, W)
        assert mask.shape == (H, W)
        # (0,0) land -> NaN; a known ocean cell -> finite
        assert torch.isnan(mu[0, 0, 0])
        assert torch.isfinite(mu[0, 2, 2])

    def test_regression_forward_called_without_coords(
        self, serving_region, checkpoint_path, cfg
    ):
        """Guard: model(x) with NO day_of_year/lat/lon kwargs."""
        from oceanembed.models.reconstruction_net import OceanEmbedNet

        model = OceanEmbedNet(
            in_channels=N_CH, out_channels=N_DEP, use_seasonal=True, use_spatial=True,
            convlstm_hidden=8, convlstm_layers=1,
        )
        service = InferenceService(
            region_dir=serving_region, checkpoint_path=checkpoint_path, cfg=cfg, model=model
        )
        service.load_model()

        calls: list[dict] = []
        original = service.model.forward

        def spy(x, **kwargs):
            calls.append(dict(kwargs))
            return original(x)

        service.model.forward = spy
        service.predict("2024-01-12")
        assert calls, "model.forward was never called"
        assert all(kwargs == {} for kwargs in calls), f"forward got coords: {calls}"

    def test_predict_out_of_range_date_raises(self, serving_region, checkpoint_path, cfg):
        service = InferenceService(region_dir=serving_region, checkpoint_path=checkpoint_path, cfg=cfg)
        with pytest.raises(ValueError):
            service.predict("2025-01-01")

    def test_predict_date_within_window_boundary_raises(
        self, serving_region, checkpoint_path, cfg
    ):
        """t < T-1 (first 6 days) cannot form a full window -> ValueError."""
        service = InferenceService(region_dir=serving_region, checkpoint_path=checkpoint_path, cfg=cfg)
        with pytest.raises(ValueError):
            service.predict("2024-01-02")

    def test_predict_profile_nearest_cell_and_land_none(
        self, serving_region, checkpoint_path, cfg
    ):
        service = InferenceService(region_dir=serving_region, checkpoint_path=checkpoint_path, cfg=cfg)
        profile_land = service.predict_profile("2024-01-12", lat=LAT0, lon=LON0)
        assert profile_land == [None] * N_DEP
        profile_ocean = service.predict_profile("2024-01-12", lat=LAT0 + 0.5, lon=LON0 + 0.5)
        assert len(profile_ocean) == N_DEP
        assert all(v is not None and math.isfinite(v) for v in profile_ocean)


class TestLoadedModel:
    def test_prefers_best_model_state(self, tmp_path):
        path = tmp_path / "ck.pt"
        torch.save(
            {
                "best_model_state": {"w": torch.ones(2, 2)},
                "model_state_dict": {"w": torch.zeros(2, 2)},
            },
            path,
        )
        assert (LoadedModel(path).state["w"] == 1.0).all()

    def test_falls_back_to_model_state_dict(self, tmp_path):
        path = tmp_path / "ck.pt"
        torch.save({"model_state_dict": {"w": torch.ones(2, 2)}}, path)
        assert (LoadedModel(path).state["w"] == 1.0).all()

    def test_missing_ckpt_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            LoadedModel(tmp_path / "nope.pt")

    def test_ckpt_without_state_raises(self, tmp_path):
        path = tmp_path / "ck.pt"
        torch.save({"epoch": 1}, path)
        with pytest.raises(KeyError):
            LoadedModel(path)
