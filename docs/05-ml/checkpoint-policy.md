# Checkpoint Policy

> Checkpoint naming, promotion, retention, and rollback.
> Source: SYSTEM_MEMORY_DUMP.md §79, §114; model-registry doc.

## Rule

Large model checkpoints are **never committed to Git** (RULE 13). Actual weights live in object
storage / managed artifact registry; `model-registry/registry.yaml` references them by URI + hash.

## Naming

```text
oceanembed-cnn-v<major>.<minor>.<patch>
```

## Manifest (see contracts/ml/checkpoint-manifest.schema.json)

```text
model:        name, version
checkpoint:   id, artifact_uri, sha256
data:         dataset_manifest
preprocessing: version
normalization: version
configuration: architecture, training_config
evaluation:   test_rmse, test_bias, test_correlation, test_period
```

## Lifecycle

- Save best-validation checkpoint (never choose the final model on test — §88/§89).
- Promote to registry only after validation + evaluation pass.
- Rollback supported by immutable, hashed artifacts referenced through the registry.

## Versioning ($79)

Every prediction references:
```text
model_version
training_dataset_version   (where available)
preprocessing_version       (where available)
normalization_version       (where available)
```