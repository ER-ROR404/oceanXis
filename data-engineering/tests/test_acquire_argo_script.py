"""Tests for the ARGO acquisition entry script (offline).

Covers: end-to-end offline acquisition against a synthetic tensor store,
the --download fetch path (mocked), and honest failure modes (unknown
region, nothing in the validation window, unusable profiles).
No network access.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent
    / "data-engineering"
    / "scripts"
    / "acquire_argo.py"
)
spec = importlib.util.spec_from_file_location("acquire_argo", _SCRIPT)
acquire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acquire)

INDEX_SAMPLE = """# ar_index_global_prof.txt
file,date,latitude,longitude,ocean,profiler_type,institution,date_update,parameters
dac/aoml/4903456/4903456_001.nc,20240128,8.51,88.19,I,846,AOML,20240129,TEMP
dac/aoml/4903456/4903456_002.nc,20240210,8.60,88.40,I,846,AOML,20240211,TEMP
dac/meds/6902914/6902914_0123.nc,20240301,22.50,79.80,I,846,MEDS,20240302,TEMP
"""


def _juld(d: date) -> float:
    return (np.datetime64(d) - np.datetime64("1950-01-01")) / np.timedelta64(1, "D") + 0.5


def _profile_nc(path: Path, dasdate: date) -> None:
    ds = xr.Dataset(
        {
            "PRES": (("N_PROF", "N_LEVELS"), [[4.9, 9.8]]),
            "TEMP": (("N_PROF", "N_LEVELS"), [[28.4, 28.2]]),
            "PRES_QC": (("N_PROF", "N_LEVELS"), [["1", "1"]]),
            "TEMP_QC": (("N_PROF", "N_LEVELS"), [["1", "1"]]),
            "JULD": ("N_PROF", [_juld(dasdate)]),
            "JULD_QC": ("N_PROF", ["1"]),
            "LATITUDE": ("N_PROF", [8.51]),
            "LONGITUDE": ("N_PROF", [88.19]),
        }
    )
    ds.to_netcdf(path)


@pytest.fixture
def tensor_store(tmp_path: Path) -> Path:
    region = tmp_path / "region"
    time = np.arange("2024-01-01", 30, dtype="datetime64[D]")
    ds = xr.Dataset({"time": ("time", time)})
    ds.to_zarr(region / "X.zarr")
    return region


@pytest.fixture
def regions_yaml(tmp_path: Path) -> Path:
    p = tmp_path / "regions.yaml"
    p.write_text(
        "regions:\n"
        "  bay_of_bengal:\n"
        "    longitude: {min: 80.0, max: 100.0}\n"
        "    latitude: {min: 5.0, max: 22.0}\n"
    )
    return p


@pytest.fixture
def cache(tmp_path: Path) -> Path:
    d = tmp_path / "gdac"
    (d / "dac" / "aoml" / "4903456").mkdir(parents=True)
    return d


def _index_file(tmp_path: Path) -> Path:
    p = tmp_path / "index.txt"
    p.write_text(INDEX_SAMPLE)
    return p


class TestAcquireArgo:
    def test_end_to_end_offline(
        self, tmp_path: Path, tensor_store: Path, regions_yaml: Path, cache: Path
    ) -> None:
        # 30-day tensor -> validation window 2024-01-27..2024-01-30
        # (n_samples=24, n_val=4, first val target idx=26).
        _profile_nc(cache / "dac" / "aoml" / "4903456" / "4903456_001.nc", date(2024, 1, 28))
        out = tmp_path / "profiles.json"
        rc = acquire.main(
            [
                "--region-id", "bay_of_bengal",
                "--regions-yaml", str(regions_yaml),
                "--tensor-store", str(tensor_store),
                "--gdac-cache", str(cache),
                "--out", str(out),
                "--index-file", str(_index_file(tmp_path)),
            ]
        )
        assert rc == 0
        entries = json.loads(out.read_text())
        assert isinstance(entries, list)
        assert [e["source_id"] for e in entries] == ["4903456_001"]
        prov = json.loads(out.with_suffix(".provenance.json").read_text())
        assert prov["validation_window"] == {"start": "2024-01-27", "end": "2024-01-30"}
        assert prov["n_selected"] == 1  # second row falls in the TRAIN period
        assert prov["region_id"] == "bay_of_bengal"

    def test_download_fetches_selected_missing_files(
        self, tmp_path: Path, tensor_store: Path, regions_yaml: Path, cache: Path
    ) -> None:
        fetched: list[str] = []

        def fake_fetch(url: str, dest: Path) -> None:
            fetched.append(url)
            dest.parent.mkdir(parents=True, exist_ok=True)
            _profile_nc(dest, date(2024, 1, 28))

        acquire.fetch = fake_fetch  # type: ignore[assignment]
        out = tmp_path / "profiles.json"
        rc = acquire.main(
            [
                "--region-id", "bay_of_bengal",
                "--regions-yaml", str(regions_yaml),
                "--tensor-store", str(tensor_store),
                "--gdac-cache", str(cache),
                "--out", str(out),
                "--index-file", str(_index_file(tmp_path)),
                "--download",
            ]
        )
        assert rc == 0
        # --index-file given -> only the selected profile file is fetched.
        assert len(fetched) == 1
        assert fetched[0].endswith("dac/aoml/4903456/4903456_001.nc")

    def test_unknown_region_fails(
        self, tmp_path: Path, tensor_store: Path, regions_yaml: Path, cache: Path
    ) -> None:
        rc = acquire.main(
            [
                "--region-id", "atlantis",
                "--regions-yaml", str(regions_yaml),
                "--tensor-store", str(tensor_store),
                "--gdac-cache", str(cache),
                "--out", str(tmp_path / "p.json"),
                "--index-file", str(_index_file(tmp_path)),
            ]
        )
        assert rc == 1

    def test_zero_profiles_in_window_fails(
        self, tmp_path: Path, tensor_store: Path, regions_yaml: Path, cache: Path
    ) -> None:
        index = tmp_path / "index.txt"
        index.write_text(
            "file,date,latitude,longitude,ocean,profiler_type,institution,date_update,parameters\n"
            "dac/aoml/4903456/4903456_009.nc,20240110,8.51,88.19,I,846,AOML,20240111,TEMP\n"
        )
        rc = acquire.main(
            [
                "--region-id", "bay_of_bengal",
                "--regions-yaml", str(regions_yaml),
                "--tensor-store", str(tensor_store),
                "--gdac-cache", str(cache),
                "--out", str(tmp_path / "p.json"),
                "--index-file", str(index),
            ]
        )
        assert rc == 2
        assert not (tmp_path / "p.json").exists()

    def test_index_file_required_without_download(
        self, tmp_path: Path, tensor_store: Path, regions_yaml: Path, cache: Path
    ) -> None:
        rc = acquire.main(
            [
                "--region-id", "bay_of_bengal",
                "--regions-yaml", str(regions_yaml),
                "--tensor-store", str(tensor_store),
                "--gdac-cache", str(cache),
                "--out", str(tmp_path / "p.json"),
            ]
        )
        assert rc == 1
