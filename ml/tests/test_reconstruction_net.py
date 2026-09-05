"""Tests for OceanEmbedNet reconstruction model (TDD RED phase).

Following spec v2.1 §7-§10:
- CNN spatial encoder (3x3 conv, 32->64->128 features, 3 downsample stages)
- ConvLSTM temporal encoder (128 input channels, configurable hidden/layers)
- Depth decoder (128->64->32, upsample to H x W, 15 output channels)
- Output: mu [B, 15, H, W] + log_variance [B, 15, H, W]
- Coordinate encoding: sin/cos seasonal + lat/lon spatial fields (configurable)
"""

from __future__ import annotations

import pytest
import torch

from oceanembed.models.reconstruction_net import (
    OceanEmbedNet,
    CNNEncoder,
    ConvLSTMBlock,
    DepthDecoder,
    CoordinateEncoder,
)

# ── Frozen constants from spec v2.1 ──────────────────────────────────────

N_INPUT_CHANNELS = 7   # SST, SSS, SSH, Current U/V, Wind U/V
N_OUTPUT_CHANNELS = 15  # temperature at 15 depths
T_WINDOW = 7            # 7-day temporal window
# Using small test grid for speed; full grid is H=101, W=241
TEST_H, TEST_W = 16, 16
BATCH = 2


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def surface_input():
    """Batch of 7-day 7-channel surface observations."""
    return torch.randn(BATCH, T_WINDOW, N_INPUT_CHANNELS, TEST_H, TEST_W)


@pytest.fixture
def target_temp():
    """Batch of 15-depth temperature targets."""
    return torch.randn(BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)


@pytest.fixture
def day_of_year():
    """Batch of day-of-year values (1-365)."""
    return torch.randint(1, 366, (BATCH,))


@pytest.fixture
def latlon_fields():
    """Batch of lat/lon coordinate fields."""
    lat = torch.linspace(5.0, 30.0, TEST_H).unsqueeze(1).expand(-1, TEST_W)
    lon = torch.linspace(45.0, 105.0, TEST_W).unsqueeze(0).expand(TEST_H, -1)
    return lat, lon


# ── Test: Coordinate Encoder ──────────────────────────────────────────────

class TestCoordinateEncoder:
    """Tests for coordinate/seasonal encoding (spec v2.1 §7)."""

    def test_seasonal_encoding_shape(self):
        """sin/cos seasonal encoding produces 2 channels from day-of-year."""
        enc = CoordinateEncoder(use_seasonal=True, use_spatial=False)
        doy = torch.tensor([1, 182, 365])
        out = enc(doy, batch_size=3, height=4, width=4)
        # Should produce [B, 2, H, W] — sin + cos channels
        assert out.shape == (3, 2, 4, 4)

    def test_spatial_encoding_shape(self):
        """Lat/lon coordinate fields produce 2 channels."""
        enc = CoordinateEncoder(use_seasonal=False, use_spatial=True)
        lat = torch.linspace(5.0, 30.0, 8).unsqueeze(1).expand(-1, 8)
        lon = torch.linspace(45.0, 105.0, 8).unsqueeze(0).expand(8, -1)
        out = enc(lat=lat, lon=lon, batch_size=2, height=8, width=8)
        assert out.shape == (2, 2, 8, 8)

    def test_combined_encoding_shape(self):
        """Combined seasonal + spatial produces 4 channels."""
        enc = CoordinateEncoder(use_seasonal=True, use_spatial=True)
        doy = torch.tensor([100, 200])
        lat = torch.linspace(5.0, 30.0, 8).unsqueeze(1).expand(-1, 8)
        lon = torch.linspace(45.0, 105.0, 8).unsqueeze(0).expand(8, -1)
        out = enc(day_of_year=doy, lat=lat, lon=lon, batch_size=2, height=8, width=8)
        assert out.shape == (2, 4, 8, 8)  # 2 seasonal + 2 spatial

    def test_disabled_encoding_returns_none(self):
        """When both disabled, returns None."""
        enc = CoordinateEncoder(use_seasonal=False, use_spatial=False)
        assert enc() is None

    def test_seasonal_values_in_range(self):
        """sin/cos outputs are in [-1, 1]."""
        enc = CoordinateEncoder(use_seasonal=True, use_spatial=False)
        doy = torch.arange(1, 366)
        out = enc(doy, batch_size=1, height=1, width=1)
        assert out.min() >= -1.0
        assert out.max() <= 1.0


# ── Test: CNN Encoder ─────────────────────────────────────────────────────

class TestCNNEncoder:
    """Tests for CNN spatial encoder (spec v2.1 §8)."""

    def test_encoder_reduces_spatial_dim(self):
        """3 downsample stages reduce spatial dimensions by 8x."""
        encoder = CNNEncoder(in_channels=N_INPUT_CHANNELS)
        x = torch.randn(BATCH, N_INPUT_CHANNELS, TEST_H, TEST_W)
        out = encoder(x)
        # After 3 downsample stages: H/8 x W/8
        assert out.shape[0] == BATCH
        assert out.shape[1] == 128  # final feature count
        assert out.shape[2] == TEST_H // 8
        assert out.shape[3] == TEST_W // 8

    def test_encoder_feature_channels(self):
        """Encoder progression: 32 -> 64 -> 128."""
        encoder = CNNEncoder(in_channels=N_INPUT_CHANNELS)
        x = torch.randn(1, N_INPUT_CHANNELS, 32, 32)
        out = encoder(x)
        assert out.shape[1] == 128

    def test_encoder_with_coordinate_channels(self):
        """Encoder handles extra coordinate channels (7 + 4 = 11)."""
        encoder = CNNEncoder(in_channels=N_INPUT_CHANNELS + 4)
        x = torch.randn(1, N_INPUT_CHANNELS + 4, TEST_H, TEST_W)
        out = encoder(x)
        assert out.shape[1] == 128

    def test_encoder_deterministic(self):
        """Same input produces same output (no stochastic layers)."""
        encoder = CNNEncoder(in_channels=N_INPUT_CHANNELS)
        encoder.eval()
        x = torch.randn(1, N_INPUT_CHANNELS, 16, 16)
        out1 = encoder(x)
        out2 = encoder(x)
        assert torch.allclose(out1, out2)


# ── Test: ConvLSTM Block ─────────────────────────────────────────────────

class TestConvLSTMBlock:
    """Tests for ConvLSTM temporal encoder (spec v2.1 §9)."""

    def test_temporal_processing(self):
        """ConvLSTM processes T timesteps into single hidden state."""
        block = ConvLSTMBlock(in_channels=128, hidden_channels=128, num_layers=1)
        h, w = TEST_H // 8, TEST_W // 8
        x = torch.randn(BATCH, T_WINDOW, 128, h, w)
        hidden = block(x)
        # Output: [B, hidden_channels, H', W']
        assert hidden.shape == (BATCH, 128, h, w)

    def test_multiple_layers(self):
        """Multi-layer ConvLSTM processes correctly."""
        block = ConvLSTMBlock(in_channels=128, hidden_channels=64, num_layers=2)
        h, w = 4, 4
        x = torch.randn(1, T_WINDOW, 128, h, w)
        hidden = block(x)
        assert hidden.shape == (1, 64, h, w)

    def test_hidden_channels_configurable(self):
        """Hidden channels are configurable per spec."""
        for hidden in [32, 64, 128]:
            block = ConvLSTMBlock(in_channels=128, hidden_channels=hidden, num_layers=1)
            x = torch.randn(1, T_WINDOW, 128, 4, 4)
            hidden_out = block(x)
            assert hidden_out.shape[1] == hidden

    def test_gradient_flow(self):
        """Gradients flow through ConvLSTM."""
        block = ConvLSTMBlock(in_channels=128, hidden_channels=128, num_layers=1)
        x = torch.randn(1, T_WINDOW, 128, 4, 4, requires_grad=True)
        hidden = block(x)
        hidden.sum().backward()
        assert x.grad is not None


# ── Test: Depth Decoder ──────────────────────────────────────────────────

class TestDepthDecoder:
    """Tests for depth decoder (spec v2.1 §10)."""

    def test_decoder_output_shape(self):
        """Decoder produces [B, 15, H, W] from latent features."""
        decoder = DepthDecoder(out_channels=N_OUTPUT_CHANNELS)
        h, w = TEST_H // 8, TEST_W // 8
        x = torch.randn(BATCH, 128, h, w)
        mu, log_var = decoder(x)
        assert mu.shape == (BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)
        assert log_var.shape == (BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)

    def test_mu_log_var_independent(self):
        """mu and log_var are separate heads, not the same tensor."""
        decoder = DepthDecoder(out_channels=N_OUTPUT_CHANNELS)
        x = torch.randn(1, 128, 4, 4)
        mu, log_var = decoder(x)
        assert mu is not log_var
        # Different values
        assert not torch.allclose(mu, log_var)

    def test_decoder_reconstruction(self):
        """Decoder can upsample from small spatial dims to full grid."""
        decoder = DepthDecoder(out_channels=N_OUTPUT_CHANNELS)
        x = torch.randn(1, 128, 2, 2)  # Very small spatial
        mu, log_var = decoder(x)
        # Should upsample to a reasonable size
        assert mu.shape[2] >= 2
        assert mu.shape[3] >= 2

    def test_decoder_odd_grid_exact_size(self):
        """Decoder produces EXACT target size for odd grids (BoB 69x81).

        scale_factor-based upsampling (x8) of an odd grid floor-divides:
        69//8 = 8 -> 8*8 = 64, but the real grid is 69 wide. The decoder
        must interpolate to the exact target size.
        """
        decoder = DepthDecoder(out_channels=N_OUTPUT_CHANNELS)
        latent_h, latent_w = 69 // 8, 81 // 8  # 8, 10
        x = torch.randn(BATCH, 128, latent_h, latent_w)
        mu, log_var = decoder(x, target_size=(69, 81))
        assert mu.shape == (BATCH, N_OUTPUT_CHANNELS, 69, 81)
        assert log_var.shape == (BATCH, N_OUTPUT_CHANNELS, 69, 81)


# ── Test: Full OceanEmbedNet ──────────────────────────────────────────────

class TestOceanEmbedNet:
    """Tests for the complete end-to-end model."""

    def test_forward_pass(self, surface_input, day_of_year):
        """Full forward pass produces mu and log_var."""
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
            use_seasonal=True,
            use_spatial=False,
        )
        mu, log_var = model(surface_input, day_of_year=day_of_year)
        assert mu.shape == (BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)
        assert log_var.shape == (BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)

    def test_forward_no_coordinates(self, surface_input):
        """Forward pass works without coordinate encoding."""
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
            use_seasonal=False,
            use_spatial=False,
        )
        mu, log_var = model(surface_input)
        assert mu.shape == (BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)

    def test_forward_with_spatial_coords(self, surface_input, day_of_year, latlon_fields):
        """Forward pass with both seasonal and spatial coordinates."""
        lat, lon = latlon_fields
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
            use_seasonal=True,
            use_spatial=True,
        )
        mu, log_var = model(surface_input, day_of_year=day_of_year, lat=lat, lon=lon)
        assert mu.shape == (BATCH, N_OUTPUT_CHANNELS, TEST_H, TEST_W)

    def test_single_sample(self):
        """Forward pass works with batch size 1."""
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
        )
        x = torch.randn(1, T_WINDOW, N_INPUT_CHANNELS, TEST_H, TEST_W)
        mu, log_var = model(x)
        assert mu.shape == (1, N_OUTPUT_CHANNELS, TEST_H, TEST_W)

    def test_variance_positive(self, surface_input):
        """log_variance produces valid variance (softplus ensures positive)."""
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
        )
        mu, log_var = model(surface_input)
        # softplus(raw) + eps > 0 always; log_var is raw log variance
        # Actual variance = softplus(log_var) + eps
        variance = torch.nn.functional.softplus(log_var) + 1e-6
        assert (variance > 0).all()

    def test_gradient_flow_end_to_end(self, surface_input, target_temp, day_of_year):
        """Gradients flow through the entire model."""
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
            use_seasonal=True,
            use_spatial=False,
        )
        mu, log_var = model(surface_input, day_of_year=day_of_year)
        loss = mu.sum() + log_var.sum()
        loss.backward()
        for name, param in model.named_parameters():
            assert param.grad is not None, f"No gradient for {name}"

    def test_model_parameter_count_reasonable(self):
        """Model has reasonable parameter count (< 50M for Colab T4)."""
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
        )
        n_params = sum(p.numel() for p in model.parameters())
        assert n_params < 50_000_000, f"Too many parameters: {n_params}"
        assert n_params > 100_000, f"Too few parameters: {n_params}"

    def test_deterministic_eval(self, surface_input, day_of_year):
        """Model is deterministic in eval mode."""
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
            use_seasonal=True,
            use_spatial=False,
        )
        model.eval()
        mu1, log_var1 = model(surface_input, day_of_year=day_of_year)
        mu2, log_var2 = model(surface_input, day_of_year=day_of_year)
        assert torch.allclose(mu1, mu2)
        assert torch.allclose(log_var1, log_var2)

    def test_custom_grid_sizes(self):
        """Model works with different H, W sizes."""
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
            use_seasonal=False,
            use_spatial=False,
        )
        for h, w in [(16, 16), (32, 32), (16, 32), (32, 16)]:
            x = torch.randn(1, T_WINDOW, N_INPUT_CHANNELS, h, w)
            mu, log_var = model(x)
            assert mu.shape == (1, N_OUTPUT_CHANNELS, h, w)

    def test_real_bog_grid_odd_dims(self):
        """Model produces EXACT BoB grid (69x81) — odd dimensions.

        Regression: 3x MaxPool2d(2) then 3x scale_factor=2 Upsample maps
        69x81 -> 64x80, breaking train loss vs. the true target grid.
        """
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
            use_seasonal=False,
            use_spatial=False,
        )
        x = torch.randn(1, T_WINDOW, N_INPUT_CHANNELS, 69, 81)
        mu, log_var = model(x)
        assert mu.shape == (1, N_OUTPUT_CHANNELS, 69, 81)
        assert log_var.shape == (1, N_OUTPUT_CHANNELS, 69, 81)

    def test_full_domain_odd_grid(self):
        """Full North Indian Ocean domain (101x241) also odd — must match."""
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
            use_seasonal=False,
            use_spatial=False,
        )
        x = torch.randn(1, T_WINDOW, N_INPUT_CHANNELS, 101, 241)
        mu, log_var = model(x)
        assert mu.shape == (1, N_OUTPUT_CHANNELS, 101, 241)

    def test_trivial_overfit(self):
        """Model can overfit a tiny batch (sanity check)."""
        model = OceanEmbedNet(
            in_channels=N_INPUT_CHANNELS,
            out_channels=N_OUTPUT_CHANNELS,
            use_seasonal=False,
            use_spatial=False,
        )
        x = torch.randn(1, T_WINDOW, N_INPUT_CHANNELS, 16, 16)
        target = torch.randn(1, N_OUTPUT_CHANNELS, 16, 16)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

        initial_loss = None
        for _ in range(300):
            optimizer.zero_grad()
            mu, log_var = model(x)
            variance = torch.nn.functional.softplus(log_var) + 1e-6
            loss = 0.5 * (torch.log(variance) + (target - mu) ** 2 / variance).mean()
            if initial_loss is None:
                initial_loss = loss.item()
            loss.backward()
            optimizer.step()

        # After 300 steps, loss should decrease significantly
        assert loss.item() < initial_loss * 0.15, (
            f"Model failed to overfit: initial={initial_loss:.4f}, final={loss.item():.4f}"
        )
