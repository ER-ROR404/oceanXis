# infrastructure/

**OceanEmbed deployment and cloud-training infrastructure.**

## Layout

```text
docker/            backend, ml-training, ml-inference, frontend Dockerfiles
terraform/         network, compute, storage, database, secrets, monitoring (+ staging/production envs)
kubernetes/        backend / ml-inference / frontend deployments, services, ingress, configmap, hpa
cloud-training/    immutable training/eval/preprocessing jobs (GPU) + submit scripts
```

## Principles

- `ml/Dockerfile.training` and `ml/Dockerfile.inference` are deliberately separate (training uses
  GPU/huge datasets; inference uses approved checkpoint + 7 surface inputs + minimal deps).
- No Kubernetes merely for "enterprise" (RULE 18); no microservices without an ADR (RULE 17).
- Not required for the first 36-hour MVP (see ADR-008). Introduce when deployment demands it.

> **Pre-build stage:** scaffolding only. Proceed per `docs/07-operations/deployment.md` and
> `docs/02-architecture/deployment-architecture.md` during the coding/deploy phase.