"""Inference HTTP server tests (ml side, FastAPI on :8080).

Contract file: contracts/ml/inference-rpc.schema.json (created with this
server — the wire format is a new, versioned interface).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def server(tmp_path, serving_region, checkpoint_path, cfg, monkeypatch):
    """TestClient wrapping the server wired to the synthetic region."""
    import shutil

    region_root = tmp_path / "bay_of_bengal"
    if region_root.exists():
        shutil.rmtree(region_root)
    shutil.copytree(serving_region, region_root)

    from oceanembed.serving.server import create_app

    # Config matching the synthetic checkpoint's architecture (hidden=8),
    # loaded through the same HYBRID_CFG_PATH env path used in production.
    (region_root / "hybrid_v1.yaml").write_text(
        "model:\n"
        "  architecture: oceanembed_net\n"
        "  in_channels: 7\n"
        "  out_channels: 15\n"
        "  uncertainty: true\n"
        "  convlstm_hidden: 8\n"
        "  convlstm_layers: 1\n"
        "  use_seasonal: true\n"
        "  use_spatial: true\n"
    )

    monkeypatch.setenv("TENSOR_DIR", str(tmp_path))
    monkeypatch.setenv("REGION", "bay_of_bengal")
    monkeypatch.setenv("CHECKPOINT_PATH", str(region_root / "best.pt"))
    monkeypatch.setenv("HYBRID_CFG_PATH", str(region_root / "hybrid_v1.yaml"))
    with TestClient(create_app()) as client:
        yield client


class TestHealth:
    def test_health_ok(self, server):
        resp = server.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["model"] == "hybrid_v1"
        assert "dates" in body

    def test_health_503_when_no_checkpoint(self, tmp_path, serving_region, cfg, monkeypatch):
        """Model not loaded -> 503 with a typed code (honest, not 200)."""
        import shutil

        from oceanembed.serving.server import create_app

        region_root = tmp_path / "bay_of_bengal"
        if region_root.exists():
            shutil.rmtree(region_root)
        shutil.copytree(serving_region, region_root)

        monkeypatch.setenv("TENSOR_DIR", str(tmp_path))
        monkeypatch.setenv("REGION", "bay_of_bengal")
        monkeypatch.setenv("CHECKPOINT_PATH", str(region_root / "missing.pt"))
        monkeypatch.setenv("HYBRID_CFG_PATH", "")
        client = TestClient(create_app())
        with client:
            resp = client.get("/health")
            assert resp.status_code == 503
            body = resp.json()
            assert body["status"] == "error"
            assert body["code"] == "MODEL_NOT_LOADED"


class TestPredict:
    def test_predict_valid_date(self, server):
        resp = server.post("/predict", json={"region": "bay_of_bengal", "date": "2024-01-12"})
        assert resp.status_code == 200
        body = resp.json()
        # Contract: flat lists of floats for mu/log_var, plus series metadata.
        assert "mu" in body and "log_var" in body
        assert len(body["mu"]) == 15  # depths
        assert len(body["mu"][0]) == 8 * 8  # H*W -> 64
        assert body["series_id"].startswith("hybrid_v1-")

    def test_predict_unknown_region_404(self, server):
        resp = server.post("/predict", json={"region": "atlantis", "date": "2024-01-12"})
        assert resp.status_code == 404
        assert resp.json()["code"] == "DATA_NOT_AVAILABLE"

    def test_predict_bad_date_404(self, server):
        resp = server.post("/predict", json={"region": "bay_of_bengal", "date": "2030-01-01"})
        assert resp.status_code == 404
        assert resp.json()["code"] == "DATA_NOT_AVAILABLE"

    def test_predict_missing_fields_422(self, server):
        resp = server.post("/predict", json={"region": "bay_of_bengal"})
        assert resp.status_code == 422

    def test_predict_contract_conformance(self, server):
        """Response must validate against contracts/ml/inference-rpc.schema.json."""
        import json as _json
        from pathlib import Path

        import jsonschema

        resp = server.post("/predict", json={"region": "bay_of_bengal", "date": "2024-01-12"})
        schema = _json.loads(
            Path(__file__).resolve().parents[4]
            .joinpath("contracts", "ml", "inference-rpc.schema.json")
            .read_text()
        )
        jsonschema.validate(resp.json(), schema)


class TestPredictProfile:
    """POST /predict_profile — nearest-cell semantics live ml-side (RULE 3)."""

    def test_predict_profile_valid(self, server):
        resp = server.post(
            "/predict_profile",
            json={"region": "bay_of_bengal", "date": "2024-01-12", "lat": 12.0, "lon": 90.0},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["temperatures"]) == 15
        assert body["series_id"].startswith("hybrid_v1-")
        # Nearest-cell snap is returned honestly.
        assert isinstance(body["latitude"], float)
        assert isinstance(body["longitude"], float)

    def test_predict_profile_land_cell_all_null(self, server):
        """(lat, lon) nearest to the synthetic land cell (0,0) -> honest nulls."""
        resp = server.post(
            "/predict_profile",
            json={"region": "bay_of_bengal", "date": "2024-01-12", "lat": 5.0, "lon": 45.0},
        )
        assert resp.status_code == 200
        assert resp.json()["temperatures"] == [None] * 15

    def test_predict_profile_bad_date_404(self, server):
        resp = server.post(
            "/predict_profile",
            json={"region": "bay_of_bengal", "date": "2030-01-01", "lat": 12.0, "lon": 90.0},
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "DATA_NOT_AVAILABLE"

    def test_predict_profile_unknown_region_404(self, server):
        resp = server.post(
            "/predict_profile",
            json={"region": "atlantis", "date": "2024-01-12", "lat": 12.0, "lon": 90.0},
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "DATA_NOT_AVAILABLE"

    def test_predict_profile_missing_fields_422(self, server):
        resp = server.post("/predict_profile", json={"region": "bay_of_bengal", "date": "2024-01-12"})
        assert resp.status_code == 422

    def test_predict_profile_contract_conformance(self, server):
        """Profile RPC must validate against inference-profile-rpc.schema.json."""
        import json as _json
        from pathlib import Path

        import jsonschema

        resp = server.post(
            "/predict_profile",
            json={"region": "bay_of_bengal", "date": "2024-01-12", "lat": 12.0, "lon": 90.0},
        )
        schema = _json.loads(
            Path(__file__).resolve().parents[4]
            .joinpath("contracts", "ml", "inference-profile-rpc.schema.json")
            .read_text()
        )
        jsonschema.validate(resp.json(), schema)
