"""Shared backend test fixtures: contract loaders, validation helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, RefResolver

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts" / "api"


def _load_ref_store() -> dict[str, dict]:
    """Map every contract schema by filename AND by its absolute $id, so
    cross-file $refs (e.g. prediction.schema.json -> ocean-map.schema.json)
    resolve during validation (RULE 6)."""
    store: dict[str, dict] = {}
    for path in CONTRACTS_DIR.glob("*.schema.json"):
        doc = json.loads(path.read_text())
        store[path.name] = doc
        schema_id = doc.get("$id")
        if isinstance(schema_id, str):
            store[schema_id] = doc
    assert store, f"no contracts found in {CONTRACTS_DIR}"
    return store


_REF_STORE = _load_ref_store()


def assert_valid_against(instance: dict, schema: dict) -> None:
    """Validate a response payload against a contract schema (RULE 6).

    Uses a RefResolver so relative $refs between contract files resolve
    against the absolute $ids in the built-in store.
    """
    validator = Draft7Validator(
        schema=schema,
        resolver=RefResolver(base_uri="", referrer=schema, store=_REF_STORE),
    )
    validator.validate(instance)


@pytest.fixture
def validate_contract(contract_schemas: dict[str, dict]):
    """Fixture factory: validate(instance, schema_key).

    contract_schemas maps schema file name minus ".schema.json" to its dict
    (kept for compatibility; the store used for resolution is at module level).
    """

    def _validate(instance: dict, schema_key: str) -> None:
        assert_valid_against(instance, contract_schemas[schema_key])

    return _validate


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
