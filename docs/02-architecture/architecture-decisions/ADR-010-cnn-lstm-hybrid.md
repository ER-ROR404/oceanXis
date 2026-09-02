# ADR-010: CNN + ConvLSTM hybrid (staged) as the core reconstruction model

- **Status:** Accepted (team decision)
- **Date:** 2026-09-02 (SIH26066 build)
- **Owner:** ml

## Context

OceanEmbed reconstructs subsurface ocean temperature (15 depths, 0.25°×0.25°, daily) from 7 daily
surface satellite channels. The input is fundamentally a **spatio-temporal time series**: daily
surface fields across a region over consecutive days.

The base/reference methods for this exact problem (surface → subsurface reconstruction),
notably **Su et al. 2022, "Subsurface Temperature Reconstruction for the Global Ocean from 1993 to
2020 Using Satellite Observations and Deep Learning", Remote Sensing 14(13):3198**, and the
OceanEmbed problem statement itself, demonstrate the key limitation of single-day models:

> "Because of ocean data's inherent **spatial nonlinearity and temporal dependence**, traditional
> LSTM and CNN cannot fully exploit the temporal and spatial properties of ocean data. As a result,
> the **ConvLSTM** algorithm was proposed to extend LSTM. The model can account for not only the
> time series dependence of ocean data but also the **spatial characteristics** of ocean data."

- **CNN** captures spatial structure (local connectivity over the surface grid).
- **LSTM** captures temporal dependence (daily sequence).
- **CNN + ConvLSTM hybrid** captures both simultaneously, and — crucially — **keeps the spatial
  grid** (ConvLSTM runs convolutions inside the recurrent cell; a plain LSTM would flatten the grid).

The previously documented `PROPOSED` baseline was a **plain CNN on a single day** (`[B,7,H,W]`),
which ignores the temporal axis. The problem statement explicitly permits CNN, ViT, GNN, autoencoder,
and **attention/hybrid architectures** — the exact architecture is an engineering decision.

## Decision (staged)

Do **NOT** lock the project to CNN-only. Implement in this order:

1. **Stage 1 — CNN baseline** (`[B,7,H,W] → [B,15,H,W]`; §17 architecture).
   Provides a scientifically meaningful baseline and proves the entire data/Colab pipeline first.
2. **Stage 2 — CNN + ConvLSTM hybrid (PRIMARY MODEL)** (`[B,T,7,H,W] → [B,15,H,W]`, T=10 days):
   per-timestep conv encoder → stacked ConvLSTM (spatial+temporal) → decoder. ConvLSTM is preferred
   over plain LSTM because our data are spatial grids (flattening is undesirable).
3. **Transformer / attention / uncertainty head** — optional experiments **only after** Stage 2 works.

**Memory-dump interpretation note:** the rule "start with CNN baseline before implementing a
Transformer/ViT" remains correct as an *implementation order*, but it must **not** be interpreted as
"final OceanEmbed = CNN only". Final decision: **CNN = baseline; CNN + ConvLSTM = primary candidate;
Transformer/attention = optional experiment** (§19–§21 remain future work).

## Alternatives considered

- **Plain CNN only (single day)** — simpler, but cannot exploit temporal evolution of daily surface
  fields; the base literature shows hybrids outperform for spatio-temporal reconstruction.
- **Plain LSTM hybrid** — viable, but flattens spatial grid; ConvLSTM preserves it.
- **ViT/attention hybrid from the start** — higher complexity; defer until Stage 2 works (Golden 12).

## Consequences

- `config/model.yaml`: primary architecture `cnn_lstm_hybrid`, `lookback_days: 10`, ConvLSTM
  `[128,128]`, k=3; baseline comparator `cnn_encoder_decoder` + climatology.
- `contracts/ml/model-input.schema.json`: input gains a time axis → `X [T, 7, H, W]` (contract
  change, human review required per CONTRIBUTING.md).
- `ml/configs/`: `cnn_v1.yaml` (Stage 1) + `hybrid_v1.yaml` (Stage 2, primary).
- Temporal split (ADR-007) is even more critical: **windows never straddle a fold boundary**; each
  Stage-2 window has T consecutive valid days.
- Colab training (ADR-009) feeds windowed batches `[B,T,7,H,W]`, not single days.
- Backend inference (RULE 5) consumes a T-day lookback window of surface fields per the updated
  model-input contract.
- Stage-1 CNN retained as a baseline comparator (credibility, §30/§91).

## References

- SYSTEM_MEMORY_DUMP.md §16 (architecture is an engineering decision), §17–§20 (baseline + variants).
- docs/01-product/problem-statement.md (permitted model families, §64–68).
- Su, H.; Jiang, J.; Wang, A.; Zhuang, W.; Yan, X.-H. (2022). Remote Sensing 14(13):3198 (ConvLSTM).
- Front. Mar. Sci. 2023 10:1218514 (CNN vs LSTM vs BLSTM vs climatology for the same task).
- ADR-007 (temporal split), ADR-003 (PyTorch), ADR-009 (Colab training).