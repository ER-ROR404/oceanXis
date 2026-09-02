# Data Provenance

> How source and transformation lineage is retained.
> Source: SYSTEM_MEMORY_DUMP.md §78; schema `contracts/data/provenance.schema.json`.

## Recorded metadata (per processed dataset)

```text
source_provider
product_id
dataset_id
dataset_version
variable
source_resolution
target_resolution
source_time
target_time
interpolation_method
unit_conversion
normalization_version
preprocessing_version
verified_at
```

## Guarantees

- Dataset IDs are verified (via `describe()`) before recording (RULE 7).
- Provenance is preserved end-to-end (Golden Rule 16).
- Provenance records accompany the dataset manifest (`config/datasets.yaml`), training samples, and
  model checkpoint manifests.
- No silent substitution of dataset versions or preprocessing versions.

## Integration

- Data engineering writes provenance at ingestion/harmonization.
- ML checkpoints reference the dataset/preprocessing/normalization versions they consumed
  (`contracts/ml/checkpoint-manifest.schema.json`).