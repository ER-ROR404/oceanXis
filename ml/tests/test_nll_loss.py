"""Tests for Gaussian NLL loss with aleatoric uncertainty (TDD RED phase).

Following spec v2.1 §11, Appendix D:
- L_NLL = 0.5 * mean(log(σ²) + (T_obs - μ)² / σ²)
- σ² = softplus(raw_log_var) + ε, ε = 1e-6
"""

from __future__ import annotations

import pytest
import torch

from oceanembed.losses.nll_loss import GaussianNLLLoss, masked_nll_loss

N_OUTPUT_CHANNELS = 15
TEST_H, TEST_W = 16, 16
BATCH = 2


class TestGaussianNLLLoss:
    """Tests for Gaussian NLL loss."""

    def test_basic_loss_computation(self):
        """Loss computes a finite scalar from mu, log_var, target."""
        loss_fn = GaussianNLLLoss()
        mu = torch.randn(BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)
        log_var = torch.randn(BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)
        target = torch.randn(BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)

        loss = loss_fn(mu, log_var, target)
        assert loss.shape == ()
        assert torch.isfinite(loss)
        assert loss.item() > 0

    def test_loss_decreases_with_better_prediction(self):
        """Loss decreases as mu approaches target."""
        loss_fn = GaussianNLLLoss()
        log_var = torch.zeros(1, N_OUTPUT_CHANNELS, 8, 8)  # fixed variance
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)

        mu_bad = target + 2.0
        mu_good = target + 0.1

        loss_bad = loss_fn(mu_bad, log_var, target)
        loss_good = loss_fn(mu_good, log_var, target)
        assert loss_good < loss_bad

    def test_loss_decreases_with_better_variance(self):
        """Loss decreases as variance matches noise level."""
        loss_fn = GaussianNLLLoss()
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        mu = target.clone()  # perfect mean
        noise = torch.randn_like(target) * 0.5
        noisy_target = target + noise

        # Too-high variance
        log_var_high = torch.ones(1, N_OUTPUT_CHANNELS, 8, 8) * 2.0
        # Well-matched variance (sigma ≈ 0.5 → log_var ≈ log(0.25))
        log_var_good = torch.full_like(log_var_high, -1.4)

        loss_high = loss_fn(mu, log_var_high, noisy_target)
        loss_good = loss_fn(mu, log_var_good, noisy_target)
        assert loss_good < loss_high

    def test_perfect_prediction_low_loss(self):
        """Perfect prediction with tight variance gives low loss."""
        loss_fn = GaussianNLLLoss()
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        log_var = torch.full_like(target, -10.0)  # very tight variance

        loss = loss_fn(target, log_var, target)
        assert loss.item() < 1.0

    def test_numerical_stability(self):
        """Loss remains finite with extreme log_var values."""
        loss_fn = GaussianNLLLoss()
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)

        # Very negative log_var (small variance)
        log_var_neg = torch.full_like(target, -20.0)
        loss_neg = loss_fn(mu, log_var_neg, target)
        assert torch.isfinite(loss_neg)

        # Very positive log_var (large variance)
        log_var_pos = torch.full_like(target, 20.0)
        loss_pos = loss_fn(mu, log_var_pos, target)
        assert torch.isfinite(loss_pos)

    def test_gradient_flow(self):
        """Gradients flow to both mu and log_var."""
        loss_fn = GaussianNLLLoss()
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8, requires_grad=True)
        log_var = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8, requires_grad=True)
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)

        loss = loss_fn(mu, log_var, target)
        loss.backward()
        assert mu.grad is not None
        assert log_var.grad is not None
        assert torch.isfinite(mu.grad).all()
        assert torch.isfinite(log_var.grad).all()

    def test_symmetry_in_loss(self):
        """Loss is symmetric: overpredicting and underpredicting equally should give same loss."""
        loss_fn = GaussianNLLLoss()
        log_var = torch.zeros(1, N_OUTPUT_CHANNELS, 8, 8)
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)

        loss_over = loss_fn(target + 1.0, log_var, target)
        loss_under = loss_fn(target - 1.0, log_var, target)
        assert torch.allclose(loss_over, loss_under, atol=1e-5)


class TestMaskedNLLLoss:
    """Tests for masked NLL loss (handles invalid ocean cells)."""

    def test_masked_loss_skips_invalid(self):
        """Loss ignores invalid cells (mask=0)."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        log_var = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        mask = torch.ones(1, 1, 8, 8)  # all valid
        mask[0, 0, :4, :4] = 0  # half invalid

        loss_all_valid = masked_nll_loss(mu, log_var, target, mask=torch.ones_like(mask))
        loss_partial = masked_nll_loss(mu, log_var, target, mask=mask)

        # Should still produce finite loss
        assert torch.isfinite(loss_partial)

    def test_masked_loss_nan_targets(self):
        """Loss stays finite when targets are NaN over masked cells.

        Regression: 0 * NaN = NaN in floating point. Real GLORYS data has
        NaN at masked land/shallow cells; nll * mask must not re-introduce
        NaN into the denominator.
        """
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        log_var = torch.zeros(1, N_OUTPUT_CHANNELS, 8, 8)
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        target[0, :, :4, :4] = torch.nan  # NaN over invalid cells
        mask = torch.ones(1, 1, 8, 8)
        mask[0, 0, :4, :4] = 0  # same cells invalid

        loss = masked_nll_loss(mu, log_var, target, mask=mask)
        assert torch.isfinite(loss)

    def test_masked_loss_nan_at_valid_cell_depth(self):
        """Loss stays finite when a valid cell has NaN at some depths.

        Regression: real GLORYS has NaN at deep depths below the local
        seafloor (e.g. 1000m target over shelf cells) even though the
        spatial mask marks the cell valid. NaN targets at valid cells
        must not poison the loss.
        """
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        log_var = torch.zeros(1, N_OUTPUT_CHANNELS, 8, 8)
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        mask = torch.ones(1, 1, 8, 8)  # all cells spatially valid
        # Deep depths (last 5 channels) are NaN everywhere — shelf cells
        target[0, -5:, :, :] = torch.nan

        loss = masked_nll_loss(mu, log_var, target, mask=mask)
        assert torch.isfinite(loss)

        # Loss should only average over finite cells
        var_const = float(torch.nn.functional.softplus(torch.zeros(()))) + 1e-6
        full_nll = 0.5 * (torch.log(torch.tensor(var_const)) + (target - mu) ** 2 / var_const)
        valid_nll = full_nll.masked_fill(~torch.isfinite(target), 0.0)
        n_valid = torch.isfinite(target).float().sum()
        expected = valid_nll.sum() / n_valid
        assert torch.allclose(loss, expected, atol=1e-5)

    def test_masked_loss_zero_mask(self):
        """Loss handles edge case of all-invalid mask gracefully."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        log_var = torch.zeros(1, N_OUTPUT_CHANNELS, 8, 8)
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        mask = torch.zeros(1, 1, 8, 8)

        loss = masked_nll_loss(mu, log_var, target, mask=mask)
        # Should return 0 or a small value, not NaN
        assert torch.isfinite(loss)

    def test_masked_loss_matches_unmasked_when_all_valid(self):
        """When all cells valid, masked loss equals unmasked loss."""
        loss_fn = GaussianNLLLoss()
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        log_var = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        target = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        mask = torch.ones(1, 1, 8, 8)

        loss_unmasked = loss_fn(mu, log_var, target)
        loss_masked = masked_nll_loss(mu, log_var, target, mask=mask)
        assert torch.allclose(loss_unmasked, loss_masked, atol=1e-5)

    def test_masked_loss_dataloader_mask_shape(self):
        """Handles 3D masks [B, H, W] as produced by the DataLoader stack."""
        mu = torch.randn(2, N_OUTPUT_CHANNELS, 8, 8)
        log_var = torch.zeros(2, N_OUTPUT_CHANNELS, 8, 8)
        target = torch.randn(2, N_OUTPUT_CHANNELS, 8, 8)
        mask = torch.ones(2, 8, 8)  # 3D, no channel dim
        mask[:, :4, :4] = 0.0  # some invalid cells

        loss = masked_nll_loss(mu, log_var, target, mask=mask)
        assert torch.isfinite(loss)

        # Equality: masked loss over valid cells equals unmasked loss over
        # the same (valid) set when variance is constant (log_var = 0).
        # variance = softplus(0) + 1e-6 = log(2) + 1e-6
        var_const = float(torch.nn.functional.softplus(torch.zeros(()))) + 1e-6
        full_nll = 0.5 * (torch.log(torch.tensor(var_const)) + (target - mu) ** 2 / var_const)
        # valid cells = all except masked-out top-left quadrant
        expanded = mask.unsqueeze(1).expand_as(full_nll)
        valid_nll = full_nll * expanded
        expected = valid_nll.sum() / expanded.sum()
        assert torch.allclose(loss, expected, atol=1e-5)
