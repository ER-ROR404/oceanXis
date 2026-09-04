"""OceanEmbedNet — Multi-scale CNN encoder + ConvLSTM + depth decoder.

Following spec v2.1 §7-§10:
  Input: [B, T=7, C=7, H, W]
    → Coordinate/seasonal context
    → CNN spatial encoder (3x3 conv, 32→64→128, 3 downsample stages)
    → ConvLSTM temporal encoder
    → Depth decoder (128→64→32, upsample, 15 output channels)
    → Output: μ [B, 15, H, W] + log_variance [B, 15, H, W]

Architecture name: Multi-scale CNN encoder-decoder (NOT U-Net unless skip
connections are present — spec v2.1 §8).
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn


class CoordinateEncoder(nn.Module):
    """Coordinate/seasonal context encoder (spec v2.1 §7).

    Produces:
      - 2 seasonal channels: sin(2π * doy / 365.25), cos(2π * doy / 365.25)
      - 2 spatial channels: normalized latitude, normalized longitude

    The model implementation makes this configurable (spec v2.1 §7).
    """

    def __init__(self, use_seasonal: bool = True, use_spatial: bool = True) -> None:
        super().__init__()
        self.use_seasonal = use_seasonal
        self.use_spatial = use_spatial
        self.n_channels = (2 if use_seasonal else 0) + (2 if use_spatial else 0)

    def forward(
        self,
        day_of_year: torch.Tensor | None = None,
        lat: torch.Tensor | None = None,
        lon: torch.Tensor | None = None,
        batch_size: int = 0,
        height: int = 0,
        width: int = 0,
    ) -> torch.Tensor | None:
        """Generate coordinate encoding.

        Args:
            day_of_year: [B] integer day-of-year values (1-365).
            lat: [H, W] or [B, H, W] latitude values.
            lon: [H, W] or [B, H, W] longitude values.
            batch_size: Batch dimension (used when seasonal encoding is needed
                        but lat/lon are provided for spatial only).
            height: Spatial height (used when only seasonal encoding).
            width: Spatial width (used when only seasonal encoding).

        Returns:
            [B, n_channels, H, W] or None if both disabled.
        """
        if not self.use_seasonal and not self.use_spatial:
            return None

        parts = []

        if self.use_seasonal and day_of_year is not None:
            B = day_of_year.shape[0]
            # Determine spatial dims from lat if available, else use provided
            if lat is not None:
                H, W = lat.shape[-2], lat.shape[-1]
            else:
                H, W = height, width
            doy_float = day_of_year.float().view(B, 1, 1, 1).expand(B, 1, H, W)
            seasonal_sin = torch.sin(2 * math.pi * doy_float / 365.25)
            seasonal_cos = torch.cos(2 * math.pi * doy_float / 365.25)
            parts.append(torch.cat([seasonal_sin, seasonal_cos], dim=1))

        if self.use_spatial and lat is not None and lon is not None:
            B = batch_size if batch_size > 0 else (parts[0].shape[0] if parts else 1)
            H, W = lat.shape[-2], lat.shape[-1]
            # Normalize to [0, 1] range
            lat_min, lat_max = lat.min(), lat.max()
            lon_min, lon_max = lon.min(), lon.max()
            lat_norm = (lat - lat_min) / (lat_max - lat_min + 1e-8)
            lon_norm = (lon - lon_min) / (lon_max - lon_min + 1e-8)
            # Expand to batch
            lat_field = lat_norm.unsqueeze(0).expand(B, 1, H, W)
            lon_field = lon_norm.unsqueeze(0).expand(B, 1, H, W)
            parts.append(torch.cat([lat_field, lon_field], dim=1))

        if not parts:
            return None

        return torch.cat(parts, dim=1)


class CNNEncoder(nn.Module):
    """Multi-scale CNN spatial encoder (spec v2.1 §8).

    Architecture:
      Input: C_in channels
        → Conv 3×3 → 32 features → downsample
        → Conv 3×3 → 64 features → downsample
        → Conv 3×3 → 128 features → downsample

    Uses BatchNorm + ReLU activations.
    Downsampling via MaxPool2d(2).
    """

    def __init__(self, in_channels: int = 7) -> None:
        super().__init__()
        self.stages = nn.Sequential(
            # Stage 1: in_channels -> 32
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            # Stage 2: 32 -> 64
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            # Stage 3: 64 -> 128
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Encode spatial features.

        Args:
            x: [B, C_in, H, W] surface observations.

        Returns:
            [B, 128, H/8, W/8] spatial features.
        """
        return self.stages(x)


class ConvLSTMCell(nn.Module):
    """Single ConvLSTM cell.

    Implements the ConvLSTM equations:
      i = σ(W_xi * X + W_hi * H + b_i)
      f = σ(W_xf * X + W_hf * H + b_f)
      g = tanh(W_xg * X + W_hg * H + b_g)
      o = σ(W_xo * X + W_ho * H + b_o)
      C' = f ⊙ C + i ⊙ g
      H' = o ⊙ tanh(C')
    """

    def __init__(self, in_channels: int, hidden_channels: int, kernel_size: int = 3) -> None:
        super().__init__()
        padding = kernel_size // 2
        self.hidden_channels = hidden_channels

        # Combined conv for all gates (more efficient than separate convs)
        self.conv = nn.Conv2d(
            in_channels + hidden_channels,
            4 * hidden_channels,
            kernel_size,
            padding=padding,
        )
        self.norm = nn.BatchNorm2d(4 * hidden_channels)

    def forward(
        self, x: torch.Tensor, hidden: tuple[torch.Tensor, torch.Tensor]
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Single step.

        Args:
            x: [B, C_in, H, W] input at current timestep.
            hidden: (h_prev, c_prev) each [B, hidden_channels, H, W].

        Returns:
            (h_new, c_new) each [B, hidden_channels, H, W].
        """
        h_prev, c_prev = hidden
        combined = torch.cat([x, h_prev], dim=1)
        gates = self.norm(self.conv(combined))
        i, f, g, o = gates.chunk(4, dim=1)
        i = torch.sigmoid(i)
        f = torch.sigmoid(f)
        g = torch.tanh(g)
        o = torch.sigmoid(o)
        c_new = f * c_prev + i * g
        h_new = o * torch.tanh(c_new)
        return h_new, c_new


class ConvLSTMBlock(nn.Module):
    """Multi-layer ConvLSTM temporal encoder (spec v2.1 §9).

    Processes [B, T, C, H, W] into [B, hidden_channels, H, W].
    """

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        num_layers: int = 1,
        kernel_size: int = 3,
    ) -> None:
        super().__init__()
        self.num_layers = num_layers
        self.hidden_channels = hidden_channels

        self.cells = nn.ModuleList()
        for layer_idx in range(num_layers):
            layer_in = in_channels if layer_idx == 0 else hidden_channels
            self.cells.append(ConvLSTMCell(layer_in, hidden_channels, kernel_size))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Process temporal sequence.

        Args:
            x: [B, T, C, H, W] temporal sequence.

        Returns:
            [B, hidden_channels, H, W] final hidden state.
        """
        B, T, C, H, W = x.shape

        # Initialize hidden states for all layers
        hidden_states = []
        for cell in self.cells:
            h = torch.zeros(B, cell.hidden_channels, H, W, device=x.device, dtype=x.dtype)
            c = torch.zeros(B, cell.hidden_channels, H, W, device=x.device, dtype=x.dtype)
            hidden_states.append((h, c))

        # Process each timestep
        for t in range(T):
            inp = x[:, t]  # [B, C, H, W]
            for layer_idx, cell in enumerate(self.cells):
                h_new, c_new = cell(inp, hidden_states[layer_idx])
                hidden_states[layer_idx] = (h_new, c_new)
                inp = h_new

        # Return final hidden state of last layer
        return hidden_states[-1][0]


class DepthDecoder(nn.Module):
    """Depth decoder with separate μ and log_variance heads (spec v2.1 §10).

    Architecture:
      [B, 128, H', W']
        → Upsample + Conv 3×3 → 64 features
        → Upsample + Conv 3×3 → 32 features
        → μ head: Conv 1×1 → 15 channels
        → log_var head: Conv 1×1 → 15 channels
    """

    def __init__(self, out_channels: int = 15) -> None:
        super().__init__()
        self.decoder = nn.Sequential(
            # Upsample stage 1: H'/8 -> H'/4
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(128, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            # Upsample stage 2: H'/4 -> H'/2
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(64, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            # Upsample stage 3: H'/2 -> H'
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(32, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
        )
        # Separate heads for mean and variance (spec v2.1 §11)
        self.mu_head = nn.Conv2d(32, out_channels, kernel_size=1)
        self.log_var_head = nn.Conv2d(32, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Decode to temperature + uncertainty.

        Args:
            x: [B, 128, H', W'] latent features.

        Returns:
            mu: [B, out_channels, H, W] predicted temperature.
            log_var: [B, out_channels, H, W] raw log-variance.
        """
        features = self.decoder(x)
        mu = self.mu_head(features)
        log_var = self.log_var_head(features)
        return mu, log_var


class OceanEmbedNet(nn.Module):
    """Complete OceanEmbed reconstruction network (spec v2.1 §7).

    End-to-end architecture:
      Surface observations [B, T=7, C=7, H, W]
        → Coordinate/seasonal context
        → CNN spatial encoder → [B, T=7, 128, H', W']
        → ConvLSTM → [B, 128, H', W']
        → Depth decoder → [B, 15, H, W]
        → μ + log_variance

    Configuration:
      - Coordinate encoding is configurable (spec v2.1 §7)
      - ConvLSTM hidden channels and layers are configurable (spec v2.1 §9)
      - Grid dimensions are derived from input, never hardcoded (spec v2.1 §2.1)
    """

    def __init__(
        self,
        in_channels: int = 7,
        out_channels: int = 15,
        use_seasonal: bool = True,
        use_spatial: bool = True,
        convlstm_hidden: int = 128,
        convlstm_layers: int = 1,
    ) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels

        # Coordinate encoder
        self.coord_encoder = CoordinateEncoder(
            use_seasonal=use_seasonal, use_spatial=use_spatial
        )
        coord_n_channels = self.coord_encoder.n_channels

        # Input projection: always map to in_channels regardless of coord presence
        # When coords present: [in_channels + coord_n] -> in_channels via 1x1 conv
        # When no coords: identity
        if coord_n_channels > 0:
            self.input_proj = nn.Conv2d(
                in_channels + coord_n_channels, in_channels, kernel_size=1
            )
        else:
            self.input_proj = nn.Identity()

        # CNN spatial encoder — always takes in_channels
        self.encoder = CNNEncoder(in_channels=in_channels)

        # ConvLSTM temporal encoder
        self.temporal = ConvLSTMBlock(
            in_channels=128,
            hidden_channels=convlstm_hidden,
            num_layers=convlstm_layers,
        )

        # Depth decoder
        self.decoder = DepthDecoder(out_channels=out_channels)

    def forward(
        self,
        x: torch.Tensor,
        day_of_year: torch.Tensor | None = None,
        lat: torch.Tensor | None = None,
        lon: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Forward pass.

        Args:
            x: [B, T, C_in, H, W] surface observations.
            day_of_year: [B] integer day-of-year (1-365).
            lat: [H, W] latitude grid.
            lon: [H, W] longitude grid.

        Returns:
            mu: [B, out_channels, H, W] predicted temperature.
            log_var: [B, out_channels, H, W] raw log-variance.
        """
        B, T, C, H, W = x.shape

        # Coordinate encoding
        coord = self.coord_encoder(
            day_of_year=day_of_year,
            lat=lat,
            lon=lon,
            batch_size=B,
            height=H,
            width=W,
        )

        # Process each timestep through CNN encoder
        encoded_steps = []
        for t in range(T):
            inp = x[:, t]  # [B, C, H, W]
            if coord is not None:
                inp = self.input_proj(torch.cat([inp, coord], dim=1))
            # When no coords, input_proj is Identity or not needed — pass through
            encoded_steps.append(self.encoder(inp))

        # Stack into temporal sequence [B, T, 128, H', W']
        temporal_input = torch.stack(encoded_steps, dim=1)

        # ConvLSTM temporal processing
        temporal_out = self.temporal(temporal_input)  # [B, 128, H', W']

        # Decode to temperature + uncertainty
        mu, log_var = self.decoder(temporal_out)

        return mu, log_var
