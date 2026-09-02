# Data-Pipeline Workflow

Safe workflow for modifying data ingestion/preprocessing.

## Rules specific to data work

- RULE 7 — verify dataset IDs via `describe()` before use; update `config/datasets.yaml` +
  `docs/04-data/dataset-registry.md` together.
- Golden Rule 16 — preserve provenance; every transformation mutates provenance records.
- Golden Rules 17–18 — preserve channel/depth ordering; use `config/variables.yaml`/`depths.yaml`.
- Golden Rule 10 — do not download years of data before a one-day test succeeds.
- Do not commit large datasets (RULE 12). Use tiny synthetic fixtures in tests.

## Steps

1. Read `docs/04-data/` (sources, registry, preprocessing, regridding, QC, missing-data,
   temporal-alignment, provenance).
2. Verify the dataset(s) (one-day regional subset first) and record verification.
3. Write tests first: harmonization, grid/order preservation, provenance, contract compliance.
4. Implement the smallest slice end-to-end (download → harmonize → one valid tensor).
5. Validate against contracts (`contracts/data/*`); regenerate manifests.
6. Run `data-engineering/tests` + `backend/tests` affected suites + `make lint`.

Do not skip verification steps even in a hurry — any guessed dataset ID invalidates the registry.