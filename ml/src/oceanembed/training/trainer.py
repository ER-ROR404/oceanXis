"""Training loop for OceanEmbed reconstruction model.

Following spec v2.1 §14, §16, §19:
- NLL loss primary (spec §14)
- Temporal locked split (spec §16)
- Depth-wise evaluation metrics (spec §19)
- Early stopping with configurable patience
- Checkpointing for best model
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from oceanembed.losses.nll_loss import GaussianNLLLoss, masked_nll_loss


@dataclass
class EarlyStopping:
    """Early stopping callback (stops when loss stops improving)."""

    patience: int = 10
    min_delta: float = 1e-4
    best_loss: float = field(default=float("inf"), init=False)
    counter: int = field(default=0, init=False)

    def step(self, loss: float) -> bool:
        """Check if training should stop.

        Args:
            loss: Current validation loss.

        Returns:
            True if training should stop.
        """
        if loss < self.best_loss - self.min_delta:
            self.best_loss = loss
            self.counter = 0
            return False
        self.counter += 1
        return self.counter >= self.patience


class Trainer:
    """Training loop for OceanEmbedNet.

    Supports:
    - NLL loss with aleatoric uncertainty
    - Early stopping
    - Model checkpointing
    - Depth-wise evaluation
    """

    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        lr: float = 1e-3,
        checkpoint_dir: Path | str | None = None,
        early_stopping_patience: int = 15,
    ) -> None:
        """Initialize trainer.

        Args:
            model: OceanEmbedNet model.
            train_loader: Training data loader.
            val_loader: Validation data loader.
            lr: Learning rate.
            checkpoint_dir: Directory for saving checkpoints.
            early_stopping_patience: Patience for early stopping.
        """
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = next(model.parameters()).device if list(model.parameters()) else torch.device("cpu")
        self.model.to(self.device)

        self.optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        self.loss_fn = GaussianNLLLoss()
        self.masked_loss_fn = masked_nll_loss
        self.early_stopping = EarlyStopping(patience=early_stopping_patience)
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        self.best_model_state: dict | None = None
        self.history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}

    def train_epoch(self) -> float:
        """Run one training epoch.

        Returns:
            Average training loss.
        """
        self.model.train()
        total_loss = 0.0
        n_batches = 0

        for x_batch, y_batch, mask_batch in self.train_loader:
            x_batch = x_batch.to(self.device)
            y_batch = y_batch.to(self.device)
            mask_batch = mask_batch.to(self.device)

            self.optimizer.zero_grad()
            mu, log_var = self.model(x_batch)
            loss = self.masked_loss_fn(mu, log_var, y_batch, mask_batch)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        return total_loss / max(n_batches, 1)

    @torch.no_grad()
    def validate(self) -> tuple[float, dict[str, float]]:
        """Run validation.

        Returns:
            (val_loss, metrics_dict) where metrics_dict has depth-wise RMSE.
        """
        self.model.eval()
        total_loss = 0.0
        n_batches = 0
        all_mu = []
        all_y = []
        all_masks = []

        for x_batch, y_batch, mask_batch in self.val_loader:
            x_batch = x_batch.to(self.device)
            y_batch = y_batch.to(self.device)
            mask_batch = mask_batch.to(self.device)

            mu, log_var = self.model(x_batch)
            loss = self.masked_loss_fn(mu, log_var, y_batch, mask_batch)

            total_loss += loss.item()
            n_batches += 1
            all_mu.append(mu.cpu())
            all_y.append(y_batch.cpu())
            all_masks.append(mask_batch.cpu())

        val_loss = total_loss / max(n_batches, 1)

        # Compute depth-wise metrics over valid (masked) cells only
        metrics = {}
        if all_mu:
            mu_cat = torch.cat(all_mu, dim=0)     # [N, 15, H, W]
            y_cat = torch.cat(all_y, dim=0)       # [N, 15, H, W]
            mask_cat = torch.cat(all_masks, dim=0)  # [N, H, W]

            diff = (mu_cat - y_cat) ** 2  # [N, 15, H, W]
            # NaN safety: y may be NaN outside the mask; 0 * NaN = NaN,
            # so zero out non-finite differences before masking.
            diff = torch.nan_to_num(diff, nan=0.0)
            # Convert mask to [N, 1, H, W] for broadcasting over channels
            mask_expanded = mask_cat.unsqueeze(1)
            n_valid = mask_expanded.sum().clamp(min=1.0)

            # Overall RMSE over valid cells
            rmse = torch.sqrt((diff * mask_expanded).sum() / n_valid).item()
            metrics["rmse"] = rmse

            # Bias over valid cells
            signed_diff = torch.nan_to_num(mu_cat - y_cat, nan=0.0)
            bias = (signed_diff * mask_expanded).sum() / n_valid
            metrics["bias"] = bias.item()

            # Depth-wise RMSE over valid cells
            for d in range(mu_cat.shape[1]):
                depth_diff = diff[:, d]  # [N, H, W]
                depth_rmse = torch.sqrt(depth_diff[mask_cat.bool()].mean()).item()
                metrics[f"rmse_depth_{d}"] = depth_rmse

        return val_loss, metrics

    def save_checkpoint(self, epoch: int, val_loss: float, is_best: bool = False) -> None:
        """Save model checkpoint.

        Args:
            epoch: Current epoch number.
            val_loss: Current validation loss.
            is_best: Whether this is the best model so far.

        The checkpoint carries everything needed to resume a Colab run that
        was interrupted (VM disconnect kills the kernel): model + optimizer
        state, early-stopping state, best-model snapshot, and loss history.
        """
        if self.checkpoint_dir is None:
            return

        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "epoch": epoch,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "val_loss": val_loss,
            "history": {k: list(v) for k, v in self.history.items()},
            "early_stopping": {
                "best_loss": self.early_stopping.best_loss,
                "counter": self.early_stopping.counter,
            },
            "best_model_state": self.best_model_state,
        }

        # Save latest
        torch.save(checkpoint, self.checkpoint_dir / "latest.pt")

        # Save best
        if is_best:
            torch.save(checkpoint, self.checkpoint_dir / "best.pt")
            self.best_model_state = copy.deepcopy(self.model.state_dict())

    def load_checkpoint(self, path: Path | str) -> tuple[int, dict[str, list[float]]]:
        """Restore model, optimizer, and early-stopping state from a checkpoint.

        Args:
            path: Path to a checkpoint written by save_checkpoint.

        Returns:
            (start_epoch, history): start_epoch is the next epoch to run
            (checkpoint epoch + 1); history is the persisted loss history.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Resume checkpoint not found: {path}")
        ckpt = torch.load(path, map_location=self.device, weights_only=True)

        self.model.load_state_dict(ckpt["model_state_dict"])
        self.optimizer.load_state_dict(ckpt["optimizer_state_dict"])

        es = ckpt.get("early_stopping") or {}
        self.early_stopping.best_loss = float(es.get("best_loss", self.early_stopping.best_loss))
        self.early_stopping.counter = int(es.get("counter", 0))

        saved_best = ckpt.get("best_model_state")
        if saved_best is not None:
            self.best_model_state = {k: v.clone() for k, v in saved_best.items()}

        history = ckpt.get("history")
        if history is None:
            history = {"train_loss": [], "val_loss": []}
        else:
            history = {k: list(v) for k, v in history.items()}
        self.history = history

        start_epoch = int(ckpt.get("epoch", -1)) + 1
        return start_epoch, history

    def train(self, epochs: int = 100, resume_from: Path | str | None = None,
              verbose: bool = False) -> dict[str, list[float]]:
        """Run training loop.

        Args:
            epochs: Maximum total number of epochs (starting at 0, or at the
                resume point when ``resume_from`` is given).
            resume_from: Optional checkpoint path. Restores model/optimizer/
                early-stopping state and continues the persisted loss history.
            verbose: Print a per-epoch progress line (live visibility during
                long Colab runs). Library default is quiet.

        Returns:
            History dict with train_loss, val_loss per epoch (cumulative).
        """
        if resume_from is not None:
            start_epoch, history = self.load_checkpoint(resume_from)
        else:
            start_epoch = 0
            history = {"train_loss": [], "val_loss": []}
        self.history = history

        for epoch in range(start_epoch, epochs):
            # Train
            train_loss = self.train_epoch()
            self.history["train_loss"].append(train_loss)

            # Validate
            val_loss, metrics = self.validate()
            self.history["val_loss"].append(val_loss)

            # Log
            status = ""
            if self.early_stopping.best_loss < float("inf"):
                improvement = self.early_stopping.best_loss - val_loss
                status = f" (Δ={improvement:+.4f})"

            # Checkpoint
            is_best = val_loss < self.early_stopping.best_loss
            self.save_checkpoint(epoch, val_loss, is_best)

            if verbose:
                print(
                    f"epoch {epoch + 1}/{epochs}  train_loss={train_loss:.4f}  "
                    f"val_loss={val_loss:.4f}{status}",
                    flush=True,
                )

            # Early stopping
            should_stop = self.early_stopping.step(val_loss)
            if should_stop:
                # Restore best model
                if self.best_model_state is not None:
                    self.model.load_state_dict(self.best_model_state)
                break

        return self.history
