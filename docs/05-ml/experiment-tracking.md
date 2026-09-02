# Experiment Tracking

> Experiment naming, configuration, metrics, and artifact tracking.
> Source: SYSTEM_MEMORY_DUMP.md §114, §79.

## Policy

- Experiments are tracked in a registry, not through ad-hoc filenames.
- Key information per experiment: dataset version, preprocessing version, normalization version,
  architecture config, training config, metrics, artifact URI/hash.
- The exact tool (MLflow / local YAML registry / Weights & Biases) is **UNRESOLVED** (§148).

## Registry entries

`experiments/registry.yaml` records:
```text
experiment_id
model_version
config_hash
dataset_manifest
preprocessing_version
normalization_version
metrics
artifacts
```

## Checkpoint traceability (§114)

A checkpoint must carry:
- model weights
- architecture configuration
- normalization statistics (mean/std per channel)
- depth list, channel order
- preprocessing version, dataset version

A checkpoint without metadata is unsafe for serving.