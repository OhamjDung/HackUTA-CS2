"""Second learned-identity experiment. Reuses the frozen CS-NET v4 base and the same cached rounds.

What changed from the first experiment (model.py, train.py), and why
(clone-model/results/diagnosis-2026-11-14.md):

  1. Many identities. Every player seen in at least 2 non-held-back matches gets an identity, and
     every such player in a window is a training target. The first run had 2 identities.
  2. Identity at every step. The identity is added to the three inputs the decoder reads at each
     of the 16 future steps, as well as to the one starting vector. The first run changed only
     the starting vector.
  3. No pull-back penalty. The first run penalised any change from the base.
  4. Identity is hidden at random during training (the model then sees "unknown player"). This
     keeps the no-identity output meaningful, so generation can amplify the difference later
     (guided_logits).
  5. A loss term that rewards telling teammates apart: the real moves must be more likely under
     the true identity than under a random teammate's identity.
  6. A likelihood "who is it?" test instead of path error: over all of a player's windows in a
     match, which teammate identity makes the real moves most likely?

Pass rule, fixed before any run (do not change after seeing held-out results):
  - a player passes when the true identity ranks in the top TOP_K of the teammate identities;
  - the experiment passes when at least PASS_SHARE of the players pass.
With 5 teammates, guessing gives 40% of players in the top 2.

    python v2.py train --csnet <csnet> --cache <cache> --checkpoint <base.pt> --out <run> --device cuda
    python v2.py test  --csnet <csnet> --cache <cache> --checkpoint <base.pt> --out <run> --device cuda

Not done here: free-running generation with these identities. The upstream prediction engine
builds the per-step inputs itself, so using this adapter there needs a further change.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from common import CSNET_REVISION, HOLDOUTS, configure, sha256, write_json

TOP_K = 2
PASS_SHARE = 0.6
MIN_MATCHES = 2
D_IDENTITY = 64


# ---------------------------------------------------------------------------------- identities
def build_registry(manifest: dict, cache: Path) -> dict:
    """Identities for every player seen in at least MIN_MATCHES matches that are not held back.

    Returns {"ids": {steamid: index from 1}, "groups": {steamid: [teammate steamids incl. self]}}.
    A group is the set of registered players who appear in exactly the same matches (a team).
    """
    from data import load_round
    seen: dict[str, set] = defaultdict(set)
    done = set()
    for entry in manifest["rounds"]:
        if entry["match_id"] in done or entry["match_id"] in HOLDOUTS:
            continue
        done.add(entry["match_id"])
        for player in load_round(str(cache / entry["file"]))["meta"]["players"]:
            seen[str(player["steamid"])].add(entry["match_id"])
    kept = sorted((s for s, m in seen.items() if len(m) >= MIN_MATCHES), key=int)
    ids = {s: i + 1 for i, s in enumerate(kept)}
    by_matches: dict[frozenset, list] = defaultdict(list)
    for s in kept:
        by_matches[frozenset(seen[s])].append(s)
    groups = {s: members for members in by_matches.values() for s in members}
    return {"ids": ids, "groups": groups}


# ---------------------------------------------------------------------------------------- model
class IdentityV2(nn.Module):
    """One vector per identity. It changes the decoder's starting vector (scale and shift) and is
    added to each of the three per-step decoder inputs. Everything starts at zero effect, and
    identity 0 ("unknown player") always gives exactly the base model."""

    def __init__(self, n_identities: int, d_model: int, d_identity: int = D_IDENTITY):
        super().__init__()
        self.n_identities, self.d_model, self.d_identity = n_identities, d_model, d_identity
        self.embedding = nn.Embedding(n_identities + 1, d_identity, padding_idx=0)
        self.start = nn.Linear(d_identity, 2 * d_model)
        self.steps = nn.ModuleList([nn.Linear(d_identity, d_model, bias=False) for _ in range(3)])
        for layer in (self.start, *self.steps):
            nn.init.zeros_(layer.weight)
        nn.init.zeros_(self.start.bias)

    def forward(self, start, depth, xyz, angle, ids):
        z = self.embedding(ids)                                   # [N, d_identity]
        known = (ids != 0).unsqueeze(-1)
        gamma, beta = self.start(z).chunk(2, dim=-1)
        start = torch.where(known, start * (1 + gamma) + beta, start)
        out = []
        for layer, ctx in zip(self.steps, (depth, xyz, angle)):
            out.append(ctx + torch.where(known, layer(z), torch.zeros_like(start)).unsqueeze(1))
        return start, *out


class LearnedCloneV2(nn.Module):
    def __init__(self, backbone, n_identities: int):
        super().__init__()
        self.backbone = backbone.eval().requires_grad_(False)
        self.adapter = IdentityV2(n_identities, backbone.cfg.d_model)

    @torch.no_grad()
    def encode(self, batch, bi, pi):
        """Everything the frozen base computes for the chosen targets. bi, pi: window and player index."""
        base = self.backbone
        base.eval()
        B, T, P = batch["player_pos"].shape[:3]
        n, d = base.cfg.n_ticks, base.cfg.d_model
        if T != n or n != 16 or P != 10:
            raise ValueError("Expected the pretrained 16-tick, 10-player window")
        N = len(bi)
        start = base.get_player_embeddings(batch)[bi, -1, pi]
        window = slice(n - 1, 2 * n - 1)
        depth = batch["player_depth_labels"][bi, :, pi][:, window]
        depth = base.embedder.depth_encoder(depth.reshape(N * n, 64, 5)).reshape(N, n, d)
        pos = batch["player_pos_labels"][bi, :, pi][:, window]
        map_emb = base.embedder.map_emb(batch["map_idx"][bi, 0].long())[:, None].expand(N, n, d)
        xyz = base.embedder.mlp1(torch.cat([pos, map_emb], dim=-1))
        angle = base.embedder.mlp_angle(batch["player_angle_labels"][bi, :, pi][:, window])
        tokens = base.tokenizer.encode_sequence(batch["label_camera"][bi, :, pi][:, window], n)
        return start, depth, xyz, angle, tokens

    def nll(self, encoded, ids):
        """Per target: how unlikely the real moves are under the given identities (lower = more likely)."""
        start, depth, xyz, angle, tokens = encoded
        start, depth, xyz, angle = self.adapter(start, depth, xyz, angle, ids)
        logits, targets = self.backbone.decoder(start, tokens, depth_ctx=depth, xyz_ctx=xyz, angle_ctx=angle)
        pad = self.backbone.tokenizer.PAD
        per_token = F.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), targets.reshape(-1),
                                    ignore_index=pad, reduction="none").reshape(targets.shape)
        mask = (targets != pad).float()
        return (per_token * mask).sum(1) / mask.sum(1).clamp(min=1)


def guided_logits(base_logits, own_logits, scale: float):
    """Amplify what the identity changes: base + scale * (own - base). scale 1 is the plain model."""
    return base_logits + scale * (own_logits - base_logits)


# ----------------------------------------------------------------------------------------- data
class WindowsV2(torch.utils.data.Dataset):
    """Windows from one split. Each item carries the identity of every player slot (0 = no identity
    or dead at the last input step), after the upstream player shuffle."""

    def __init__(self, cache: Path, manifest: dict, registry: dict, split: str, shuffle: bool, stride: int = 16):
        from data import load_round
        from training_data.pretrain_processor import PretrainWindowExtractor
        self.cache, self.registry, self.shuffle = cache, registry, shuffle
        self.extractor = PretrainWindowExtractor(n_ticks=16, stride=stride, min_input_ticks=16,
                                                 min_output_ticks=15, jitter=False, require_camera=True)
        self.index = []
        for entry in manifest["rounds"]:
            if entry["split"] != split:
                continue
            sample = load_round(str(cache / entry["file"]))
            slots = self._slot_ids(sample["meta"])
            for s in range(0, entry["ticks"] - 30, stride):
                if (sample["player_alive_mask"][s + 15] & (slots > 0)).any():
                    self.index.append((entry, s))
        if not self.index:
            raise ValueError(f"No windows for split {split}")

    def _slot_ids(self, meta) -> np.ndarray:
        return np.array([self.registry["ids"].get(str(p["steamid"]), 0) for p in meta["players"]], dtype=np.int64)

    def __len__(self):
        return len(self.index)

    def __getitem__(self, i):
        from data import load_round, shuffle_aligned
        from training_data.torch_dataset import augment_depth_with_angles, sample_to_torch
        entry, s = self.index[i]
        sample = load_round(str(self.cache / entry["file"]))
        window = self.extractor._build_window(sample, s, entry["ticks"], s, s + 16, s + 16, s + 31,
                                              sample["round_seconds"], .25, sample["meta"])
        ids = self._slot_ids(sample["meta"])
        ids = np.where(sample["player_alive_mask"][s + 15], ids, 0)
        if self.shuffle:
            window, ids, _ = shuffle_aligned(window, ids, 0, np.random.permutation(10))
        window = sample_to_torch(augment_depth_with_angles(window))
        window["slot_ids"] = torch.from_numpy(np.ascontiguousarray(ids))
        return window


def targets_of(batch):
    """Window index, player index and identity of every registered, alive player in the batch."""
    bi, pi = torch.nonzero(batch["slot_ids"] > 0, as_tuple=True)
    return bi, pi, batch["slot_ids"][bi, pi].long()


def wrong_teammates(ids: torch.Tensor, registry: dict, rng: random.Random) -> torch.Tensor:
    """For each identity, a random different identity from the same team."""
    by_index = {index: steamid for steamid, index in registry["ids"].items()}
    out = []
    for value in ids.tolist():
        mates = [registry["ids"][s] for s in registry["groups"][by_index[value]] if registry["ids"][s] != value]
        out.append(rng.choice(mates) if mates else value)
    return torch.tensor(out, dtype=torch.long, device=ids.device)


# ---------------------------------------------------------------------------------------- test
def rank_identities(nll_by_candidate: dict[int, float], true_id: int) -> int:
    """1 = the true identity makes the real moves most likely."""
    order = sorted(nll_by_candidate, key=lambda k: nll_by_candidate[k])
    return order.index(true_id) + 1


def summarise(ranks: dict[str, int], candidates: dict[str, int]) -> dict:
    passed = {s: r <= TOP_K for s, r in ranks.items()}
    share = sum(passed.values()) / len(passed) if passed else 0.0
    return {
        "players": len(ranks), "top_1": sum(r == 1 for r in ranks.values()),
        "top_k": sum(passed.values()), "k": TOP_K, "share_in_top_k": round(share, 3),
        "pass_share_required": PASS_SHARE, "pass": bool(passed) and share >= PASS_SHARE,
        "ranks": ranks, "candidates": candidates,
        "chance_share_in_top_k": round(float(np.mean([min(1.0, TOP_K / c) for c in candidates.values()])), 3) if candidates else None,
    }


@torch.no_grad()
def who_is_it(model, dataset, registry, device, max_windows: int | None, batch_size: int = 4):
    """For every identity: mean NLL of its real moves under each teammate identity, then the rank."""
    from training_data.torch_dataset import pretrain_collate_fn
    model.eval()
    by_index = {index: steamid for steamid, index in registry["ids"].items()}
    totals = defaultdict(lambda: defaultdict(float))     # true id -> candidate id -> summed NLL
    counts = defaultdict(int)
    picks = range(len(dataset)) if max_windows is None or len(dataset) <= max_windows else \
        np.linspace(0, len(dataset) - 1, max_windows, dtype=int)
    picks = [int(i) for i in picks]
    for start in range(0, len(picks), batch_size):
        batch = pretrain_collate_fn([dataset[i] for i in picks[start:start + batch_size]])
        batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
        bi, pi, ids = targets_of(batch)
        if not len(ids):
            continue
        with torch.autocast(device_type=device, dtype=torch.bfloat16, enabled=device == "cuda"):
            encoded = model.encode(batch, bi, pi)
            group_size = max(len(registry["groups"][by_index[v]]) for v in ids.tolist())
            for k in range(group_size):
                cand = torch.tensor([registry["ids"][registry["groups"][by_index[v]][k % len(registry["groups"][by_index[v]])]]
                                     for v in ids.tolist()], device=device)
                values = model.nll(encoded, cand).float().cpu().tolist()
                for true, c, value in zip(ids.tolist(), cand.tolist(), values):
                    if k < len(registry["groups"][by_index[true]]):
                        totals[true][c] += value
            base = model.nll(encoded, torch.zeros_like(ids)).float().cpu().tolist()
        for true, value in zip(ids.tolist(), base):
            totals[true][0] += value
            counts[true] += 1
    ranks, candidates, detail = {}, {}, {}
    for true, sums in totals.items():
        mean = {c: v / counts[true] for c, v in sums.items()}
        teammates = {c: v for c, v in mean.items() if c != 0}
        if len(teammates) < 2:
            continue
        steamid = by_index[true]
        ranks[steamid] = rank_identities(teammates, true)
        candidates[steamid] = len(teammates)
        others = [v for c, v in teammates.items() if c != true]
        detail[steamid] = {"windows": counts[true], "own": round(mean[true], 5), "no_identity": round(mean[0], 5),
                           "best_other": round(min(others), 5), "mean_other": round(float(np.mean(others)), 5)}
    result = summarise(ranks, candidates)
    result["detail"] = detail
    # Used only to choose a checkpoint on development rounds: how much more likely the real moves
    # are under the true identity than under the average teammate identity.
    result["margin"] = round(float(np.mean([d["mean_other"] - d["own"] for d in detail.values()])), 6) if detail else 0.0
    return result


# ---------------------------------------------------------------------------------------- train
def load_model(args, registry):
    from model import load_backbone
    model = LearnedCloneV2(load_backbone(args.csnet, args.checkpoint, args.device), len(registry["ids"]))
    return model.to(args.device)


def train(args):
    from training_data.torch_dataset import pretrain_collate_fn
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    rng = random.Random(42)
    manifest = json.loads((args.cache / "manifest.json").read_text())
    registry = build_registry(manifest, args.cache)
    training = WindowsV2(args.cache, manifest, registry, "train", shuffle=True)
    development = WindowsV2(args.cache, manifest, registry, "dev", shuffle=False)
    model = load_model(args, registry)
    optimizer = torch.optim.AdamW(model.adapter.parameters(), lr=args.lr, weight_decay=.01)
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "registry.json", registry)
    print(f"TRAINING_STARTED identities={len(registry['ids'])} teams={len({frozenset(g) for g in registry['groups'].values()})} "
          f"train_windows={len(training)} dev_windows={len(development)} "
          f"trainable_parameters={sum(p.numel() for p in model.adapter.parameters())}", flush=True)

    def save(path, step, dev):
        torch.save(dict(adapter={k: v.detach().cpu() for k, v in model.adapter.state_dict().items()},
                        registry=registry, d_model=model.adapter.d_model, d_identity=model.adapter.d_identity,
                        csnet_revision=CSNET_REVISION, step=step, dev=dev, version=2,
                        base_checkpoint_sha256=model.backbone.checkpoint_sha256,
                        manifest_sha256=sha256(args.cache / "manifest.json"), seed=42), path)

    best_dev = who_is_it(model, development, registry, args.device, args.dev_windows)
    print("DEV", json.dumps(dict(step=0, **{k: best_dev[k] for k in ("top_1", "top_k", "players", "margin")})), flush=True)
    best, best_step, stale, history = best_dev["margin"], 0, 0, []
    save(args.out / "best.pt", 0, best_dev)
    started = time.time()
    order = np.random.permutation(len(training))
    for step in range(1, args.steps + 1):
        chosen = [int(order[(step * args.batch_size + i) % len(order)]) for i in range(args.batch_size)]
        batch = pretrain_collate_fn([training[i] for i in chosen])
        batch = {k: v.to(args.device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
        bi, pi, ids = targets_of(batch)
        if not len(ids):
            continue
        model.adapter.train()
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=args.device, dtype=torch.bfloat16, enabled=args.device == "cuda"):
            encoded = model.encode(batch, bi, pi)
            hidden = torch.rand(len(ids), device=ids.device) < args.hide          # identity hidden at random
            own = model.nll(encoded, torch.where(hidden, torch.zeros_like(ids), ids))
            other = model.nll(encoded, wrong_teammates(ids, registry, rng))
            shown = (~hidden).float()
            # The real moves must be more likely under the true identity than under a teammate's.
            apart = (F.relu(args.margin + own - other) * shown).sum() / shown.sum().clamp(min=1)
            objective = own.mean() + args.apart_weight * apart
        if not torch.isfinite(objective):
            raise RuntimeError("Nonfinite training loss; stopping before saving a corrupt adapter")
        objective.backward()
        torch.nn.utils.clip_grad_norm_(model.adapter.parameters(), 1.)
        optimizer.step()
        if step == 1 or step % 20 == 0:
            record = dict(step=step, nll=float(own.mean().detach()), apart=float(apart.detach()),
                          targets=len(ids), elapsed_seconds=round(time.time() - started, 1))
            history.append(record)
            print("TRAIN", json.dumps(record), flush=True)
            write_json(args.out / "progress.json", dict(state="training", **record))
        if step % args.check_every == 0 or step == args.steps:
            dev = who_is_it(model, development, registry, args.device, args.dev_windows)
            save(args.out / "last.pt", step, dev)
            if dev["margin"] > best + 1e-6:
                best, best_step, stale = dev["margin"], step, 0
                save(args.out / "best.pt", step, dev)
            else:
                stale += 1
            print("DEV", json.dumps(dict(step=step, best_step=best_step,
                  **{k: dev[k] for k in ("top_1", "top_k", "players", "margin")})), flush=True)
            write_json(args.out / "training.json", dict(history=history, best_step=best_step, latest_dev=dev,
                       settings=dict(steps=args.steps, batch_size=args.batch_size, lr=args.lr, hide=args.hide,
                                     margin=args.margin, apart_weight=args.apart_weight),
                       holdout_used_for_selection=False))
            if stale >= args.patience:
                print("EARLY_STOP: development margin has not improved", flush=True)
                break
    write_json(args.out / "progress.json", dict(state="trained_needs_test", best_step=best_step,
               elapsed_seconds=round(time.time() - started, 1)))
    print(f"TRAINING_COMPLETE best_step={best_step}; the held-out test has not been run", flush=True)


def test(args):
    manifest = json.loads((args.cache / "manifest.json").read_text())
    saved = torch.load(args.out / "best.pt", map_location="cpu", weights_only=True)
    registry = saved["registry"]
    if saved["base_checkpoint_sha256"] != sha256(args.checkpoint) or saved["manifest_sha256"] != sha256(args.cache / "manifest.json"):
        raise ValueError("Base checkpoint or data manifest differs from the training run")
    model = load_model(args, registry)
    model.adapter.load_state_dict(saved["adapter"], strict=True)
    held = WindowsV2(args.cache, manifest, registry, "test", shuffle=False)
    result = who_is_it(model, held, registry, args.device, None)
    result.update(split="test", selected_step=saved["step"], held_back_matches=sorted(HOLDOUTS),
                  interpretation="Teacher-forced likelihood on 4-steps-per-second movement tokens. "
                                 "Not free-running play, not combat skill, not proof of identical quirks.")
    write_json(args.out / "test.json", result)
    write_json(args.out / "progress.json", dict(state="validated_pass" if result["pass"] else "validation_failed",
               selected_step=saved["step"], deployed=False))
    print("TEST_COMPLETE", json.dumps({k: v for k, v in result.items() if k != "detail"}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["train", "test"])
    parser.add_argument("--csnet", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--batch-size", type=int, default=6, help="windows per step; each has up to 10 targets")
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--hide", type=float, default=0.15, help="share of targets trained with the identity hidden")
    parser.add_argument("--margin", type=float, default=0.02)
    parser.add_argument("--apart-weight", type=float, default=1.0)
    parser.add_argument("--check-every", type=int, default=100)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--dev-windows", type=int, default=120)
    args = parser.parse_args()
    configure(args.csnet)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested a GPU, but no CUDA device is connected")
    torch.set_num_threads(4)
    if args.device == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
    (train if args.command == "train" else test)(args)


if __name__ == "__main__":
    main()
