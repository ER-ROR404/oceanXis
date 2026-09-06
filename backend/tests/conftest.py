"""Shared backend test fixtures: contract loaders, validation helpers."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts" / "api"


@pytest.fixture(scope="session")
def contract_schemas() -> dict[str, dict]:
    """Load all API contract JSON schemas once per session."""
    schemas: dict[str, dict] = {}
    for path in CONTRACTS_DIR.glob("*.schema.json"):
        with open(path) as f:
            # "ocean-map.schema.json" -> key "ocean-map"
            schemas[path.name.removesuffix(".schema.json")] = json.load(f)
    assert schemas, f"no contracts found in {CONTRACTS_DIR}"
    return schemas


def assert_valid_against(instance: dict, schema: dict) -> None:
    """Validate a response payload against a contract schema (RULE 6)."""
    jsonschema.validate(instance=instance, schema=schema)


@pytest.fixture
def validate_contract(contract_schemas: dict[str, dict]):
    """Fixture factory: validate(instance, schema_key)."""

    def _validate(instance: dict, schema_key: str) -> None:
        assert_valid_against(instance, contract_schemas[schema_key])

    return _validate
