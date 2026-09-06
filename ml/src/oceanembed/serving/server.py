"""Inference HTTP server (ml side, :8080).

Exposes the trained model to the backend over HTTP. This is the ONLY place
the backend may acquire model predictions (RULE 3: backend never imports
torch). The wire format is versioned in contracts/ml/inference-rpc.schema.json.

Run:  python -m oceanembed.serving.server
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from oceanembed.evaluation.argo import find_nearest_cell
from oceanembed.serving.service import InferenceService

SERVICE_VERSION = "0.1.0"
MODEL_NOT_LOADED = "MODEL_NOT_LOADED"
DATA_NOT_AVAILABLE = "DATA_NOT_AVAILABLE"
REGIONS = ("bay_of_bengal", "arabian_sea", "north_indian_ocean")

# Built-in model config mirrors ml/configs/hybrid_v1.yaml (fallback when
# HYBRID_CFG_PATH is not set — the config file may not be present in the
# container image).
DEFAULT_CFG: dict[str, Any] = {
    "architecture": "oceanembed_net",
    "in_channels": 7,
    "out_channels": 15,
    "uncertainty": True,
    "convlstm_hidden": 128,
    "convlstm_layers": 1,
    "use_seasonal": True,
    "use_spatial": True,
}


class PredictRequest(BaseModel):
    region: str = Field(..., description="Region id")
    date: str = Field(..., description="ISO-8601 date")


class PredictProfileRequest(BaseModel):
    region: str = Field(..., description="Region id")
    date: str = Field(..., description="ISO-8601 date")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Requested latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Requested longitude")


def _cfg() -> dict[str, Any]:
    path = os.environ.get("HYBRID_CFG_PATH", "")
    if not path:
        return dict(DEFAULT_CFG)
    import yaml

    with open(path) as f:
        cfg = yaml.safe_load(f)
    return dict(cfg["model"])


def _region_dir() -> Path:
    """Region tensor store: {TENSOR_DIR}/{REGION} (REGION default bay_of_bengal)."""
    tensor_dir = Path(os.environ.get("TENSOR_DIR", "."))
    region = os.environ.get("REGION", "bay_of_bengal")
    return tensor_dir / region


def _checkpoint_environ() -> str:
    return os.environ.get("CHECKPOINT_PATH", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eagerly load the model at startup; failures are visible via /health.

    A missing checkpoint must NOT crash the process (503 is honest) so the
    demo cache fallback can still serve the frontend.
    """
    app.state.service = None
    app.state.init_error: str | None = None
    try:
        cfg = _cfg()
        service = InferenceService(
            region_dir=_region_dir(),
            checkpoint_path=_checkpoint_environ(),
            cfg=cfg,
        )
        service.load_model()
        app.state.service = service
    except Exception as exc:  # model not loadable -> degraded 503, not crash
        app.state.init_error = str(exc)[:300]
    yield
    app.state.service = None


def create_app() -> FastAPI:
    """App factory (testable; env-driven config)."""
    app = FastAPI(
        title="OceanEmbed ML Inference",
        description="Serves model(x) predictions on the RULE 3 HTTP boundary.",
        version=SERVICE_VERSION,
        lifespan=lifespan,
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        svc = getattr(app.state, "service", None)
        if svc is None:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "code": MODEL_NOT_LOADED,
                    "detail": getattr(app.state, "init_error", "model not loaded"),
                },
            )
        return {
            "status": "ok",
            "model": "hybrid_v1",
            "version": SERVICE_VERSION,
            "dates": svc.available_dates(),
        }

    @app.post("/predict")
    def predict(req: PredictRequest) -> dict[str, Any]:
        svc = getattr(app.state, "service", None)
        if svc is None:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "code": MODEL_NOT_LOADED},
            )
        if req.region not in REGIONS:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "code": DATA_NOT_AVAILABLE, "region": req.region},
            )
        try:
            mu, log_var, _ = svc.predict(req.date)
        except ValueError as exc:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "code": DATA_NOT_AVAILABLE, "detail": str(exc)[:300]},
            )
        # Flatten [D,H,W] -> [D, H*W] row-major (lat outer; contracts/ml layout)
        # NaN land cells serialize to null in JSON (contract allows null).
        return {
            "mu": [layer.reshape(-1).tolist() for layer in mu],
            "log_var": [layer.reshape(-1).tolist() for layer in log_var],
            "series_id": f"hybrid_v1-{req.date}",
            "date": req.date,
            "region": req.region,
            "model_version": "hybrid_v1",
        }

    @app.post("/predict_profile")
    def predict_profile(req: PredictProfileRequest) -> dict[str, Any]:
        svc = getattr(app.state, "service", None)
        if svc is None:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "code": MODEL_NOT_LOADED},
            )
        if req.region not in REGIONS:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "code": DATA_NOT_AVAILABLE, "region": req.region},
            )
        try:
            temps = svc.predict_profile(req.date, req.lat, req.lon)
        except ValueError as exc:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "code": DATA_NOT_AVAILABLE, "detail": str(exc)[:300]},
            )
        # Nearest-cell semantics live ml-side; report the snapped cell honestly.
        row, col = find_nearest_cell(req.lat, req.lon, svc.lats, svc.lons)
        return {
            "temperatures": temps,
            "series_id": f"hybrid_v1-{req.date}-cell",
            "date": req.date,
            "region": req.region,
            "model_version": "hybrid_v1",
            "latitude": float(svc.lats[row]),
            "longitude": float(svc.lons[col]),
        }

    return app


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    import uvicorn

    uvicorn.run("oceanembed.serving.server:create_app", host="0.0.0.0", port=8080, factory=True)
