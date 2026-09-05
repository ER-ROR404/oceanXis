"""Tests for the Copernicus Marine client wrapper.

These tests mock the `copernicusmarine` library entirely — no live network.
Covers the credential handling contract:
  - describe() must NOT pass username/password (metadata-only call in copernicusmarine >= 2.x)
  - from_env() raises if credentials are missing
  - subset() DOES pass credentials and properly shapes the bbox
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent
_src_path = str(_project_root / "data-engineering" / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from oceanembed_data.catalog import (
    CANONICAL_DEPTHS_M,
    GLORYS_DOWNLOAD_MAX_DEPTH_M,
    DatasetCatalog,
)
from oceanembed_data.copernicus import CopernicusClient, SubsetResult
from oceanembed_data.regions import RegionBounds, RegionRegistry


@pytest.fixture
def region_bounds() -> RegionBounds:
    return RegionBounds(
        id="bay_of_bengal",
        lon_min=80.0,
        lon_max=100.0,
        lat_min=5.0,
        lat_max=22.0,
        description="test",
    )


class TestFromEnv:
    def test_from_env_with_credentials(self, monkeypatch) -> None:
        monkeypatch.setenv("COPERNICUSMARINE_SERVICE_USERNAME", "user")
        monkeypatch.setenv("COPERNICUSMARINE_SERVICE_PASSWORD", "pass")
        client = CopernicusClient.from_env()
        assert client.username == "user"
        assert client.password == "pass"

    def test_from_env_missing_username(self, monkeypatch) -> None:
        monkeypatch.delenv("COPERNICUSMARINE_SERVICE_USERNAME", raising=False)
        monkeypatch.setenv("COPERNICUSMARINE_SERVICE_PASSWORD", "pass")
        with pytest.raises(ValueError, match="credentials not found"):
            CopernicusClient.from_env()

    def test_from_env_missing_password(self, monkeypatch) -> None:
        monkeypatch.setenv("COPERNICUSMARINE_SERVICE_USERNAME", "user")
        monkeypatch.delenv("COPERNICUSMARINE_SERVICE_PASSWORD", raising=False)
        with pytest.raises(ValueError, match="credentials not found"):
            CopernicusClient.from_env()


class TestDescribe:
    def test_describe_does_not_pass_credentials(self) -> None:
        """describe() is metadata-only; credentials must NOT be forwarded (regression)."""
        client = CopernicusClient(username="user", password="pass")
        fake_catalogue = MagicMock()
        fake_catalogue.model_dump.return_value = {"products": [{"id": "x"}]}
        with patch("copernicusmarine.describe", return_value=fake_catalogue) as mock_describe:
            result = client.describe("cmems_mod_glo_phy_my_0.083deg_P1D-m")
        # The regression: username/password were previously forwarded and caused TypeError
        assert "username" not in mock_describe.call_args.kwargs
        assert "password" not in mock_describe.call_args.kwargs
        assert mock_describe.call_args.kwargs["dataset_id"] == "cmems_mod_glo_phy_my_0.083deg_P1D-m"
        assert result == {"products": [{"id": "x"}]}

    def test_describe_show_all_versions_forwarded(self) -> None:
        client = CopernicusClient(username="user", password="pass")
        fake_catalogue = MagicMock()
        fake_catalogue.model_dump.return_value = {"versions": []}
        with patch("copernicusmarine.describe", return_value=fake_catalogue) as mock_describe:
            client.describe("DS", show_all_versions=True)
        assert mock_describe.call_args.kwargs["show_all_versions"] is True

    def test_describe_fallback_to_raw_str(self) -> None:
        """Non-Pydantic return (old API style) degrades to {'raw': ...}."""
        client = CopernicusClient(username="user", password="pass")
        with patch("copernicusmarine.describe", return_value="catalogue-str") as mock_describe:
            result = client.describe("DS")
        assert mock_describe.called
        assert result == {"raw": "catalogue-str"}

    def test_describe_raises_on_error(self) -> None:
        client = CopernicusClient(username="user", password="pass")
        with patch("copernicusmarine.describe", side_effect=RuntimeError("net down")) as m:
            with pytest.raises(RuntimeError, match="net down"):
                client.describe("DS")
        assert m.called


class TestSubset:
    def test_subset_passes_credentials_and_bbox(self, region_bounds) -> None:
        client = CopernicusClient(username="user", password="pass")
        fake_response = MagicMock()
        fake_response.file_path = "/tmp/out.nc"
        with patch("copernicusmarine.subset", return_value=fake_response) as mock_subset:
            result = client.subset(
                dataset_id="CAT",
                variable="sla",
                region_bounds=region_bounds,
                start_date="2022-01-01",
                end_date="2022-01-31",
                output_dir="/tmp/out",
            )
        kwargs = mock_subset.call_args.kwargs
        assert kwargs["username"] == "user"
        assert kwargs["password"] == "pass"
        assert kwargs["minimum_longitude"] == 80.0
        assert kwargs["maximum_longitude"] == 100.0
        assert kwargs["minimum_latitude"] == 5.0
        assert kwargs["maximum_latitude"] == 22.0
        assert kwargs["start_datetime"] == "2022-01-01"
        assert kwargs["end_datetime"] == "2022-01-31"
        assert result.success is True
        assert result.output_path == Path("/tmp/out.nc")

    def test_subset_dry_run(self, region_bounds) -> None:
        client = CopernicusClient(username="user", password="pass")
        with patch("copernicusmarine.subset", return_value=MagicMock()) as mock_subset:
            result = client.subset(
                dataset_id="CAT",
                variable="sos",
                region_bounds=region_bounds,
                start_date="2022-01-01",
                end_date="2022-01-02",
                dry_run=True,
            )
        assert mock_subset.call_args.kwargs["dry_run"] is True
        assert result.success is True
        assert result.output_path is None

    def test_subset_failure_is_captured(self, region_bounds) -> None:
        client = CopernicusClient(username="user", password="pass")
        with patch("copernicusmarine.subset", side_effect=RuntimeError("boom")):
            result = client.subset(
                dataset_id="CAT",
                variable="uo",
                region_bounds=region_bounds,
                start_date="2022-01-01",
                end_date="2022-01-02",
            )
        assert result.success is False
        assert "boom" in result.error

    def test_glorys_download_depth_brackets_1000m(self) -> None:
        """GLORYS downloads must request depth beyond the deepest canonical
        depth (1000m) so vertical interpolation to 1000m is bracketed, never
        extrapolated.

        Regression: maximum_depth=1000.0 returned native levels only up to
        902.34m — the 1000m target was silently filled with 902m data.
        """
        assert GLORYS_DOWNLOAD_MAX_DEPTH_M > max(CANONICAL_DEPTHS_M)

        catalog = DatasetCatalog.from_yaml(
            _project_root / "config" / "datasets.yaml"
        )
        glorys = catalog.training_target()
        assert glorys.dataset_id == "cmems_mod_glo_phy_my_0.083deg_P1D-m"

        entry = catalog.entries.get("glorys_temperature")
        assert entry is not None

        # The download script must use the contract constant, not a
        # hardcoded shallow depth that fails to bracket 1000m.
        script = (
            _project_root / "scripts" / "download_historical.py"
        ).read_text()
        assert "GLORYS_DOWNLOAD_MAX_DEPTH_M" in script
        assert "maximum_depth=1000.0" not in script

    def test_subset_shape_read_from_file(self, region_bounds, tmp_path) -> None:
        client = CopernicusClient(username="user", password="pass")
        nc_file = tmp_path / "out.nc"
        # Create a minimal NetCDF to read dims from
        import xarray as xr
        import numpy as np
        ds = xr.Dataset(
            {"sla": (("time", "latitude", "longitude"), np.zeros((5, 6, 7)))},
            coords={
                "time": np.arange(5),
                "latitude": np.arange(6),
                "longitude": np.arange(7),
            },
        )
        ds.to_netcdf(nc_file)
        fake_response = MagicMock()
        fake_response.file_path = str(nc_file)
        with patch("copernicusmarine.subset", return_value=fake_response):
            result = client.subset(
                dataset_id="CAT",
                variable="sla",
                region_bounds=region_bounds,
                start_date="2022-01-01",
                end_date="2022-01-05",
            )
        assert result.shape == (5, 6, 7)