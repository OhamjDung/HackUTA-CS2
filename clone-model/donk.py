"""A donk-only movement model: CS-NET v4 specialised to donk, kept close to the human base model.

Design (clone-model/ROUND3_DESIGN.md, section 8). Two ideas from published work:

  1. AlphaStar (Vinyals et al., 2019) learned from human replays, then kept later training close to that
     human policy with a KL-divergence penalty, so the agent stayed human. Here: start from CS-NET
     (learned from many pros), specialise it to donk, and penalise how far its move probabilities drift
     from CS-NET's (KL to base). With about 47 training rounds of donk, this anchor is what stops the
     model from memorising them.
  2. Low-rank adapters (LoRA): about 1.2 million trainable numbers inside the decoder, the part that
     writes the moves. After training they are folded into an ordinary CS-NET checkpoint, so CS-NET's
     own prediction engine generates donk play with no new generation code.

Imagination is used at evaluation and for later self-training: the engine samples several futures per
moment, and futures that break human limits are rejected (section 4 of the design, layer L5).

Training data are donk's windows only, from the training rounds of his non-held-back matches. Windows
whose real future breaks a human per-step limit (H8 to H10) are dropped: they are spectator or death
artefacts, not moves to learn.

    python donk.py train    --csnet <csnet> --cache <cache> --checkpoint <base.pt> --out <run> --device cuda
    python donk.py evaluate --csnet <csnet> --cache <cache> --checkpoint <base.pt> --out <run> --device cuda

Rounds: donk's development rounds are split in two by round number. Even rounds (dev-A) choose the
checkpoint by teacher-forced loss. Odd rounds (dev-B) are used once, by "evaluate", for the result.
Matches 2393242 and 2393024 are never used: they were spent as final tests in round 2.

Pass rule for "evaluate", fixed before any run (do not change after seeing dev-B results):
  P1  free-running paths: the donk model's mean path error is lower than the base model's, and the
      95% paired bootstrap interval of the difference lies entirely below zero;
  P2  behaviour: the donk model is closer than the base to real donk on at least 2 of 3 measures
      (distribution of distance per step, distribution of view turn per step, backwards share);
  P3  human limits: the donk model's share of steps that break H8 to H10 is not higher than the base's.
  Pass = P1 and P2 and P3.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import torch.nn.utils.parametrize as P
from torch import nn

from common import CSNET_REVISION, HOLDOUTS, configure, sha256, write_json

PLAYER = "donk"
# Human per-step limits at 4 steps per second (ROUND3_DESIGN.md, H8 to H10).
MAX_STEP_YAW = 165.0
MAX_STEP_PITCH = 45.0
MAX_STEP_MOVE = 68.0
MOVING_STEP = 15.0                  # 60 units/s for 0.25 s: the threshold for "moving"
SAMPLES, TEMPERATURE, TOP_P = 8, 1.0, 0.9


# ------------------------------------------------------------------------------------------- LoRA
class LoRA(nn.Module):
    """W + B @ A * (alpha / r). B starts at zero, so the model starts exactly at the base."""

    def __init__(self, out_features: int, in_features: int, r: int = 16, alpha: int = 16):
        super().__init__()
        self.A = nn.Parameter(torch.empty(r, in_features))
        self.B = nn.Parameter(torch.zeros(out_features, r))
        nn.init.kaiming_uniform_(self.A, a=math.sqrt(5))
        self.scale = alpha / r
        self.enabled = True

    def forward(self, weight: torch.Tensor) -> torch.Tensor:
        if not self.enabled:
            return weight
        return weight + (self.B @ self.A).to(weight.dtype) * self.scale


def add_lora(decoder: nn.Module, r: int = 16) -> list[LoRA]:
    """Attach LoRA to every attention and feed-forward weight of every decoder block."""
    added = []
    for block in decoder.decoder_blocks:
        targets = [(block.self_attn, "in_proj_weight"), (block.self_attn.out_proj, "weight")]
        targets += [(m, "weight") for m in block.ffn if isinstance(m, nn.Linear)]
        for module, name in targets:
            out_f, in_f = getattr(module, name).shape
            lora = LoRA(out_f, in_f, r).to(getattr(module, name).device)
            P.register_parametrization(module, name, lora)
            added.append(lora)
    return added


def set_lora(loras: list[LoRA], enabled: bool) -> None:
    for lora in loras:
        lora.enabled = enabled


def merge_lora(decoder: nn.Module) -> None:
    """Fold the adapters into the weights, leaving an ordinary CS-NET decoder."""
    for module in list(decoder.modules()):
        if P.is_parametrized(module):
            for name in list(module.parametrizations.keys()):
                for lora in module.parametrizations[name]:
                    lora.enabled = True
                P.remove_parametrizations(module, name, leave_parametrized=True)


# ------------------------------------------------------------------------------------------ model
def encode(base, batch, b, p):
    """Frozen inputs for the decoder, for window b and player p (as in v2.py)."""
    n, d = base.cfg.n_ticks, base.cfg.d_model
    N = len(b)
    with torch.no_grad():
        start = base.get_player_embeddings(batch)[b, -1, p]
        window = slice(n - 1, 2 * n - 1)
        depth = batch["player_depth_labels"][b, :, p][:, window]
        depth = base.embedder.depth_encoder(depth.reshape(N * n, 64, 5)).reshape(N, n, d)
        pos = batch["player_pos_labels"][b, :, p][:, window]
        map_emb = base.embedder.map_emb(batch["map_idx"][b, 0].long())[:, None].expand(N, n, d)
        xyz = base.embedder.mlp1(torch.cat([pos, map_emb], dim=-1))
        angle = base.embedder.mlp_angle(batch["player_angle_labels"][b, :, p][:, window])
        tokens = base.tokenizer.encode_sequence(batch["label_camera"][b, :, p][:, window], n)
    return start, depth, xyz, angle, tokens


def losses(base, loras, encoded):
    """Next-move loss of the donk model, and its KL divergence from the base model."""
    start, depth, xyz, angle, tokens = encoded
    set_lora(loras, True)
    logits, targets = base.decoder(start, tokens, depth_ctx=depth, xyz_ctx=xyz, angle_ctx=angle)
    with torch.no_grad():
        set_lora(loras, False)
        base_logits, _ = base.decoder(start, tokens, depth_ctx=depth, xyz_ctx=xyz, angle_ctx=angle)
        set_lora(loras, True)
    pad = base.tokenizer.PAD
    mask = (targets != pad)
    nll = F.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), targets.reshape(-1), ignore_index=pad)
    logp = F.log_softmax(logits.float(), -1)[mask]
    logq = F.log_softmax(base_logits.float(), -1)[mask]
    kl = (logp.exp() * (logp - logq)).sum(-1).mean() if mask.any() else logits.sum() * 0
    return nll, kl


def step_violations(labels: torch.Tensor) -> torch.Tensor:
    """Per window: True if the real future breaks a per-step human limit (labels: [N, steps, 10])."""
    alive = labels[..., 7] > 0.5
    move = torch.hypot(labels[..., 0], labels[..., 1])
    pitch = torch.rad2deg(torch.atan2(labels[..., 4], labels[..., 3])).abs()
    yaw = torch.rad2deg(torch.atan2(labels[..., 6], labels[..., 5])).abs()
    bad = (move > MAX_STEP_MOVE) | (pitch > MAX_STEP_PITCH) | (yaw > MAX_STEP_YAW)
    return (bad & alive).any(-1)


# ------------------------------------------------------------------------------------------- data
def donk_indices(dataset, half: str | None = None) -> list[int]:
    """Indices of donk's windows; half "A" (even round numbers) or "B" (odd) for development rounds."""
    out = []
    for i in dataset.by_player[PLAYER]:
        entry = dataset.index[i][0]
        if entry["match_id"] in HOLDOUTS:
            raise ValueError("A held-back match reached donk's data")
        if half is None or (entry["round_id"] % 2 == 0) == (half == "A"):
            out.append(i)
    return out


def to_device(batch, device):
    return {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}


@torch.no_grad()
def dev_loss(base, loras, dataset, indices, device, batch_size=8):
    from training_data.torch_dataset import pretrain_collate_fn
    total, count, base_total = 0.0, 0, 0.0
    for s in range(0, len(indices), batch_size):
        batch = to_device(pretrain_collate_fn([dataset[i] for i in indices[s:s + batch_size]]), device)
        b = torch.arange(len(batch["target_index"]), device=device)
        with torch.autocast(device_type=device, dtype=torch.bfloat16, enabled=device == "cuda"):
            enc = encode(base, batch, b, batch["target_index"].long())
            nll, _ = losses(base, loras, enc)
            set_lora(loras, False)
            base_logits, targets = base.decoder(enc[0], enc[4], depth_ctx=enc[1], xyz_ctx=enc[2], angle_ctx=enc[3])
            set_lora(loras, True)
        pad = base.tokenizer.PAD
        base_nll = F.cross_entropy(base_logits.float().reshape(-1, base_logits.shape[-1]), targets.reshape(-1), ignore_index=pad)
        total += float(nll) * len(b); base_total += float(base_nll) * len(b); count += len(b)
    return {"donk_model": total / count, "base": base_total / count, "windows": count}


def train(args):
    from data import Windows
    from model import load_backbone
    from training_data.torch_dataset import pretrain_collate_fn
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    training = Windows(args.cache, "train", shuffle=True)
    development = Windows(args.cache, "dev")
    train_idx, dev_a = donk_indices(training), donk_indices(development, "A")
    base = load_backbone(args.csnet, args.checkpoint, args.device)
    base.requires_grad_(False)
    loras = add_lora(base.decoder, args.rank)
    params = [p for lora in loras for p in lora.parameters()]
    for p in params:
        p.requires_grad_(True)
    optimizer = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"TRAINING_STARTED donk_train_windows={len(train_idx)} dev_A_windows={len(dev_a)} "
          f"trainable_parameters={sum(p.numel() for p in params)} kl_weight={args.kl}", flush=True)
    first = dev_loss(base, loras, development, dev_a, args.device)
    print("DEV", json.dumps(dict(step=0, **first)), flush=True)
    best, best_step, stale, history, dropped = first["donk_model"], 0, 0, [], 0
    torch.save({"lora": [l.state_dict() for l in loras], "step": 0}, args.out / "best_lora.pt")
    started = time.time()
    for step in range(1, args.steps + 1):
        chosen = random.sample(train_idx, min(args.batch_size, len(train_idx)))
        batch = to_device(pretrain_collate_fn([training[i] for i in chosen]), args.device)
        b = torch.arange(len(chosen), device=args.device)
        p = batch["target_index"].long()
        labels = batch["label_camera"][b, :, p][:, base.cfg.n_ticks - 1:2 * base.cfg.n_ticks - 1]
        keep = ~step_violations(labels)
        dropped += int((~keep).sum())
        if not keep.any():
            continue
        b, p = b[keep], p[keep]
        base.decoder.train()
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=args.device, dtype=torch.bfloat16, enabled=args.device == "cuda"):
            nll, kl = losses(base, loras, encode(base, batch, b, p))
            objective = nll + args.kl * kl
        if not torch.isfinite(objective):
            raise RuntimeError("Nonfinite loss; stopping before saving a corrupt model")
        objective.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        optimizer.step()
        base.decoder.eval()
        if step == 1 or step % 20 == 0:
            record = dict(step=step, nll=float(nll), kl=float(kl), dropped_windows=dropped,
                          elapsed_seconds=round(time.time() - started, 1))
            history.append(record)
            print("TRAIN", json.dumps(record), flush=True)
        if step % args.check_every == 0 or step == args.steps:
            dev = dev_loss(base, loras, development, dev_a, args.device)
            if dev["donk_model"] < best - 1e-5:
                best, best_step, stale = dev["donk_model"], step, 0
                torch.save({"lora": [l.state_dict() for l in loras], "step": step}, args.out / "best_lora.pt")
            else:
                stale += 1
            print("DEV", json.dumps(dict(step=step, best_step=best_step, **dev)), flush=True)
            write_json(args.out / "training.json", dict(history=history, best_step=best_step, latest_dev=dev,
                       first_dev=first, settings=vars(args) | {"csnet": str(args.csnet), "cache": str(args.cache),
                       "checkpoint": str(args.checkpoint), "out": str(args.out)}, holdout_used=False))
            if stale >= args.patience:
                print("EARLY_STOP", flush=True)
                break
    saved = torch.load(args.out / "best_lora.pt", map_location="cpu")
    for lora, state in zip(loras, saved["lora"]):
        lora.load_state_dict(state)
    merge_lora(base.decoder)
    torch.save({"model": {k: v.detach().cpu() for k, v in base.state_dict().items()}, "global_step": saved["step"],
                "donk_finetune": dict(base_checkpoint_sha256=base.checkpoint_sha256, csnet_revision=CSNET_REVISION,
                                      manifest_sha256=sha256(args.cache / "manifest.json"), kl_weight=args.kl,
                                      rank=args.rank, selected_step=saved["step"])}, args.out / "donk_model.pt")
    write_json(args.out / "progress.json", dict(state="trained_needs_evaluation", best_step=saved["step"]))
    print(f"TRAINING_COMPLETE best_step={saved['step']} saved donk_model.pt; dev-B evaluation not run yet", flush=True)


# ------------------------------------------------------------------------------------- evaluation
def wrap(a):
    return (np.asarray(a, dtype=float) + 180.0) % 360.0 - 180.0


def path_steps(start, points, yaws, pitches, start_yaw=None):
    """Per 0.25 s step: distance moved, view turn, pitch change, and whether it walks backwards."""
    pts = np.vstack([np.asarray(start, float)[None, :3], np.asarray(points, float).reshape(-1, 3)])
    d = np.diff(pts[:, :2], axis=0)
    move = np.hypot(d[:, 0], d[:, 1])
    yaws = np.asarray(yaws, float)
    full_yaw = np.concatenate([[yaws[0] if start_yaw is None else start_yaw], yaws])
    turn = np.abs(wrap(np.diff(full_yaw)))
    pitches = np.asarray(pitches, float)
    pitch = np.abs(np.diff(np.concatenate([[pitches[0]], pitches]))) if len(pitches) else np.zeros(0)
    direction = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
    back = (move >= MOVING_STEP) & (np.abs(wrap(direction - yaws[:len(move)])) > 135)
    return move, turn[:len(move)], pitch[:len(move)], back


def ade(pred, real, start):
    real = np.asarray(real, float).reshape(-1, 3)
    pred = np.asarray(pred if len(pred) else [start], float).reshape(-1, 3)
    pred = pred[np.minimum(np.arange(len(real)), len(pred) - 1)]
    return float(np.linalg.norm(pred - real, axis=1).mean())


def w1(a, b):
    """1-D Wasserstein distance between two samples (mean absolute difference of quantiles)."""
    a, b = np.sort(np.asarray(a, float)), np.sort(np.asarray(b, float))
    if not len(a) or not len(b):
        return float("nan")
    q = np.linspace(0, 1, 201)
    return float(np.mean(np.abs(np.quantile(a, q) - np.quantile(b, q))))


def paired_ci(diff, n_boot=5000, seed=0):
    rng = np.random.default_rng(seed)
    diff = np.asarray(diff, float)
    boots = [rng.choice(diff, len(diff)).mean() for _ in range(n_boot)]
    return float(diff.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def violation_share(move, turn, pitch):
    return float(np.mean((move > MAX_STEP_MOVE) | (turn > MAX_STEP_YAW) | (pitch > MAX_STEP_PITCH))) if len(move) else 0.0


def judge(per_model: dict, real: dict) -> dict:
    """Apply the fixed pass rule. per_model[name] holds ade lists and pooled step arrays."""
    diff = np.asarray(per_model["donk"]["mean_ade"]) - np.asarray(per_model["base"]["mean_ade"])
    mean, low, high = paired_ci(diff)
    behaviour = {}
    for name in ("donk", "base"):
        m = per_model[name]
        behaviour[name] = {
            "move_w1": w1(m["move"], real["move"]), "turn_w1": w1(m["turn"], real["turn"]),
            "backwards_gap": abs(float(np.mean(m["back"])) - float(np.mean(real["back"]))),
            "violation_share": violation_share(np.asarray(m["move"]), np.asarray(m["turn"]), np.asarray(m["pitch"])),
            "backwards_share": float(np.mean(m["back"])),
        }
    closer = sum(behaviour["donk"][k] < behaviour["base"][k] for k in ("move_w1", "turn_w1", "backwards_gap"))
    p1 = high < 0
    p2 = closer >= 2
    p3 = behaviour["donk"]["violation_share"] <= behaviour["base"]["violation_share"]
    return {"P1_mean_ade": {"donk_minus_base": mean, "ci95": [low, high], "pass": bool(p1)},
            "P2_behaviour": {"closer_on": int(closer), "of": 3, "pass": bool(p2), "detail": behaviour,
                             "real_donk_backwards_share": float(np.mean(real["back"]))},
            "P3_limits": {"pass": bool(p3)}, "pass": bool(p1 and p2 and p3)}


def evaluate(args):
    from data import Windows, load_round
    from prediction_engine import PredictionEngine
    development = Windows(args.cache, "dev")
    entries = {}
    for i in donk_indices(development, "B"):
        entry, s = development.index[i]
        entries.setdefault(entry["file"], (entry, []))[1].append(s + 15)
    config = str(args.csnet / "config/pretrain-a100-pro.yaml")
    engines = {"base": PredictionEngine(config, str(args.checkpoint), device=args.device,
                                        maps_dir=str(args.csnet / "maps/optimized_obj_files")),
               "donk": PredictionEngine(config, str(args.out / "donk_model.pt"), device=args.device,
                                        maps_dir=str(args.csnet / "maps/optimized_obj_files"))}
    per_model = {k: {"mean_ade": [], "min_ade": [], "move": [], "turn": [], "pitch": [], "back": []} for k in engines}
    real = {"move": [], "turn": [], "pitch": [], "back": []}
    windows = 0
    torch.manual_seed(7); np.random.seed(7); random.seed(7)
    for file, (entry, ticks) in sorted(entries.items()):
        sample = load_round(str(args.cache / file))
        for tick in ticks:
            results = {}
            for name, engine in engines.items():
                results[name] = engine.predict_at_tick_player_sampled(sample, tick, player_idx=entry["target_index"],
                    num_samples=SAMPLES, temperature=TEMPERATURE, top_p=TOP_P, metric=None)
            gt = results["base"].get("gt")
            if not gt or not gt.get("gt_points"):
                continue
            windows += 1
            start = results["base"]["start_pos"]
            mv, tn, pt, bk = path_steps(start, gt["gt_points"], gt["gt_yaw"], gt.get("gt_pitch", []))
            for k, v in zip(("move", "turn", "pitch", "back"), (mv, tn, pt, bk)):
                real[k].extend(v.tolist())
            for name, res in results.items():
                ades = [ade(smp["pred_points"], gt["gt_points"], start) for smp in res["samples"]]
                per_model[name]["mean_ade"].append(float(np.mean(ades)))
                per_model[name]["min_ade"].append(float(np.min(ades)))
                for smp in res["samples"]:
                    if not smp["pred_points"]:
                        continue
                    mv, tn, pt, bk = path_steps(start, smp["pred_points"], smp["pred_yaw"], smp.get("pred_pitch", []))
                    for k, v in zip(("move", "turn", "pitch", "back"), (mv, tn, pt, bk)):
                        per_model[name][k].extend(v.tolist())
        print(f"EVALUATED {file} windows_so_far={windows}", flush=True)
    result = judge(per_model, real)
    result.update(windows=windows, rounds=len(entries), samples_per_window=SAMPLES, temperature=TEMPERATURE,
                  top_p=TOP_P, split="dev-B (odd development rounds of donk)",
                  min_ade={k: float(np.mean(v["min_ade"])) for k, v in per_model.items()},
                  mean_ade={k: float(np.mean(v["mean_ade"])) for k, v in per_model.items()},
                  interpretation="Free-running 4-second futures sampled by CS-NET's own engine. Movement and view "
                                 "only; not combat, not in CS2, not a people panel.")
    write_json(args.out / "evaluation.json", result)
    write_json(args.out / "progress.json", dict(state="evaluated_pass" if result["pass"] else "evaluated_fail",
                                                 deployed=False))
    print("EVALUATION_COMPLETE", json.dumps({k: v for k, v in result.items() if k != "P2_behaviour"}), flush=True)
    print("BEHAVIOUR", json.dumps(result["P2_behaviour"]), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["train", "evaluate"])
    ap.add_argument("--csnet", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--kl", type=float, default=0.1, help="weight of the KL penalty to the base model")
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--check-every", type=int, default=50)
    ap.add_argument("--patience", type=int, default=6)
    args = ap.parse_args()
    configure(args.csnet)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested a GPU, but no CUDA device is connected")
    torch.set_num_threads(4)
    (train if args.command == "train" else evaluate)(args)


if __name__ == "__main__":
    main()
