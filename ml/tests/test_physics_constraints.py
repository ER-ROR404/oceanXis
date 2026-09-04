"""Tests for physics constraint losses (TDD RED phase).

Following spec v2.1 §14-§15, Appendix D:
- Vertical smoothness: penalize unrealistic adjacent-depth discontinuities
- Surface consistency: μ₀ consistent with GLORYS surface temperature
- Deep stabilization (optional): smoothness below 300m
"""

from __future__ import annotations

import pytest
import torch

from oceanembed.losses.physics_constraints import (
    vertical_smoothness_loss,
    surface_consistency_loss,
    deep_stabilization_loss,
    CANONICAL_DEPTHS,
)

N_OUTPUT_CHANNELS = 15
TEST_H, TEST_W = 16, 16
BATCH = 2


class TestVerticalSmoothnessLoss:
    """Tests for vertical smoothness constraint (spec v2.1 §15)."""

    def test_smooth_profile_low_loss(self):
        """Smooth vertical profile has low smoothness loss."""
        mu = torch.linspace(25, 5, N_OUTPUT_CHANNELS).view(1, N_OUTPUT_CHANNELS, 1, 1).expand(
            BATCH, -1, TEST_H, TEST_W
        ).clone()
        loss = vertical_smoothness_loss(mu)
        assert loss.item() < 1.0

    def test_discontinuous_profile_high_loss(self):
        """Discontinuous profile has higher smoothness loss."""
        # Smooth profile
        mu_smooth = torch.linspace(25, 5, N_OUTPUT_CHANNELS).view(1, N_OUTPUT_CHANNELS, 1, 1).expand(
            BATCH, -1, TEST_H, TEST_W
        ).clone()
        # Add a sharp jump at depth 5 (index 1)
        mu_discontinuous = mu_smooth.clone()
        mu_discontinuous[:, 1, :, :] += 20.0  # huge jump at 5m

        loss_smooth = vertical_smoothness_loss(mu_smooth)
        loss_disc = vertical_smoothness_loss(mu_discontinuous)
        assert loss_disc > loss_smooth

    def test_loss_shape(self):
        """Loss is a scalar."""
        mu = torch.randn(BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)
        loss = vertical_smoothness_loss(mu)
        assert loss.shape == ()
        assert torch.isfinite(loss)

    def test_gradient_flow(self):
        """Gradients flow through smoothness loss."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8, requires_grad=True)
        loss = vertical_smoothness_loss(mu)
        loss.backward()
        assert mu.grad is not None

    def test_depth_spacing_accounted(self):
        """Loss accounts for non-uniform depth spacing (spec v2.1 Appendix D)."""
        # Create two profiles: one with jump at closely-spaced depths,
        # one with same jump at widely-spaced depths
        mu1 = torch.linspace(25, 5, N_OUTPUT_CHANNELS).view(1, N_OUTPUT_CHANNELS, 1, 1).expand(
            1, -1, 4, 4
        ).clone()
        mu2 = mu1.clone()

        # Same absolute jump but at different depth spacing
        # Index 0->1 is 0->5m (spacing=5), index 10->11 is 150->200m (spacing=50)
        jump = 5.0
        mu1[:, 1, :, :] += jump  # small spacing
        mu2[:, 11, :, :] += jump  # large spacing

        loss1 = vertical_smoothness_loss(mu1)
        loss2 = vertical_smoothness_loss(mu2)
        # Jump at closely-spaced depths should have higher loss
        assert loss1 > loss2


class TestSurfaceConsistencyLoss:
    """Tests for surface consistency constraint (spec v2.1 Appendix D)."""

    def test_surface_matches_target(self):
        """When μ₀ matches GLORYS surface, loss is low."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        glorys_surface = mu[:, 0:1, :, :].clone()  # extract surface
        loss = surface_consistency_loss(mu, glorys_surface)
        assert loss.item() < 1e-5

    def test_surface_mismatch_high_loss(self):
        """When μ₀ mismatches GLORYS surface, loss is high."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        glorys_surface = mu[:, 0:1, :, :] + 10.0  # large mismatch
        loss = surface_consistency_loss(mu, glorys_surface)
        assert loss.item() > 1.0

    def test_loss_uses_first_depth_channel(self):
        """Loss only compares first depth channel (0m) with GLORYS surface."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        glorys_surface = torch.randn(1, 1, 8, 8)
        loss = surface_consistency_loss(mu, glorys_surface)
        assert loss.shape == ()
        assert torch.isfinite(loss)

    def test_gradient_flow(self):
        """Gradients flow to mu through surface consistency."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8, requires_grad=True)
        glorys_surface = torch.randn(1, 1, 8, 8)
        loss = surface_consistency_loss(mu, glorys_surface)
        loss.backward()
        assert mu.grad is not None


class TestDeepStabilizationLoss:
    """Tests for optional deep stabilization (spec v2.1 §15)."""

    def test_deep_stability(self):
        """Stable deep profile has low loss."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        # Make deep layers nearly identical (stable)
        deep_temp = 4.0
        for i in range(len(CANONICAL_DEPTHS)):
            if CANONICAL_DEPTHS[i] >= 300:
                mu[:, i, :, :] = deep_temp
        loss = deep_stabilization_loss(mu)
        assert loss.item() < 0.5

    def test_loss_ignores_shallow_depths(self):
        """Loss only applies to depths > 300m."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        mu_orig = mu.clone()

        # Change only shallow depths (< 300m)
        for i in range(len(CANONICAL_DEPTHS)):
            if CANONICAL_DEPTHS[i] < 300:
                mu[:, i, :, :] += 100.0

        loss = deep_stabilization_loss(mu)
        # Should be similar to original loss since shallow changes are ignored
        loss_orig = deep_stabilization_loss(mu_orig)
        assert torch.allclose(loss, loss_orig, atol=1e-4)

    def test_loss_shape(self):
        """Loss is a scalar."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8)
        loss = deep_stabilization_loss(mu)
        assert loss.shape == ()
        assert torch.isfinite(loss)

    def test_gradient_flow(self):
        """Gradients flow through deep stabilization."""
        mu = torch.randn(1, N_OUTPUT_CHANNELS, 8, 8, requires_grad=True)
        loss = deep_stabilization_loss(mu)
        loss.backward()
        assert mu.grad is not None


class TestCanonicalDepths:
    """Tests for canonical depth definitions."""

    def test_15_depths(self):
        """Exactly 15 canonical depths."""
        assert len(CANONICAL_DEPTHS) == 15

    def test_depth_values(self):
        """Depths match spec v2.1 Appendix B."""
        expected = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]
        assert CANONICAL_DEPTHS == expected

    def test_monotonically_increasing(self):
        """Depths are monotonically increasing."""
        for i in range(1, len(CANONICAL_DEPTHS)):
            assert CANONICAL_DEPTHS[i] > CANONICAL_DEPTHS[i - 1]
