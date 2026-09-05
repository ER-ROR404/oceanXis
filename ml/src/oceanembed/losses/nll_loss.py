"""Gaussian NLL loss with aleatoric uncertainty.

Following spec v2.1 §11, Appendix D:
  L_NLL = 0.5 * mean(log(σ²) + (T_obs - μ)² / σ²)
  where σ² = softplus(raw_log_var) + ε, ε = 1e-6

This trains both accurate mean prediction and meaningful variance estimation.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class GaussianNLLLoss(nn.Module):
    """Gaussian Negative Log-Likelihood loss for heteroscedastic uncertainty.

    The network outputs mu (mean prediction) and log_variance (raw log-variance).
    Actual variance is computed as softplus(log_variance) + eps for numerical stability.
    """

    def __init__(self, eps: float = 1e-6) -> None:
        super().__init__()
        self.eps = eps

    def forward(
        self, mu: torch.Tensor, log_var: torch.Tensor, target: torch.Tensor
    ) -> torch.Tensor:
        """Compute Gaussian NLL loss.

        Args:
            mu: Predicted mean [B, C, H, W].
            log_var: Raw log-variance [B, C, H, W].
            target: Observed values [B, C, H, W].

        Returns:
            Scalar loss.
        """
        # σ² = softplus(raw_variance) + ε  (spec v2.1 §11)
        variance = torch.nn.functional.softplus(log_var) + self.eps
        # L_NLL = 0.5 * mean(log(σ²) + (target - μ)² / σ²)  (spec v2.1 Appendix D)
        nll = 0.5 * (torch.log(variance) + (target - mu) ** 2 / variance)
        return nll.mean()


def masked_nll_loss(
    mu: torch.Tensor,
    log_var: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    eps: float = 1e-6,
) -> torch.Tensor:
    """NLL loss masked to valid ocean cells only.

    The effective mask is ``mask AND finite(target)``: real GLORYS is NaN
    at land cells AND at individual depth levels below the local seafloor
    (e.g. the 1000m target over shelf cells). Both sources must be excluded
    from the loss, and neither may poison the autograd graph (0 * NaN = NaN).

    Args:
        mu: Predicted mean [B, C, H, W].
        log_var: Raw log-variance [B, C, H, W].
        target: Observed values [B, C, H, W].
        mask: Binary validity mask [B, 1, H, W]. 1 = valid, 0 = invalid.
        eps: Small constant for numerical stability.

    Returns:
        Scalar loss (mean over valid cells only).
    """
    # Normalize mask to [B, 1, H, W]:
    # - 3D [B, H, W] comes from DataLoader stack of per-sample masks
    # - 4D [B, 1, H, W] is the canonical form
    if mask.dim() == 3:
        mask = mask.unsqueeze(1)
    if mask.dim() == 4 and mask.shape[1] == 1 and mu.shape[1] > 1:
        mask = mask.expand_as(mu)

    # Effective mask = spatial mask AND finite target. NaN target cells
    # (land or below-seafloor depths) are excluded entirely — a zeroed
    # target with mu != 0 would add spurious error to the loss and NaN
    # gradient risk to the graph.
    effective_mask = (mask.bool() & torch.isfinite(target)).float()

    # Replace invalid targets with 0 so nll is finite, then mask it out.
    target_safe = torch.where(
        torch.isfinite(target), target, torch.zeros_like(target)
    )
    variance = torch.nn.functional.softplus(log_var) + eps
    nll = 0.5 * (torch.log(variance) + (target_safe - mu) ** 2 / variance)

    masked_nll = nll * effective_mask
    n_valid = effective_mask.sum().clamp(min=1.0)
    return masked_nll.sum() / n_valid
