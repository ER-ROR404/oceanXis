# Model Architecture

> Current approved model architecture and tensor contracts.
> Status: the exact architecture is an engineering decision (PROPOSED baseline).

## Tensor contract (LOCKED shapes)

```text
input:    float32 [B, 7, H, W]     (channel order fixed, see variables.md)
output:   float32 [B, 15, H, W]    (depth order fixed, see depth-levels.md)
optional uncertainty: float32 [B, 15, H, W]  (non-negative variance)
```

## Recommended baseline: CNN encoder–decoder (PROPOSED)

```text
Input [B,7,H,W]
  Conv2D(7→32,k=3,pad=1) + BatchNorm + ReLU
  Conv2D(32→64) + BatchNorm + ReLU
  Conv2D(64→128) + BatchNorm + ReLU
  Conv2D(128→128) + ReLU
  → Ocean Embedding [B,128,H,W]
Decoder
  Conv2D(128→128)+ReLU
  Conv2D(128→64)+ReLU
  Conv2D(64→32)+ReLU
  Conv2D(32→15)
  → Temperature [B,15,H,W]
```

This is a **recommended starting point**, not a locked requirement (§17).

## Variants

- **U-Net-like** with skip connections (optional; preserves spatial detail, easy to explain) — §18.
- **Attention / ViT / depth-conditioned** decoder — only after the baseline works (§19–§20).
- **Uncertainty head** — Gaussian heteroscedastic (μ, log σ²) as a differentiation (§21, §25).

## Files

- `ml/src/oceanembed/models/oceanembed.py`, `encoder.py`, `decoder.py`, `depth_embedding.py`,
  `uncertainty.py`, `baselines.py`.

## Config

Architecture parameters live in `ml/configs/cnn_v1.yaml` and `config/model.yaml`; layer counts and
hidden dims are experimental (NOT locked — §148).