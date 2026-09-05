"""Tests for the training dataset build script's file-cleanup logic.

Covers robustness against interrupted Copernicus downloads:
  - duplicate artifacts from re-runs (`name_(1).nc`) must be excluded
  - partial writes must not be consumed as data
  - clean chunks are kept
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "build_training_dataset.py"

spec = importlib.util.spec_from_file_location("build_training_dataset", _SCRIPT)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


@pytest.fixture
def processed_dir(tmp_path: Path) -> Path:
    d = tmp_path / "bay_of_bengal"
    (d / "SST").mkdir(parents=True, exist_ok=True)
    return d


class TestFindNcFiles:
    def test_excludes_copernicus_duplicates(self, processed_dir: Path) -> None:
        sst = processed_dir / "SST"
        (sst / "data_2022-01-01-2022-03-31.nc").write_bytes(b"")
        (sst / "data_2022-01-01-2022-03-31_(1).nc").write_bytes(b"")
        (sst / "data_2022-04-01-2022-06-29_(1).nc").write_bytes(b"")
        files = build.find_nc_files(processed_dir, "SST")
        assert [f.name for f in files] == ["data_2022-01-01-2022-03-31.nc"]

    def test_excludes_partial_writes(self, processed_dir: Path) -> None:
        sst = processed_dir / "SST"
        (sst / "data_2022-01-01.nc").write_bytes(b"")
        (sst / "data_2022-01-01.nc.e6j5kdgf").write_bytes(b"")  # temp suffix
        files = build.find_nc_files(processed_dir, "SST")
        assert [f.name for f in files] == ["data_2022-01-01.nc"]

    def test_keeps_all_clean_chunks_sorted(self, processed_dir: Path) -> None:
        sst = processed_dir / "SST"
        (sst / "b.nc").write_bytes(b"")
        (sst / "a.nc").write_bytes(b"")
        files = build.find_nc_files(processed_dir, "SST")
        assert [f.name for f in files] == ["a.nc", "b.nc"]

    def test_empty_dir_returns_empty(self, processed_dir: Path) -> None:
        assert build.find_nc_files(processed_dir, "SST") == []

    def test_missing_channel_dir_returns_empty(self, tmp_path: Path) -> None:
        assert build.find_nc_files(tmp_path / "bay_of_bengal", "SST") == []


class TestIsCleanNc:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("data.nc", True),
            ("data_(1).nc", False),
            ("data_(2).nc", False),
            ("data_(3).nc", False),
            ("data_2022-01-01.nc", True),
        ],
    )
    def test_flag(self, name: str, expected: bool) -> None:
        assert build._is_clean_nc(Path(name)) is expected