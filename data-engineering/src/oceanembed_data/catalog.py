"""Verified external dataset metadata (RULE 7).

Loads dataset entries from config/datasets.yaml and provides a clean Python
interface for the data-engineering pipeline. Every dataset ID must be verified
via copernicusmarine.describe() before use — this module does NOT perform
verification; it consumes already-verified entries.

Usage:
    catalog = DatasetCatalog.from_yaml("config/datasets.yaml")
    sst = catalog.get("SST")
    print(sst.dataset_id)  # "METOFFICE-GLO-SST-L4-REP-OBS-SST"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Canonical channel ordering (LOCKED — Golden Rule 17).
# Surface input channels in the order consumed by the model.
CANONICAL_INPUT_CHANNELS: list[str] = [
    "SST",
    "SSS",
    "SSH",
    "current_U",
    "current_V",
    "wind_U",
    "wind_V",
]

# Canonical depth ordering (LOCKED — Golden Rule 18).
CANONICAL_DEPTHS_M: list[float] = [
    0.0, 5.0, 10.0, 20.0, 30.0,
    50.0, 75.0, 100.0, 125.0, 150.0,
    200.0, 300.0, 500.0, 700.0, 1000.0,
]

# Canonical output variable name for GLORYS temperature.
GLORYS_TEMP_VAR = "thetao"


@dataclass(frozen=True)
class DatasetEntry:
    """A single verified dataset from the catalog.

    Attributes:
        name: Logical name (e.g. "SST", "SSS", "SSH", "current", "wind").
        role: "input", "training_target", or "validation".
        dataset_id: Copernicus Marine dataset identifier.
        variable: Variable name(s) within the dataset.
        source: Source identifier (copernicus_marine, glorys, argo).
        note: Human-readable note about this dataset.
        verified: Whether describe() has confirmed this dataset exists.
        verified_at: ISO date of last verification.
    """

    name: str
    role: str
    dataset_id: str
    variable: str
    source: str
    note: str = ""
    verified: bool = False
    verified_at: Optional[str] = None

    @property
    def is_verified(self) -> bool:
        """True only if both verified flag is set AND dataset_id is non-empty."""
        return self.verified and bool(self.dataset_id)


@dataclass
class DatasetCatalog:
    """Collection of verified dataset entries loaded from config.

    Provides lookup by logical name and iteration over all entries.
    """

    entries: dict[str, DatasetEntry] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> DatasetCatalog:
        """Load catalog from a datasets.yaml config file.

        Args:
            path: Path to the YAML config file.

        Returns:
            Populated DatasetCatalog.

        Raises:
            FileNotFoundError: If config file does not exist.
            KeyError: If required fields are missing.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset config not found: {path}")

        with open(path) as f:
            raw = yaml.safe_load(f)

        catalog = cls()

        # Top-level metadata
        if "manifests_dir" in raw:
            catalog.manifests_dir = raw["manifests_dir"]

        # Load entries
        raw_entries = raw.get("entries", {})
        for name, entry_raw in raw_entries.items():
            # Skip non-dataset keys (manifests_dir, schema, split_policy, etc.)
            if not isinstance(entry_raw, dict):
                continue
            if "dataset_id" not in entry_raw and "selected_dataset_id" not in entry_raw:
                continue

            # Extract selected dataset info
            selected_id = entry_raw.get("selected_dataset_id")
            selected_var = entry_raw.get("selected_variable", "")
            role = entry_raw.get("role", "input")
            verified = entry_raw.get("verified", False)
            verified_at = entry_raw.get("verified_at")

            # Find the matching candidate for metadata
            candidates = entry_raw.get("candidates", [])
            source = ""
            note = ""
            if candidates and selected_id:
                for cand in candidates:
                    if cand.get("dataset_id") == selected_id:
                        source = cand.get("source", "")
                        note = cand.get("note", "")
                        break

            # Map "current" -> current_U/current_V, "wind" -> wind_U/wind_V
            if name == "current":
                # Current has two variables: uo (current_U) and vo (current_V)
                for var_name in ["current_U", "current_V"]:
                    var_label = "uo" if var_name == "current_U" else "vo"
                    catalog.entries[var_name] = DatasetEntry(
                        name=var_name,
                        role=role,
                        dataset_id=selected_id or "",
                        variable=var_label,
                        source=source,
                        note=f"{note} [{var_label}]",
                        verified=verified,
                        verified_at=verified_at,
                    )
            elif name == "wind":
                # Wind has two variables: eastward_wind (wind_U) and northward_wind (wind_V)
                for var_name, var_label in [
                    ("wind_U", "eastward_wind"),
                    ("wind_V", "northward_wind"),
                ]:
                    catalog.entries[var_name] = DatasetEntry(
                        name=var_name,
                        role=role,
                        dataset_id=selected_id or "",
                        variable=var_label,
                        source=source,
                        note=f"{note} [{var_label}]",
                        verified=verified,
                        verified_at=verified_at,
                    )
            else:
                catalog.entries[name] = DatasetEntry(
                    name=name,
                    role=role,
                    dataset_id=selected_id or "",
                    variable=selected_var,
                    source=source,
                    note=note,
                    verified=verified,
                    verified_at=verified_at,
                )

        logger.info(
            "Loaded %d catalog entries: %s",
            len(catalog.entries),
            ", ".join(sorted(catalog.entries.keys())),
        )
        return catalog

    def get(self, name: str) -> DatasetEntry:
        """Get a dataset entry by logical name.

        Raises:
            KeyError: If the name is not in the catalog.
        """
        if name not in self.entries:
            available = ", ".join(sorted(self.entries.keys()))
            raise KeyError(f"Dataset '{name}' not in catalog. Available: {available}")
        return self.entries[name]

    def input_channels(self) -> list[DatasetEntry]:
        """Return input datasets in canonical order (Golden Rule 17)."""
        return [self.entries[ch] for ch in CANONICAL_INPUT_CHANNELS if ch in self.entries]

    def training_target(self) -> DatasetEntry:
        """Return the GLORYS training target entry."""
        return self.get("glorys_temperature")

    def all_verified(self) -> bool:
        """True if every non-ARGO entry is verified."""
        for entry in self.entries.values():
            if entry.name == "argo":
                continue
            if not entry.is_verified:
                return False
        return True

    def summary(self) -> str:
        """Human-readable summary of catalog state."""
        lines = [f"DatasetCatalog: {len(self.entries)} entries"]
        for name in CANONICAL_INPUT_CHANNELS:
            if name in self.entries:
                e = self.entries[name]
                status = "✓" if e.is_verified else "✗"
                lines.append(f"  {status} {name:12s} -> {e.dataset_id}")
        if "glorys_temperature" in self.entries:
            e = self.entries["glorys_temperature"]
            status = "✓" if e.is_verified else "✗"
            lines.append(f"  {status} {'target':12s} -> {e.dataset_id}")
        if "argo" in self.entries:
            e = self.entries["argo"]
            status = "✓" if e.is_verified else "?"
            lines.append(f"  {status} {'argo':12s} -> {e.dataset_id or 'raw GDAC'}")
        return "\n".join(lines)
