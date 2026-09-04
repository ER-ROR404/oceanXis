"""Tests for oceanembed_data.catalog — verified dataset metadata (RULE 7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from oceanembed_data.catalog import (
    CANONICAL_INPUT_CHANNELS,
    CANONICAL_DEPTHS_M,
    DatasetCatalog,
    DatasetEntry,
)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "datasets.yaml"


class TestDatasetEntry:
    """Tests for the DatasetEntry dataclass."""

    def test_verified_entry_is_verified(self):
        entry = DatasetEntry(
            name="SST",
            role="input",
            dataset_id="METOFFICE-GLO-SST-L4-REP-OBS-SST",
            variable="analysed_sst",
            source="copernicus_marine",
            verified=True,
            verified_at="2026-09-02",
        )
        assert entry.is_verified is True

    def test_unverified_entry_is_not_verified(self):
        entry = DatasetEntry(
            name="SST",
            role="input",
            dataset_id="METOFFICE-GLO-SST-L4-REP-OBS-SST",
            variable="analysed_sst",
            source="copernicus_marine",
            verified=False,
        )
        assert entry.is_verified is False

    def test_empty_dataset_id_is_not_verified(self):
        entry = DatasetEntry(
            name="argo",
            role="validation",
            dataset_id="",
            variable="TEMP",
            source="argo",
            verified=False,
        )
        assert entry.is_verified is False


class TestDatasetCatalog:
    """Tests for DatasetCatalog loading and lookup."""

    @pytest.fixture
    def catalog(self) -> DatasetCatalog:
        """Load the real config for integration-style tests."""
        return DatasetCatalog.from_yaml(CONFIG_PATH)

    def test_from_yaml_loads_entries(self, catalog: DatasetCatalog):
        assert len(catalog.entries) > 0

    def test_from_yaml_loads_all_input_channels(self, catalog: DatasetCatalog):
        for channel in CANONICAL_INPUT_CHANNELS:
            assert channel in catalog.entries, f"Missing channel: {channel}"

    def test_from_yaml_loads_glorys_target(self, catalog: DatasetCatalog):
        assert "glorys_temperature" in catalog.entries

    def test_from_yaml_loads_argo(self, catalog: DatasetCatalog):
        assert "argo" in catalog.entries

    def test_get_returns_correct_entry(self, catalog: DatasetCatalog):
        sst = catalog.get("SST")
        assert sst.name == "SST"
        assert sst.dataset_id == "METOFFICE-GLO-SST-L4-REP-OBS-SST"

    def test_get_raises_on_missing_name(self, catalog: DatasetCatalog):
        with pytest.raises(KeyError, match="not in catalog"):
            catalog.get("NONEXISTENT")

    def test_input_channels_returns_canonical_order(self, catalog: DatasetCatalog):
        channels = catalog.input_channels()
        names = [ch.name for ch in channels]
        assert names == CANONICAL_INPUT_CHANNELS

    def test_training_target_is_glorys(self, catalog: DatasetCatalog):
        target = catalog.training_target()
        assert target.name == "glorys_temperature"
        assert target.role == "training_target"

    def test_all_verified_excludes_argo(self, catalog: DatasetCatalog):
        # All non-ARGO entries should be verified (from the real config)
        assert catalog.all_verified() is True

    def test_summary_contains_channel_names(self, catalog: DatasetCatalog):
        summary = catalog.summary()
        for channel in CANONICAL_INPUT_CHANNELS:
            assert channel in summary

    def test_from_yaml_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            DatasetCatalog.from_yaml("/nonexistent/path.yaml")


class TestConstants:
    """Tests for catalog constants."""

    def test_canonical_input_channels_count(self):
        assert len(CANONICAL_INPUT_CHANNELS) == 7

    def test_canonical_depths_count(self):
        assert len(CANONICAL_DEPTHS_M) == 15

    def test_canonical_depths_are_monotonic(self):
        assert CANONICAL_DEPTHS_M == sorted(CANONICAL_DEPTHS_M)

    def test_canonical_depths_start_at_zero(self):
        assert CANONICAL_DEPTHS_M[0] == 0.0

    def test_canonical_depths_end_at_1000(self):
        assert CANONICAL_DEPTHS_M[-1] == 1000.0
