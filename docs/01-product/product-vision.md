# Product Vision — OceanEmbed No.1 Strategy

> STATUS: **LOCKED** (team decision, 2026-09-04)
> This document is the authoritative product vision. It supersedes any earlier, narrower
> interpretation of "Mode 1 / Mode 2" and defines what the winning solution looks like.

---

## One-sentence definition

> **OceanEmbed — A validated, uncertainty-aware 3D subsurface ocean temperature reconstruction
> system from surface satellite-derived observations.**

The primary deliverable is the **scientific reconstruction itself**, not a nice ocean dashboard.

---

## The 4 Layers of a Winning Solution

| Layer | What we give | Why it matters |
|-------|-------------|----------------|
| 1. **Reconstruction Engine** | 7 surface variables → subsurface temperature | ⭐⭐⭐⭐⭐ Core requirement |
| 2. **Scientific Validation** | Compare prediction against independent observations (ARGO) | ⭐⭐⭐⭐⭐ Proves it works |
| 3. **Uncertainty / Confidence** | Tell user where prediction is reliable vs uncertain | ⭐⭐⭐⭐⭐ Scientific responsibility |
| 4. **Operational Explorer** | Map + depth + vertical profile | ⭐⭐⭐⭐ How user interacts |

**Core strategic shift:** Don't compete on having the fanciest model. Compete on proving that
your reconstructed ocean data is **useful, measurable, trustworthy, and scientifically defensible.**

---

## The 3 Product Modes

### MODE 1 — Spatial Map Mode (🌊)

**Purpose:** See the reconstructed temperature across the whole region.

**User selects:** Region → Date → Depth (e.g. 100 m)

**Output:** Every 0.25° × 0.25° cell shows predicted temperature at that depth.

**UPGRADE over basic map:** Add a **Confidence Layer**. User can switch between views:

| View | What it shows |
|------|--------------|
| **Temperature** | Predicted °C at selected depth |
| **Confidence** | Model uncertainty per cell (±X.X °C) |
| **Prediction Error** | Where model is likely wrong (error map) |

This answers: *"Where is the subsurface ocean warmer or cooler — and where can we trust the prediction?"*

---

### MODE 2 — Vertical Profile Mode (📈)

**Purpose:** See the temperature structure from surface to 1000m at one location.

**When:** User clicks any 0.25° grid cell on the map.

**Show:**
- Observed surface temperature (input)
- Predicted profile at 15 depths
- **Where ARGO exists: side-by-side comparison**

```
Depth     ARGO        OceanEmbed
─────────────────────────────────
0 m       28.5°C      28.4°C
50 m      25.6°C      25.8°C
100 m     21.5°C      21.8°C
200 m     18.9°C      18.7°C
...
```

**Then calculate per-profile:**
- RMSE
- Bias
- Correlation

This transforms the demo from:
> "Look, our AI predicts temperature."

to:
> "Here is evidence that our reconstruction works."

This answers: *"What is the temperature structure from the surface down to 1000m at this location?"*

---

### MODE 3 — Scientific Validation Mode (🔬) — Judge-Facing

**Purpose:** Prove to judges that the model is correct.

**Judge selects:** Date → Region → Depth

**Show:**

```
OceanEmbed Validation Summary
─────────────────────────────
RMSE          0.XX °C
Bias          +0.XX °C
Correlation   0.XX

ARGO Coverage
████████████░░░░  78%

Prediction Error Map
🟢 Low error    (RMSE < 1°C)
🟡 Moderate     (RMSE 1–2°C)
🔴 High error   (RMSE > 2°C)
```

This answers the judge's most important question:
> *"How do you know your model is actually correct?"*

---

## How the 3 Modes Connect

```
OCEANEMBED
    │
    ├── MODE 1: MAP VIEW (Spatial intelligence)
    │     Whole region at one depth
    │     + Confidence/Uncertainty layer
    │
    ├── MODE 2: PROFILE VIEW (Vertical intelligence)
    │     One grid cell → 15-depth profile
    │     + ARGO comparison
    │     + Per-profile RMSE/Bias/Correlation
    │
    └── MODE 3: VALIDATION VIEW (Scientific proof)
          RMSE/Bias/Correlation summary
          Error map spatial distribution
          ARGO coverage indicator
```

Underneath all 3 modes, the model produces:

```
Input:  7 surface variables × 0.25° grid × temporal sequence
                         ↓
                   CNN + ConvLSTM
                         ↓
Output: 15 depths × 0.25° spatial grid
```

---

## Technical Differentiators (What Makes Us No.1)

### 1. Physics-Aware Loss (Key Differentiator)

A pure black-box CNN+ConvLSTM is easy for another team to reproduce.
Our model incorporates scientific constraints:

```
Total Loss = Prediction Loss
           + λ₁ × Vertical Smoothness Loss
           + λ₂ × Masked Data Loss
```

**Vertical Smoothness:** Ocean temperature shouldn't randomly jump:
```
28°C → 27.9°C → 27.8°C → 19°C ← suspicious → 27.5°C
```
Penalize unrealistic vertical discontinuities during training.

Don't claim this makes the model physically perfect — it makes the
reconstruction **more scientifically constrained** than a pure black-box.

### 2. Uncertainty Quantification

- Gaussian heteroscedastic head: predicted μ and log(σ²)
- NLL loss: `L_NLL = 0.5 * [log(σ²) + (y-μ)²/σ²]`
- Shows "24°C ± 0.8°C" not just "24°C"
- Maps where model is confident vs uncertain

### 3. Independent ARGO Validation

- Not just GLORYS (training target) — real independent observations
- Per-profile RMSE/Bias/Correlation
- Spatial ARGO coverage indicator
- Most credible form of validation for judges

### 4. Full Provenance Chain

- Every prediction traceable to: model version, data version, preprocessing version
- Dataset manifest with verified IDs
- Normalization statistics from training data only
- Reproducible pipeline

---

## What NOT To Build

| Don't | Why |
|-------|-----|
| Chatbot / unnecessary LLM | Not the product |
| Cyclone prediction | Out of scope |
| Hardware | Software-only requirement |
| Giant Transformer for show | Complexity ≠ quality |
| Fake real-time claims | Scientific dishonesty |
| 15 fancy features | Focus beats feature count |
| Generic dashboard | This is a scientific data product |
| Replace GODAS | Position as complementary |
| "Pure satellite" claims | Current products contain model-derived components |

---

## Winning Demo Sequence (9 Steps)

1. **Surface inputs** — show the 7 channels exist and are real data
2. **AI reconstruction** — CNN+ConvLSTM engine produces 15-depth field
3. **0.25° depth map** — Mode 1: spatial temperature at selected depth
4. **Click a cell** — transition to Mode 2
5. **15-depth profile** — Mode 2: vertical temperature structure
6. **Prediction vs ARGO** — independent validation comparison
7. **RMSE/Bias/Correlation** — quantitative evidence
8. **Confidence/uncertainty map** — where can we trust the prediction?
9. **Scientific Validation Mode** — Mode 3: judge-facing summary

**The story:** "Here is evidence our reconstruction is useful, measurable,
trustworthy, and scientifically defensible."

---

## Relationship to Existing Docs

- `problem-statement.md` — LOCKED official requirements (unchanged)
- `product-requirements.md` — FR-7 (uncertainty) and FR-10 (validation) are now **upgraded from PROPOSED to core product features**
- `user-workflows.md` — workflows 1–3 are now the 3 Modes defined above
- `scope-and-non-goals.md` — "What NOT To Build" table above reinforces scope
- `SYSTEM_MEMORY_DUMP.md` — §150 (final architecture) remains correct; this doc adds the product layer on top

---

## Priority Order for Implementation

1. **Reconstruction Engine** — prove data pipeline + model works (Phases 0–4)
2. **Scientific Validation** — RMSE/Bias/Correlation + ARGO comparison (Phase 5)
3. **Uncertainty** — add uncertainty head after deterministic works (Phase 5+)
4. **3-Mode UI** — Map + Profile + Validation views (Phase 7)
5. **Physics-aware loss** — add vertical smoothness after baseline works (Phase 4+)
