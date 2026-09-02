"""OceanEmbed ML package — training + inference.

Single codebase that runs both locally (CPU, tests + fast iteration) and in
Google Colab on GPU (ADR-009). The backend never imports this package for
training (RULE 3); it serves only an approved checkpoint (RULE 5).

Package layout: see ml/README.md. Subpackages:

- data:          PyTorch Dataset/DataLoader/manifests/samplers (temporal split, RULE 10)
- preprocessing: loader, QC, temporal/spatial, regridding, masking, normalization (train-only, RULE 11)
- models:        CNN baseline (Stage 1), CNN + ConvLSTM hybrid (Stage 2, ADR-010), baselines
- losses:        masked_mse (primary), huber, depth_weighted, ..., uncertainty_nll
- training:      trainer, optimizer, scheduler, callbacks, checkpointing, reproducibility
- evaluation:    RMSE/bias/corr, depth-wise, spatial, ARGO (RULE 9), baseline comparison
- inference:     predictor, postprocess (denormalize + mask), profile
- registry:      model_registry, artifact_registry, manifests
"""

__version__ = "0.1.0"