"""Dense identities and zero-initialized FiLM, adapted from CS2 Clone Lab (MIT).

See THIRD_PARTY.md and third_party/CLONE_LAB_LICENSE.
"""
from __future__ import annotations

import torch
from torch import nn


class FiLM(nn.Module):
    def __init__(self, d: int, cond_dim: int):
        super().__init__()
        self.to_scale_shift = nn.Linear(cond_dim, 2 * d)
        nn.init.zeros_(self.to_scale_shift.weight)
        nn.init.zeros_(self.to_scale_shift.bias)

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        gamma, beta = self.to_scale_shift(cond).chunk(2, dim=-1)
        while gamma.dim() < x.dim():
            gamma, beta = gamma.unsqueeze(-2), beta.unsqueeze(-2)
        return x * (1 + gamma) + beta


class PlayerAdapter(nn.Module):
    def __init__(self, registry: dict[str, int], d_model: int, d_identity: int = 64):
        super().__init__()
        if sorted(registry.values()) != list(range(1, len(registry) + 1)):
            raise ValueError("Identity indices must be dense, starting at 1; 0 is unknown")
        self.registry = dict(registry)
        self.d_model, self.d_identity = d_model, d_identity
        self.embedding = nn.Embedding(len(registry) + 1, d_identity, padding_idx=0)
        self.film = FiLM(d_model, d_identity)

    def forward(self, x: torch.Tensor, ids: torch.Tensor) -> torch.Tensor:
        """Modulate paired feature vectors; unknown identity remains exact base after training."""
        if x.shape[:-1] != ids.shape:
            raise ValueError("Every feature vector must have exactly one identity index")
        modulated = self.film(x, self.embedding(ids))
        return torch.where((ids != 0).unsqueeze(-1), modulated, x)

    def temporal_hook(self, ids: torch.Tensor):
        """Apply the same identity to each time step in upstream inference."""
        def hook(module, args, output):
            expanded = ids[:, None, :].expand(output.shape[:-1])
            return self(output, expanded)
        return hook
