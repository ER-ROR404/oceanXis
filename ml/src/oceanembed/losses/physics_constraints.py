"""Physics constraint losses for subsurface temperature reconstruction.

Following spec v2.1 §14-§15, Appendix D:
- Vertical smoothness: penalize unrealistic adjacent-depth discontinuities
- Surface consistency: μ₀ consistent with GLORYS surface temperature
- Deep stabilization (optional): smoothness below 300m

Every constraint must survive an ablation (spec v2.1 §15).
"""

from __future__ import annotations

import torch

# Canonical depths in meters (spec v2.1 Appendix B, LOCKED)
CANONICAL_DEPTHS: list[int] = [
    0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000
]


def _depth_spacing() -> torch.Tensor:
    """Compute depth spacing Δz between adjacent canonical depths.

    Returns:
        Tensor of shape [14] with Δz for each adjacent pair.
    """
    depths = torch.tensor(CANONICAL_DEPTHS, dtype=torch.float32)
    return depths[1:] - depths[:-1]  # [14]


def vertical_smoothness_loss(mu: torch.Tensor) -> torch.Tensor:
    """Penalize unrealistic adjacent-depth discontinuities.

    Following spec v2.1 Appendix D:
      L_smooth = mean((μ_d - μ_{d+1})² / Δz_d)  for d = 0..13

    Args:
        mu: Predicted temperature [B, C=15, H, W].

    Returns:
        Scalar loss.
    """
    dz = _depth_spacing().to(mu.device)  # [14]
    # Differences between adjacent depth channels
    diffs = mu[:, :-1, :, :] - mu[:, 1:, :, :]  # [B, 14, H, W]
    # Normalize by depth spacing (broadcast dz over [B, H, W])
    dz_view = dz.view(1, -1, 1, 1)
    loss = (diffs ** 2 / dz_view).mean()
    return loss


def surface_consistency_loss(
    mu: torch.Tensor, glorys_surface: torch.Tensor
) -> torch.Tensor:
    """Ensure predicted near-surface temperature is consistent with GLORYS.

    Following spec v2.1 Appendix D:
      L_surface = mean((μ_0 - T_GLORYS_surface)²)

    Note: μ₀ is supervised against GLORYS surface temperature, NOT satellite SST
    directly (spec v2.1 Appendix D).

    Args:
        mu: Predicted temperature [B, C=15, H, W].
        glorys_surface: GLORYS surface temperature [B, 1, H, W].

    Returns:
        Scalar loss.
    """
    return ((mu[:, 0:1, :, :] - glorys_surface) ** 2).mean()


def deep_stabilization_loss(mu: torch.Tensor) -> torch.Tensor:
    """Optional: penalize instability in deep layers (> 300m).

    Following spec v2.1 §15:
      L_deep = mean((μ_d - μ_{d-1})² / Δz_d)  for d where depth > 300m

    Only applied if scientifically justified by results (ablation required).

    Args:
        mu: Predicted temperature [B, C=15, H, W].

    Returns:
        Scalar loss.
    """
    depths = torch.tensor(CANONICAL_DEPTHS, dtype=torch.float32)
    dz = _depth_spacing().to(mu.device)

    # Find indices where depth > 300m
    deep_indices = [i for i, d in enumerate(CANONICAL_DEPTHS) if d > 300]

    if len(deep_indices) == 0:
        return torch.tensor(0.0, device=mu.device, requires_grad=True)

    # Compute differences for deep layers
    total_loss = torch.tensor(0.0, device=mu.device)
    for idx in deep_indices:
        # d-1 is the previous depth index
        prev_idx = idx - 1
        diff = mu[:, idx, :, :] - mu[:, prev_idx, :, :]  # [B, H, W]
        spacing = dz[prev_idx]
        total_loss = total_loss + (diff ** 2 / spacing).mean()

    return total_loss / len(deep_indices)
