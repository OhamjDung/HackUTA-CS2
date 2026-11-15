"""Frozen CS-NET encoder/decoder with a player-conditioned decoder input."""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import torch
import yaml
from torch import nn

from identity import PlayerAdapter
from common import sha256


def load_backbone(csnet: Path, checkpoint: Path, device: str):
    from pretrain_model import CS2PretrainModel, PretrainConfig
    config = yaml.safe_load((csnet / "config/pretrain-a100-pro.yaml").read_text(encoding="utf-8"))
    config = {k: v for k, v in config.items() if k in {f.name for f in fields(PretrainConfig)}}
    model = CS2PretrainModel(PretrainConfig(**config))
    saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
    state = {k.replace("_orig_mod.", ""): v for k, v in saved["model"].items()}
    model.load_state_dict(state, strict=True)
    if any(not torch.isfinite(v).all() for v in model.state_dict().values()):
        raise ValueError("The base checkpoint has nonfinite weights")
    model.checkpoint_sha256 = sha256(checkpoint)
    return model.to(device).eval().requires_grad_(False)


class LearnedClone(nn.Module):
    def __init__(self, backbone, registry):
        super().__init__()
        self.backbone = backbone.eval().requires_grad_(False)
        self.adapter = PlayerAdapter(registry, backbone.cfg.d_model)

    def forward(self, batch, identity_override: int | None = None):
        base = self.backbone
        base.eval()
        B, T, P = batch["player_pos"].shape[:3]
        n, d = base.cfg.n_ticks, base.cfg.d_model
        if T != n or n != 16 or P != 10:
            raise ValueError("Expected the pretrained 16-tick, 10-player window")
        b = torch.arange(B, device=batch["player_pos"].device)
        p = batch["target_index"].long()
        with torch.no_grad():
            conditions = base.get_player_embeddings(batch)[b, -1, p]
            depth = batch["player_depth_labels"][b, :, p][:, n-1:n-1+n]
            depth_ctx = base.embedder.depth_encoder(depth.reshape(B*n, 64, 5)).reshape(B, n, d)
            pos = batch["player_pos_labels"][b, :, p][:, n-1:n-1+n]
            map_emb = base.embedder.map_emb(batch["map_idx"][:, 0].long())[:, None].expand(B, n, d)
            xyz_ctx = base.embedder.mlp1(torch.cat([pos, map_emb], dim=-1))
            angle = batch["player_angle_labels"][b, :, p][:, n-1:n-1+n]
            angle_ctx = base.embedder.mlp_angle(angle)
            labels = batch["label_camera"][b, :, p][:, n-1:n-1+n]
            tokens = base.tokenizer.encode_sequence(labels, n)
        ids = batch["identity"].long()
        if identity_override is not None:
            ids = torch.full_like(ids, identity_override)
        adapted = self.adapter(conditions, ids)
        logits, targets = base.decoder(adapted, tokens, depth_ctx=depth_ctx, xyz_ctx=xyz_ctx, angle_ctx=angle_ctx)
        loss, metrics = base._compute_loss(logits, targets)
        regularizer = (adapted - conditions).float().square().mean()
        return loss, regularizer, metrics
