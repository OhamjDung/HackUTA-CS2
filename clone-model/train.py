"""Stage A: train only identities and FiLM; select checkpoints using training-game dev rounds."""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch

from common import CSNET_REVISION, REGISTRY, configure, write_json, sha256
from data import Windows
from model import LearnedClone, load_backbone


def to_device(batch, device):
    return {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}


@torch.no_grad()
def dev_loss(model, dataset, device, max_per_player=24):
    from training_data.torch_dataset import pretrain_collate_fn
    model.eval()
    result = {}
    for name, indices in dataset.by_player.items():
        selected = [indices[i] for i in np.linspace(0, len(indices)-1, min(max_per_player, len(indices)), dtype=int)]
        own, base = [], []
        for start in range(0, len(selected), 4):
            batch = to_device(pretrain_collate_fn([dataset[i] for i in selected[start:start+4]]), device)
            with torch.autocast(device_type=device, dtype=torch.bfloat16, enabled=device == "cuda"):
                own.append(float(model(batch)[0]))
                base.append(float(model(batch, identity_override=0)[0]))
        result[name] = {"own_teacher_forced_loss": float(np.mean(own)), "base_teacher_forced_loss": float(np.mean(base)),
            "windows": len(selected)}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csnet", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    args = parser.parse_args()
    configure(args.csnet)
    from training_data.torch_dataset import pretrain_collate_fn
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested a GPU, but no CUDA device is connected")
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    torch.set_num_threads(4)
    if args.device == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
    args.out.mkdir(parents=True, exist_ok=True)
    training = Windows(args.cache, "train", shuffle=True)
    development = Windows(args.cache, "dev")
    model = LearnedClone(load_backbone(args.csnet, args.checkpoint, args.device), REGISTRY).to(args.device)
    if any(p.requires_grad for p in model.backbone.parameters()):
        raise RuntimeError("Backbone must remain frozen")
    optimizer = torch.optim.AdamW(model.adapter.parameters(), lr=args.lr, weight_decay=.01)
    base_dev = dev_loss(model, development, args.device)
    print("BASELINE", json.dumps(base_dev), flush=True)
    best = float(np.mean([v["own_teacher_forced_loss"] for v in base_dev.values()]))
    history, stale, best_step = [], 0, 0
    started = time.time()
    manifest_sha = sha256(args.cache / "manifest.json")

    def save(path, step, metrics):
        state = {k: v.detach().cpu() for k, v in model.adapter.state_dict().items()}
        torch.save(dict(adapter=state, registry=REGISTRY, d_model=model.adapter.d_model,
            d_identity=model.adapter.d_identity, csnet_revision=CSNET_REVISION, step=step,
            metrics=metrics, base_checkpoint_name=args.checkpoint.name,
            base_checkpoint_sha256=model.backbone.checkpoint_sha256,
            manifest_sha256=manifest_sha, seed=42), path)

    save(args.out / "best.pt", 0, base_dev)
    print(f"TRAINING_STARTED device={args.device} train_windows={len(training)} dev_windows={len(development)} "
        f"trainable_parameters={sum(p.numel() for p in model.adapter.parameters())}", flush=True)
    names = sorted(training.by_player)
    for step in range(1, args.steps + 1):
        selected = [int(np.random.choice(training.by_player[names[(step+i) % len(names)]])) for i in range(args.batch_size)]
        batch = to_device(pretrain_collate_fn([training[i] for i in selected]), args.device)
        model.adapter.train()
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=args.device, dtype=torch.bfloat16, enabled=args.device == "cuda"):
            loss, regularizer, _ = model(batch)
            objective = loss + .001 * regularizer
        if not torch.isfinite(objective):
            raise RuntimeError("Nonfinite training loss; stopping before saving a corrupt adapter")
        objective.backward()
        torch.nn.utils.clip_grad_norm_(model.adapter.parameters(), 1.)
        optimizer.step()
        if step == 1 or step % 10 == 0:
            record = dict(step=step, loss=float(loss.detach()), regularizer=float(regularizer.detach()),
                elapsed_seconds=round(time.time()-started, 1))
            history.append(record)
            print("TRAIN", json.dumps(record), flush=True)
            write_json(args.out / "progress.json", dict(state="training", **record))
        if step % 50 == 0 or step == args.steps:
            metrics = dev_loss(model, development, args.device)
            score = float(np.mean([v["own_teacher_forced_loss"] for v in metrics.values()]))
            save(args.out / "last.pt", step, metrics)
            if score < best - .0001:
                best, best_step, stale = score, step, 0
                save(args.out / "best.pt", step, metrics)
            else:
                stale += 1
            print("DEV", json.dumps(dict(step=step, best_step=best_step, players=metrics)), flush=True)
            write_json(args.out / "training.json", dict(baseline=base_dev, history=history,
                best_step=best_step, latest_dev=metrics, holdout_used_for_selection=False))
            if stale >= 4:
                print("EARLY_STOP: development loss has not improved for four checks", flush=True)
                break
    write_json(args.out / "progress.json", dict(state="trained_needs_validation", step=step,
        best_step=best_step, elapsed_seconds=round(time.time()-started, 1)))
    print(f"TRAINING_COMPLETE best_step={best_step}; held-out free-running validation is still required", flush=True)


if __name__ == "__main__":
    main()
