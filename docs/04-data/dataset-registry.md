# Dataset Registry

> Verified dataset/product IDs, versions, variables, coverage, and provenance.
> Hard engineering gate (SYSTEM_MEMORY_DUMP.md §81). **Fill in only after `describe()`.**

## Verification matrix (hard gate)

| Variable | dataset_id | variable_name | source | spatial_resolution | temporal_resolution | coverage | units | latency | subset_supported | notes | verified_at |
|----------|-----------|---------------|--------|-------------------|---------------------|----------|-------|---------|------------------|-------|-------------|
| SST | *(unverified)* | | | | | | | | | candidate `010_024`/`010_001` | |
| SSS | *(unverified)* | | | | | | | | | candidate `015_014` | |
| SSH/SLA | *(unverified)* | | | | | | | | | candidates `008_057`/`008_046` | |
| Current U | *(unverified)* | | | | | | | | | candidate `015_003` — disclose model-derived components | |
| Current V | *(unverified)* | | | | | | | | | same product as Current U | |
| Wind U | *(unverified)* | | | | | | | | | candidates `012_005`/`012_002` | |
| Wind V | *(unverified)* | | | | | | | | | same product as Wind U | |
| GLORYS temperature | *(unverified)* | | | | | | | | | `GLOBAL_MULTIYEAR_PHY_001_030` family | |
| ARGO | *(unverified)* | | | | | | | | | independent validation only | |

## Manifest

Machine-readable entries live in `config/datasets.yaml` (runtime) and serialized manifests under
`data/manifests/`. Each entry records: `product_id`, `dataset_id`, `variable`, `source`, `resolution`,
`temporal_frequency`, `coverage_start/end`, `latency`, `units`, `notes`, `verified_at`
(SEE `contracts/data/dataset-metadata.schema.json`).

## Rules

- Never hard-code unverified dataset IDs (RULE 7).
- Update this registry + `config/datasets.yaml` together after every successful `describe()`.
- A training period is chosen only after the overlap across all inputs+target is verified (§126).