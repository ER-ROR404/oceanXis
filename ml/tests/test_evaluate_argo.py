"""Tests for the evaluate_argo entry point (RULE 9 wiring)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import torch

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "evaluate_argo.py"
_spec = importlib.util.spec_from_file_location("evaluate_argo", _SCRIPT)
_entry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_entry)

load_profiles = _entry.load_profiles
main = _entry.main
run_argo_validation = _entry.run_argo_validation

MINI_CONFIG = """\
experiment:
  name: argo-test
data:
  temporal_window: 7
  batch_size: 8
  val_fraction: 0.2
model:
  in_channels: 7
  out_channels: 15
  convlstm_hidden: 4
  convlstm_layers: 1
training:
  epochs: 1
  lr: 0.001
  seed: 42
  early_stopping_patience: 15
"""


def _write_config(tmp_path) -> None:
    (tmp_path / "config.yaml").write_text(MINI_CONFIG)


def _write_profiles(tmp_path, n=2, ocean_cell=True) -> None:
    profiles = []
    for i in range(n):
        profiles.append(
            {
                "source_id": f"wmo{i}_001",
                "date": "2024-01-08",
                "lat": 5.0,
                "lon": 45.25 if ocean_cell else 45.0,  # ocean / land
                "depths_m": [0.0, 50.0],
                "temps_c": [28.0, 27.0],
            }
        )
    (tmp_path / "profiles.json").write_text(json.dumps(profiles))


class RecordingModel:
    """Stub OceanEmbedNet: records weights load; returns a fixed profile."""

    def __init__(self, **kwargs):
        self.state = None
        self.device = "cpu"
        self.temps = np.full(15, 28.0)

    def load_state_dict(self, state) -> None:
        self.state = state

    def to(self, device):
        self.device = device
        return self

    def eval(self):
        return self

    def __call__(self, x: torch.Tensor):
        H, W = x.shape[3], x.shape[4]
        mu = np.broadcast_to(self.temps[:, None, None], (15, H, W)).copy()
        return (
            torch.as_tensor(mu, dtype=torch.float32).unsqueeze(0),
            torch.zeros(1, 15, H, W),
        )


class TestRunArgoValidation:
    def test_end_to_end_writes_report(self, tmp_path, tiny_region, monkeypatch):
        _write_config(tmp_path)
        _write_profiles(tmp_path)

        # Stand-in model that records weight loading
        recording = RecordingModel()
        monkeypatch.setattr(
            "oceanembed.models.reconstruction_net.OceanEmbedNet",
            lambda **kw: recording,
        )
        # real checkpoint: torch.save then read back
        ckpt = {"best_model_state": {"dummy": torch.tensor(1.0)}}
        torch.save(ckpt, tmp_path / "best.pt")

        artifacts = tmp_path / "artifacts"
        payload = run_argo_validation(
            config_path=tmp_path / "config.yaml",
            checkpoint_path=tmp_path / "best.pt",
            data_dir=tiny_region,
            argo_profiles_path=tmp_path / "profiles.json",
            artifacts_dir=artifacts,
            device="cpu",
        )

        # weights were loaded onto the model
        assert recording.state is not None
        # honest bookkeeping
        assert payload["n_profiles"] == 2
        assert payload["n_matched"] == 2
        assert payload["n_unmatched"] == 0
        assert payload["metrics"]["rmse_depth_0"] == 0.0  # 28.0 vs 28.0
        assert payload["metrics"]["bias_depth_0"] == 0.0

        # report file written and round-trips
        report = json.loads((artifacts / "argo_report.json").read_text())
        assert report["validation"] == "argo"
        assert report["n_matched"] == 2
        assert len(report["profiles"]) == 2
        assert report["profiles"][0]["matched"] is True

    def test_land_cell_reported_unmatched(self, tmp_path, tiny_region, monkeypatch):
        _write_config(tmp_path)
        _write_profiles(tmp_path, n=1, ocean_cell=False)
        monkeypatch.setattr(
            "oceanembed.models.reconstruction_net.OceanEmbedNet",
            lambda **kw: RecordingModel(),
        )
        torch.save({"best_model_state": {"d": torch.tensor(1.0)}}, tmp_path / "best.pt")

        payload = run_argo_validation(
            config_path=tmp_path / "config.yaml",
            checkpoint_path=tmp_path / "best.pt",
            data_dir=tiny_region,
            argo_profiles_path=tmp_path / "profiles.json",
            artifacts_dir=tmp_path / "artifacts",
            device="cpu",
        )
        assert payload["n_matched"] == 0
        assert payload["n_unmatched"] == 1
        assert payload["profiles"][0]["reason"] == "land"

    def test_missing_checkpoint_fails_fast(self, tmp_path, tiny_region):
        _write_config(tmp_path)
        _write_profiles(tmp_path)
        with pytest.raises(FileNotFoundError):
            run_argo_validation(
                config_path=tmp_path / "config.yaml",
                checkpoint_path=tmp_path / "nope.pt",
                data_dir=tiny_region,
                argo_profiles_path=tmp_path / "profiles.json",
                artifacts_dir=tmp_path / "artifacts",
                device="cpu",
            )


class TestLoadProfiles:
    def test_parses_valid_profiles(self, tmp_path):
        (tmp_path / "p.json").write_text(
            json.dumps(
                [
                    {
                        "source_id": "6902914_0123",
                        "date": "2024-01-08T13:00:00",
                        "lat": 8.5,
                        "lon": 88.2,
                        "depths_m": [0.0, 5.1, 20.0],
                        "temps_c": [28.3, 28.2, 20.1],
                    }
                ]
            )
        )
        profiles = load_profiles(tmp_path / "p.json")
        assert len(profiles) == 1
        assert profiles[0].source_id == "6902914_0123"
        assert profiles[0].temps_c.shape == (3,)

    def test_level_mismatch_rejected(self, tmp_path):
        (tmp_path / "p.json").write_text(
            json.dumps(
                [
                    {
                        "source_id": "x",
                        "date": "2024-01-08",
                        "lat": 8.5,
                        "lon": 88.2,
                        "depths_m": [0.0, 5.1],
                        "temps_c": [28.3],
                    }
                ]
            )
        )
        import pytest

        with pytest.raises(ValueError):
            load_profiles(tmp_path / "p.json")


class TestMain:
    def test_missing_checkpoint_exit_1(self, tmp_path, capsys):
        rc = main(
            [
                "--config", str(tmp_path / "config.yaml"),
                "--checkpoint", str(tmp_path / "nope.pt"),
                "--data-dir", str(tmp_path),
                "--argo-profiles", str(tmp_path / "p.json"),
                "--artifacts-dir", str(tmp_path / "artifacts"),
            ]
        )
        assert rc == 1
        assert "ERROR" in capsys.readouterr().err
