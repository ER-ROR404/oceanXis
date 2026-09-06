"""Offline tests for ARGO acquisition + harmonization (data-engineering).

Covers: GDAC index parsing, bbox+date selection, temporal validation-window
computation (mirrors ml/.../dataset.py split exactly), NetCDF QC filtering,
and writing the harmonized JSON store consumed by ml/scripts/evaluate_argo.py.
No network access in tests — synthetic fixtures only.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from oceanembed_data.argo_acquire import (
    IndexRow,
    compute_validation_window,
    load_gdac_files,
    parse_gdac_profile,
    parse_index,
    select_rows,
    write_profiles_json,
)

INDEX_SAMPLE = """# ar_index_global_prof.txt
file,date,latitude,longitude,ocean,profiler_type,institution,date_update,parameters
dac/aoml/4903456/4903456_001.nc,20240615,8.51,88.19,I,846,AOML,20240616,TEMP
dac/aoml/4903456/4903456_002.nc,20240625,8.60,88.40,I,846,AOML,20240626,TEMP
dac/meds/6902914/6902914_0123.nc,20240903,22.50,79.80,I,846,MEDS,20240904,TEMP
dac/coriolis/2901673/2901673_004.nc,20241001,17.42,87.95,I,846,CORIOLIS,20241002,TEMP
"""

BOB = dict(lon_min=80.0, lon_max=100.0, lat_min=5.0, lat_max=22.0)


def _juld(d: date) -> float:
    """Days since 1950-01-01 (Argo JULD convention), mid-day."""
    return (datetime(d.year, d.month, d.day) - datetime(1950, 1, 1)).days + 0.5


def _profile_ds(
    *,
    temps: list[float] | None = None,
    pres: list[float] | None = None,
    temp_qc: list[str] | None = None,
    pres_qc: list[str] | None = None,
    temp_adj: list[float] | None = None,
    temp_adj_qc: list[str] | None = None,
    dasdate: date = date(2024, 6, 15),
    juld_qc: str = "1",
    lat: float = 8.51,
    lon: float = 88.19,
) -> xr.Dataset:
    temps = temps if temps is not None else [28.4]
    pres = pres if pres is not None else [4.9]
    n = len(temps)
    ds = xr.Dataset(
        {
            "PRES": (("N_PROF", "N_LEVELS"), [pres]),
            "TEMP": (("N_PROF", "N_LEVELS"), [temps]),
            "PRES_QC": (("N_PROF", "N_LEVELS"), [pres_qc or ["1"] * n]),
            "TEMP_QC": (("N_PROF", "N_LEVELS"), [temp_qc or ["1"] * n]),
            "JULD": ("N_PROF", [_juld(dasdate)]),
            "JULD_QC": ("N_PROF", [juld_qc]),
            "LATITUDE": ("N_PROF", [lat]),
            "LONGITUDE": ("N_PROF", [lon]),
        }
    )
    if temp_adj is not None:
        ds["TEMP_ADJUSTED"] = (("N_PROF", "N_LEVELS"), [temp_adj])
        ds["TEMP_ADJUSTED_QC"] = (
            ("N_PROF", "N_LEVELS"),
            [temp_adj_qc or ["1"] * n],
        )
    return ds


# --------------------------------------------------------------------------- #
# Index parsing
# --------------------------------------------------------------------------- #


class TestParseIndex:
    def test_parses_rows_and_skips_header(self) -> None:
        rows = parse_index(INDEX_SAMPLE)
        assert len(rows) == 4
        r0 = rows[0]
        assert r0.file == "dac/aoml/4903456/4903456_001.nc"
        assert r0.date == date(2024, 6, 15)
        assert r0.lat == 8.51
        assert r0.lon == 88.19

    def test_skips_malformed_lines(self) -> None:
        text = "# comment\nfile,date,latitude,longitude\nbad,line\n"
        rows = parse_index(text)
        assert rows == []

    def test_empty_input(self) -> None:
        assert parse_index("") == []


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #


class TestSelectRows:
    def test_bounds_inclusive(self) -> None:
        rows = parse_index(INDEX_SAMPLE)
        # Row 2 (lat 22.50, lon 79.80) is outside BoB; rows 0,1,3 inside.
        picked = select_rows(rows, **BOB)
        assert [r.file for r in picked] == [
            "dac/aoml/4903456/4903456_001.nc",
            "dac/aoml/4903456/4903456_002.nc",
            "dac/coriolis/2901673/2901673_004.nc",
        ]

    def test_boundary_values_kept(self) -> None:
        edge = IndexRow(file="f.nc", date=date(2024, 6, 1), lat=22.0, lon=100.0)
        picked = select_rows([edge], **BOB)
        assert picked == [edge]

    def test_date_window_inclusive(self) -> None:
        rows = parse_index(INDEX_SAMPLE)
        # Date-only filter: 2024-09-01..2024-09-30 keeps row 2 only.
        picked = select_rows(
            rows, min_date=date(2024, 9, 1), max_date=date(2024, 9, 30)
        )
        assert [r.file for r in picked] == [
            "dac/meds/6902914/6902914_0123.nc",
        ]

    def test_disjoint_window_returns_empty(self) -> None:
        rows = parse_index(INDEX_SAMPLE)
        picked = select_rows(
            rows, min_date=date(2030, 1, 1), max_date=date(2030, 1, 2), **BOB
        )
        assert picked == []

    def test_none_filters_pass_everything(self) -> None:
        rows = parse_index(INDEX_SAMPLE)
        assert select_rows(rows) == rows


# --------------------------------------------------------------------------- #
# Validation window (must mirror ml/.../dataset.py temporal_locked split)
# --------------------------------------------------------------------------- #


class TestComputeValidationWindow:
    def test_matches_dataset_formula(self) -> None:
        # 2-year daily axis exactly like the BoB tensor store.
        start = np.datetime64("2024-01-01")
        time = start + np.arange(730, dtype="timedelta64[D]")
        val_start, val_end = compute_validation_window(
            time, temporal_window=7, val_fraction=0.2
        )
        # n_samples = 730 - 7 + 1 = 724; n_val = int(724 * 0.2) = 144;
        # n_train = 580; first val target day index = 580 + 6 = 586.
        expected_start = _np_day(time[586])
        expected_end = _np_day(time[729])
        assert val_start == expected_start
        assert val_end == expected_end

    def test_tiny_axis_uses_at_least_one_val_sample(self) -> None:
        time = np.arange("2024-01-01", 10, dtype="datetime64[D]")
        val_start, val_end = compute_validation_window(time)
        # n_samples = 4; n_val = max(1, 0) = 1; n_train = 3;
        # first val target day index = 3 + 6 = 9 (last day).
        assert val_start == val_end == _np_day(time[-1])

    def test_rejects_bad_arguments(self) -> None:
        time = np.arange("2024-01-01", 30, dtype="datetime64[D]")
        with pytest.raises(ValueError):
            compute_validation_window(time, temporal_window=0)
        with pytest.raises(ValueError):
            compute_validation_window(time, val_fraction=1.5)


# --------------------------------------------------------------------------- #
# NetCDF profile parsing (QC filtering)
# --------------------------------------------------------------------------- #


class TestParseGdacProfile:
    def test_filters_qc_flagged_levels(self) -> None:
        ds = _profile_ds(
            temps=[28.4, 28.2, 27.9, 26.0],
            pres=[4.9, 9.8, 14.7, 19.6],
            temp_qc=["1", "1", "4", "1"],
        )
        entry = parse_gdac_profile(ds, source_id="4903456_001")
        assert entry is not None
        assert entry["depths_m"] == pytest.approx([4.9, 9.8, 19.6])
        assert entry["temps_c"] == pytest.approx([28.4, 28.2, 26.0])

    def test_prefers_adjusted_where_qc_good(self) -> None:
        ds = _profile_ds(
            temps=[28.4, 28.2, 27.9],
            pres=[4.9, 9.8, 14.7],
            temp_adj=[28.31, 28.25, 27.99],
            temp_adj_qc=["1", "1", "4"],
        )
        entry = parse_gdac_profile(ds, source_id="4903456_001")
        assert entry is not None
        # Level 2 adjusted QC bad -> falls back to raw for that level.
        assert entry["temps_c"] == pytest.approx([28.31, 28.25, 27.9])

    def test_skips_levels_with_bad_pressure(self) -> None:
        ds = _profile_ds(
            temps=[28.4, 28.2, 27.9],
            pres=[4.9, 9.8, 14.7],
            pres_qc=["1", "4", "1"],
        )
        entry = parse_gdac_profile(ds, source_id="4903456_001")
        assert entry is not None
        assert entry["depths_m"] == pytest.approx([4.9, 14.7])

    def test_bad_juld_returns_none(self) -> None:
        ds = _profile_ds(juld_qc="4")
        assert parse_gdac_profile(ds, source_id="4903456_001") is None

    def test_no_valid_levels_returns_none(self) -> None:
        ds = _profile_ds(temps=[28.4], pres=[4.9], temp_qc=["4"])
        assert parse_gdac_profile(ds, source_id="4903456_001") is None

    def test_entry_fields(self) -> None:
        ds = _profile_ds(
            temps=[28.4, 28.2],
            pres=[4.9, 9.8],
            dasdate=date(2024, 6, 15),
            lat=8.51,
            lon=88.19,
        )
        entry = parse_gdac_profile(ds, source_id="4903456_001")
        assert entry is not None
        assert entry["source_id"] == "4903456_001"
        assert entry["date"] == "2024-06-15"
        assert entry["lat"] == 8.51
        assert entry["lon"] == 88.19


# --------------------------------------------------------------------------- #
# Whole-cache loading + JSON store
# --------------------------------------------------------------------------- #


class TestLoadGdacFiles:
    def test_loads_matching_files_skips_date_mismatch(
        self, tmp_path: Path
    ) -> None:
        good = _profile_ds(dasdate=date(2024, 6, 15))
        off = _profile_ds(dasdate=date(2024, 6, 12))
        (tmp_path / "dac" / "aoml" / "4903456").mkdir(parents=True)
        good.to_netcdf(tmp_path / "dac" / "aoml" / "4903456" / "4903456_001.nc")
        bad_dir = tmp_path / "dac" / "aoml" / "4903457"
        bad_dir.mkdir(parents=True)
        off.to_netcdf(bad_dir / "4903457_002.nc")

        rows = [
            IndexRow(file="dac/aoml/4903456/4903456_001.nc", date=date(2024, 6, 15), lat=8.51, lon=88.19),
            # Index date 2024-06-15 vs JULD 2024-06-12 -> 3 days off -> skipped.
            IndexRow(file="dac/aoml/4903457/4903457_002.nc", date=date(2024, 6, 15), lat=8.51, lon=88.19),
        ]
        entries = load_gdac_files(tmp_path, rows)
        assert [e["source_id"] for e in entries] == ["4903456_001"]


class TestWriteProfilesJson:
    def test_roundtrip_flat_list_contract(self, tmp_path: Path) -> None:
        profiles = [
            {
                "source_id": "4903456_001",
                "date": "2024-06-15",
                "lat": 8.51,
                "lon": 88.19,
                "depths_m": [4.9, 9.8],
                "temps_c": [28.4, 28.2],
            }
        ]
        out = tmp_path / "profiles.json"
        write_profiles_json(profiles, out, provenance={"generated_by": "test"})
        raw = json.loads(out.read_text())
        assert isinstance(raw, list)  # flat list, exactly as evaluate_argo.py expects
        assert raw[0]["source_id"] == "4903456_001"
        assert raw[0]["date"] == "2024-06-15"
        assert len(raw[0]["depths_m"]) == len(raw[0]["temps_c"]) == 2
        pv = tmp_path / "profiles.provenance.json"
        assert pv.exists()
        assert json.loads(pv.read_text())["generated_by"] == "test"


def _np_day(v: np.datetime64) -> date:
    """Convert a day-resolution datetime64 to a datetime.date."""
    result = np.datetime64(v, "D").item()
    if isinstance(result, date):
        return result
    return result.date()
