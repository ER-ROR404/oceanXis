# Model Architecture

> Current approved model architecture and tensor contracts.
> Status: **CNN + ConvLSTM hybrid is the PRIMARY model (ADR-010).**
> The plain single-day CNN is the Stage-1 **baseline**; climatology is the second comparator.

## Tensor contracts

### Stage 1 — CNN baseline (single day)

```text
input:    float32 [B, 7, H, W]      (one day; channel order fixed, see variables.md)
output:   float32 [B, 15, H, W]     (depth order fixed, see depth-levels.md)
```

### Stage 2 — CNN + ConvLSTM hybrid (PRIMARY, ADR-010)

```text
input:    float32 [B, T, 7, H, W]   (T = lookback window of daily surface fields; T=10 default)
output:   float32 [B, 15, H, W]     (15 depths for the TARGET day = last day of the window)
optional uncertainty: float32 [B, 15, H, W]  (non-negative variance, post-baseline)
```

## Stage 1 — CNN encoder–decoder (baseline, §17)

```text
Input [B,7,H,W]
  Conv2D(7→32,k=3,pad=1) + BatchNorm + ReLU
  Conv2D(32→64,k=3,pad=1) + BatchNorm + ReLU
  Conv2D(64→128,k=3,pad=1) + BatchNorm + ReLU
  Conv2D(128→128,k=3,pad=1) + ReLU
  → Ocean Embedding [B,128,H,W]
Decoder
  Conv2D(128→128,k=3,pad=1)+ReLU
  Conv2D(128→64,k=3,pad=1)+ReLU
  Conv2D(64→32,k=3,pad=1)+ReLU
  Conv2D(32→15,k=3,pad=1)
  → Temperature [B,15,H,W]
```

This is the **baseline comparator**, built first to prove the pipeline (implementation order, NOT the
final model).

## Stage 2 — CNN + ConvLSTM hybrid (PRIMARY, ADR-010)

```text
Input [B,T,7,H,W]
  ┌─ per-time-step spatial encoder (shared weights) ─┐
  │  Conv2D(7→32,k=3,pad=1)+BN+ReLU                  │
  │  Conv2D(32→64,k=3,pad=1)+BN+ReLU                 │
  │  Conv2D(64→128,k=3,pad=1)+BN+ReLU                │
  └──────────────────────────────────────────────────┘
  → surface features [B,T,128,H,W]
  ↓
  Stacked ConvLSTM (spatial + temporal jointly):
  ConvLSTMCell(128→128, k=3, pad=1), 2 stacked layers
  → final-time-step hidden state [B,128,H,W]        ← time axis collapsed
  ↓
  Decoder (shared with Stage 1)
  Conv2D(128→128,k=3,pad=1)+ReLU
  Conv2D(128→64,k=3,pad=1)+ReLU
  Conv2D(64→32,k=3,pad=1)+ReLU
  Conv2D(32→15,k=3,pad=1)
  → Temperature [B,15,H,W]                           ← TARGET day = last day of window
```

Rationale (ADR-010 / Su et al. 2022): daily data → time carries information. CNN-only sees
"today → T"; the hybrid sees "Day-N … Today → temporal+spatial → T". ConvLSTM is preferred over
**plain LSTM** because our data are spatial grids — a plain LSTM would flatten the grid.

## Variants (post-baseline, optional)

- **U-Net-like** skip connections (preserve spatial detail) — §18.
- **Attention / ViT / depth-conditioned** decoder or depth positional encoding — §19–§20.
- **Uncertainty head** — Gaussian heteroscedastic (μ, log σ²) — §21, §25.

## Files

- `ml/src/oceanembed/models/oceanembed.py`, `encoder.py`, `decoder.py`, `convlstm.py` (ConvLSTM cell
  + stack), `cnn.py` (Stage 1 baseline), `depth_embedding.py`, `uncertainty.py`, `baselines.py`.

## Config

Architecture parameters live in `ml/configs/*.yaml` and `config/model.yaml`; layer counts, hidden
dims, and lookback `T` are experimental (NOT locked — §148) but **fixed for v1 via config**
(`lookback_days: 10`, ConvLSTM `[128,128]`, k=3). `config/model.yaml` declares the primary hybrid
architecture + the CNN baseline comparator flag.