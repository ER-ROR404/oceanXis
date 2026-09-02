# model-registry/

**OceanEmbed model registry — approved model/checkpoint metadata.**

Holds **manifests and metadata**, never large `.pt` binaries (RULE 13). Actual checkpoints live in
object storage / MLflow referenced by `artifact_uri`.

## Files

```text
registry.yaml                    approved model versions -> artifact locations
schemas/model-manifest.schema.json
schemas/checkpoint-manifest.schema.json   (mirrors contracts/ml/checkpoint-manifest.schema.json)
models/                          artifact dir (gitkept; binaries excluded)
```

## A reproducible checklist entry (not just `final_model.pt`)

```text
model: name/version
checkpoint: id, artifact_uri, sha256
data: dataset_manifest
preprocessing: version
normalization: version
configuration: architecture/training config hash
evaluation: test_rmse/bias/correlation
```

Every approved/rollback decision references this. Policy: `docs/05-ml/checkpoint-policy.md`.

> **Pre-build stage:** scaffolding + schema; populated during ML coding phase.