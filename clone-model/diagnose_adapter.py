"""Diagnose a Stage A identity adapter on CPU, using training and development data only.

Two subcommands:

``adapter``  needs only adapter checkpoints (no base model): identity vectors, FiLM scale/shift per
             identity, how far the parameters moved, the training log and a development review file.
``decoder``  needs the pinned base checkpoint and a development cache: teacher-forced token
             agreement, logit margins and losses for own / other / no identity on development
             windows. It loads development rounds only and refuses a cache that lists a
             held-out match as development data.

Neither subcommand trains, selects or promotes anything.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch

from common import HOLDOUTS, write_json

REGULARIZER_WEIGHT = 0.001  # train.py: objective = loss + .001 * regularizer
WEIGHT_DECAY = 0.01         # train.py: AdamW(weight_decay=.01)
SEED = 42


# ---------------------------------------------------------------- adapter-only analysis

def load_adapter(path: Path) -> dict:
    saved = torch.load(path, map_location="cpu", weights_only=True)
    state = saved["adapter"]
    for key in ("embedding.weight", "film.to_scale_shift.weight", "film.to_scale_shift.bias"):
        if key not in state:
            raise ValueError(f"{path} is not an identity adapter checkpoint (missing {key})")
    return saved


def film_terms(state: dict) -> dict:
    """Per identity row (1..n): gamma and beta exactly as identity.FiLM computes them."""
    E = state["embedding.weight"].double()
    W = state["film.to_scale_shift.weight"].double()
    b = state["film.to_scale_shift.bias"].double()
    d = W.shape[0] // 2
    out = {}
    for row in range(1, E.shape[0]):
        gb = W @ E[row] + b
        out[row] = dict(gamma=gb[:d], beta=gb[d:])
    return out


def _cos(a: torch.Tensor, b: torch.Tensor) -> float:
    denominator = float(a.norm() * b.norm())
    return float(a @ b) / denominator if denominator else 0.0


def _vector_stats(v: torch.Tensor, thresholds) -> dict:
    energy = v.square()
    top = torch.sort(energy, descending=True).values
    k = max(1, len(v) // 10)
    return dict(norm=float(v.norm()), rms=float(energy.mean().sqrt()), max_abs=float(v.abs().max()),
        dims_above={str(t): int((v.abs() > t).sum()) for t in thresholds},
        top10pct_energy_share=float(top[:k].sum() / energy.sum()) if float(energy.sum()) else 0.0)


def names_by_row(registry: dict, players: dict | None) -> dict:
    by_sid = {sid: name for name, sid in (players or {}).items()}
    return {row: by_sid.get(sid, sid) for sid, row in registry.items()}


def adapter_summary(saved: dict, players: dict | None = None, lr: float | None = None,
                    initial_embedding: torch.Tensor | None = None) -> dict:
    state, step = saved["adapter"], int(saved.get("step", 0))
    E = state["embedding.weight"].double()
    W = state["film.to_scale_shift.weight"].double()
    b = state["film.to_scale_shift.bias"].double()
    names = names_by_row(saved["registry"], players)
    terms = film_terms(state)
    rows = sorted(terms)
    result = dict(step=step, d_model=int(saved["d_model"]), d_identity=int(saved["d_identity"]),
        trainable_parameters=int(sum(v.numel() for v in state.values())),
        unknown_row_is_zero=bool(torch.count_nonzero(E[0]) == 0),
        embedding={names[r]: dict(row=r, norm=float(E[r].norm())) for r in rows},
        film_weight=dict(norm=float(W.norm()), max_abs=float(W.abs().max()), rms=float(W.square().mean().sqrt())),
        film_bias=dict(gamma_norm=float(b[:len(b)//2].norm()), beta_norm=float(b[len(b)//2:].norm()),
            max_abs=float(b.abs().max())),
        identities={})
    for r in rows:
        result["identities"][names[r]] = dict(
            gamma=_vector_stats(terms[r]["gamma"], (0.01, 0.05, 0.1, 0.2)),
            beta=_vector_stats(terms[r]["beta"], (0.1, 0.5, 1.0)))
    if len(rows) == 2:
        a, c = rows
        shared = {k: (terms[a][k] + terms[c][k]) / 2 for k in ("gamma", "beta")}
        half_difference = {k: (terms[a][k] - terms[c][k]) / 2 for k in ("gamma", "beta")}
        result["pair"] = dict(
            embedding_cosine=_cos(E[a], E[c]),
            gamma_cosine=_cos(terms[a]["gamma"], terms[c]["gamma"]),
            beta_cosine=_cos(terms[a]["beta"], terms[c]["beta"]),
            # Own-vs-other differs only by the half-difference part; the shared part moves both identities alike.
            shared_norm={k: float(v.norm()) for k, v in shared.items()},
            half_difference_norm={k: float(v.norm()) for k, v in half_difference.items()})
    if lr and step:
        bound = lr * step  # Adam moves each parameter by at most about lr per step.
        result["adam_step_bound"] = dict(lr=lr, step=step, max_move_per_parameter=bound,
            film_weight_max_over_bound=float(W.abs().max()) / bound,
            film_bias_max_over_bound=float(b.abs().max()) / bound,
            weight_decay_shrink=1 - (1 - lr * WEIGHT_DECAY) ** step)
    if initial_embedding is not None:
        init = initial_embedding.double()
        if init.shape != E.shape:
            raise ValueError("Initial embedding shape does not match the checkpoint")
        moved = E - init
        result["embedding_vs_init"] = {names[r]: dict(cosine_to_init=_cos(E[r], init[r]),
            init_norm=float(init[r].norm()), moved_norm=float(moved[r].norm()),
            moved_max_abs=float(moved[r].abs().max()),
            moved_max_over_adam_bound=(float(moved[r].abs().max()) / (lr * step)) if lr and step else None)
            for r in rows}
        result["embedding_vs_init"]["init_pair_cosine"] = _cos(init[rows[0]], init[rows[-1]])
    return result


def drift_summary(early: dict, late: dict, players: dict | None = None) -> dict:
    """How much the adapter changed between two checkpoints of the same run."""
    a, b = early["adapter"], late["adapter"]
    tensors = {}
    for key in a:
        x, y = a[key].double(), b[key].double()
        tensors[key] = dict(relative_change=float((y - x).norm() / x.norm()) if float(x.norm()) else None,
            cosine=_cos(x.flatten(), y.flatten()), max_abs_change=float((y - x).abs().max()))
    ta, tb = film_terms(a), film_terms(b)
    names = names_by_row(early["registry"], players)
    per_identity = {names[r]: {k: dict(norm_early=float(ta[r][k].norm()), norm_late=float(tb[r][k].norm()),
        cosine=_cos(ta[r][k], tb[r][k]), change_norm=float((tb[r][k] - ta[r][k]).norm())) for k in ("gamma", "beta")}
        for r in ta}
    return dict(from_step=int(early.get("step", 0)), to_step=int(late.get("step", 0)),
        tensors=tensors, identities=per_identity,
        dev_metrics={"from": early.get("metrics"), "to": late.get("metrics")})


def training_summary(training: dict, regularizer_weight: float = REGULARIZER_WEIGHT) -> dict:
    history = training["history"]
    losses = np.array([h["loss"] for h in history])
    regs = np.array([h["regularizer"] for h in history])
    blocks = {}
    for h in history:
        if h["step"] <= 1:
            continue
        key = f"{(h['step'] - 1) // 100 * 100 + 1}-{(h['step'] - 1) // 100 * 100 + 100}"
        blocks.setdefault(key, []).append(h["loss"])
    dev = {}
    for name, base in training["baseline"].items():
        latest = training["latest_dev"][name]
        dev[name] = dict(windows=base["windows"], base=base["base_teacher_forced_loss"],
            latest_own=latest["own_teacher_forced_loss"],
            latest_improvement=base["base_teacher_forced_loss"] - latest["own_teacher_forced_loss"],
            latest_relative_improvement=(base["base_teacher_forced_loss"] - latest["own_teacher_forced_loss"])
                / base["base_teacher_forced_loss"])
    return dict(best_step=training["best_step"], last_logged_step=int(history[-1]["step"]),
        holdout_used_for_selection=training.get("holdout_used_for_selection"),
        logged_train_batches=len(history),
        train_loss=dict(first=float(losses[0]), mean=float(losses.mean()), std=float(losses.std()),
            min=float(losses.min()), max=float(losses.max()),
            mean_per_100_steps={k: float(np.mean(v)) for k, v in blocks.items()}),
        train_loss_base_comparison="not logged: the trainer records only own-identity batch loss",
        regularizer=dict(weight=regularizer_weight, first_nonzero=float(regs[regs > 0][0]) if (regs > 0).any() else 0.0,
            last=float(regs[-1]), max=float(regs.max()),
            weighted_last=float(regularizer_weight * regs[-1]),
            weighted_share_of_objective_last=float(regularizer_weight * regs[-1] / (losses[-1] + regularizer_weight * regs[-1])),
            still_rising=bool(np.mean(regs[-10:]) > np.mean(regs[-20:-10]))),
        development=dev)


def implied_condition_rms(regularizer: float, identity_terms: dict) -> float | None:
    """Rough condition scale implied by the logged regularizer.

    regularizer = mean((gamma * x + beta)^2) over batch and dimensions. Assuming x is independent
    of gamma/beta and roughly zero-mean, that is mean(gamma^2) * mean(x^2) + mean(beta^2).
    Identities are averaged equally because train.py alternates players within each batch.
    This is an estimate built on that assumption, not a measurement.
    """
    g2 = np.mean([float(t["gamma"].square().mean()) for t in identity_terms.values()])
    b2 = np.mean([float(t["beta"].square().mean()) for t in identity_terms.values()])
    if g2 <= 0 or regularizer <= b2:
        return None
    return math.sqrt((regularizer - b2) / g2)


def review_summary(review: dict) -> dict:
    if review.get("split") != "dev":
        raise ValueError("Only development review files are summarised")
    pairs = (("own", "base"), ("own", "other"), ("other", "base"))
    counts = {f"{a}=={b}": 0 for a, b in pairs}
    counts["all_three_equal"] = 0
    cases = []
    for case in review["cases"]:
        if case["match_id"] in HOLDOUTS:
            raise ValueError("A held-out match appears in a development review")
        paths = {k: np.asarray([p[1:] for p in v["path"]], dtype=float) for k, v in case["predictions"].items()}
        yaws = {k: np.asarray(v["yaw_degrees"], dtype=float) for k, v in case["predictions"].items()}
        actual = np.asarray([p[1:] for p in case["actual"]["path"]], dtype=float)
        row = dict(player=case["player"], match_id=case["match_id"], round_id=case["round_id"],
            side=case["side"], context_tick=case["context_tick"])
        equal = {}
        for a, b in pairs:
            same = paths[a].shape == paths[b].shape and np.array_equal(paths[a], paths[b])
            equal[(a, b)] = same
            counts[f"{a}=={b}"] += int(same)
            n = min(len(paths[a]), len(paths[b]))
            row[f"max_xyz_diff_{a}_{b}"] = float(np.abs(paths[a][:n] - paths[b][:n]).max()) if n else None
            m = min(len(yaws[a]), len(yaws[b]))
            row[f"max_yaw_diff_{a}_{b}"] = float(np.abs(yaws[a][:m] - yaws[b][:m]).max()) if m else None
        counts["all_three_equal"] += int(all(equal.values()))
        for k, p in paths.items():
            n = min(len(p), len(actual))
            row[f"ade_{k}"] = float(np.linalg.norm(p[:n] - actual[:n], axis=1).mean()) if n else None
        cases.append(row)
    return dict(cases=len(cases), exact_equal_paths=counts, per_case=cases,
        note="Small deterministic development selection; not a validation statistic.")


def initial_embedding(csnet: Path, registry: dict, d_identity: int = 64, seed: int = SEED) -> torch.Tensor:
    """Rebuild the identity table at initialization by replaying train.py's CPU random draws.

    train.py seeds torch with 42, builds the pretrained model on CPU (its parameter init consumes
    random numbers), loads weights without drawing any, then builds PlayerAdapter. No weights are
    needed to replay this. Check the result: trained rows should stay close to it.
    """
    import yaml
    from dataclasses import fields
    from common import configure
    configure(csnet)
    from pretrain_model import CS2PretrainModel, PretrainConfig
    from identity import PlayerAdapter
    config = yaml.safe_load((Path(csnet) / "config/pretrain-a100-pro.yaml").read_text(encoding="utf-8"))
    config = {k: v for k, v in config.items() if k in {f.name for f in fields(PretrainConfig)}}
    torch.manual_seed(seed)
    model = CS2PretrainModel(PretrainConfig(**config))
    adapter = PlayerAdapter(registry, model.cfg.d_model, d_identity)
    return adapter.embedding.weight.detach().clone()


# ---------------------------------------------------------------- decoder sensitivity (needs base)

def decoder_inputs(model, batch):
    """The part of model.LearnedClone.forward before the adapter, returned instead of consumed."""
    base = model.backbone
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
    return dict(conditions=conditions, tokens=tokens, depth_ctx=depth_ctx, xyz_ctx=xyz_ctx, angle_ctx=angle_ctx)


@torch.no_grad()
def decode(model, inputs, conditions):
    logits, targets = model.backbone.decoder(conditions, inputs["tokens"], depth_ctx=inputs["depth_ctx"],
        xyz_ctx=inputs["xyz_ctx"], angle_ctx=inputs["angle_ctx"])
    return logits.float(), targets


def compare_logits(reference: torch.Tensor, other: torch.Tensor, mask: torch.Tensor) -> dict:
    """Token-level agreement between two logit tensors at the predicted (non-PAD) positions."""
    r, o = reference[mask], other[mask]
    top2 = torch.topk(r, 2, dim=-1).values
    margin = top2[:, 0] - top2[:, 1]
    delta = (o - r).abs().max(dim=-1).values
    lr_, lo = torch.log_softmax(r, -1), torch.log_softmax(o, -1)
    return dict(positions=int(mask.sum()),
        argmax_agreement=float((r.argmax(-1) == o.argmax(-1)).float().mean()),
        mean_kl_reference_to_other=float((lr_.exp() * (lr_ - lo)).sum(-1).mean()),
        mean_max_abs_logit_change=float(delta.mean()), max_abs_logit_change=float(delta.max()),
        # A flip needs the gap between the top two tokens to close: at most 2 * max change.
        share_positions_flippable=float((2 * delta > margin).float().mean()),
        reference_margin_median=float(margin.median()))


def _loss_per_window(model, logits, targets):
    pad = model.backbone.tokenizer.PAD
    losses = torch.nn.functional.cross_entropy(logits.transpose(1, 2), targets, ignore_index=pad, reduction="none")
    mask = targets != pad
    return (losses * mask).sum(1) / mask.sum(1)


def paired_difference(differences, groups) -> dict:
    """Mean per-window loss difference, with the standard error over rounds as well as windows.

    Windows from one round are correlated, so the round-level error is the honest one.
    """
    d = np.asarray(differences, dtype=float)
    by_round = {}
    for value, group in zip(d, groups):
        by_round.setdefault(group, []).append(value)
    round_means = np.array([np.mean(v) for v in by_round.values()])
    sem = lambda x: float(x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else None
    return dict(mean=float(d.mean()), sem_windows=sem(d), round_mean=float(round_means.mean()),
        sem_rounds=sem(round_means), share_windows_lower=float((d < 0).mean()),
        share_rounds_lower=float((round_means < 0).mean()), rounds=len(round_means))


def measure_decoder(model, dataset, identity_of: dict, max_per_player: int | None = None, batch_size: int = 4,
                    scales: tuple = ()) -> dict:
    """Teacher-forced own / other / base on development windows (all, or an even subset per player).

    Controls: ``shared_only`` keeps only the part of the FiLM change that both identities share;
    ``swapped_condition`` gives each window another window's condition (how much the decoder uses
    the condition slot at all). ``own_xK`` / ``other_xK`` multiply the trained FiLM change by K: a
    probe of the direction, not a trained model.
    """
    from training_data.torch_dataset import pretrain_collate_fn
    model.eval()
    pad = model.backbone.tokenizer.PAD
    report = {}
    for name, indices in dataset.by_player.items():
        if max_per_player:
            indices = [indices[i] for i in np.linspace(0, len(indices)-1, min(max_per_player, len(indices)), dtype=int)]
        own_id = identity_of[name]
        others = [v for v in identity_of.values() if v != own_id]
        if len(others) != 1:
            raise ValueError("Expected exactly one other identity")
        variants = ["own", "other", "base", "shared_only", "swapped_condition"]
        for k in scales:
            variants += [f"own_x{k:g}", f"other_x{k:g}"]
        losses = {v: [] for v in variants}
        batch_losses = {v: [] for v in ("own", "base")}
        acc = {v: [0, 0] for v in variants}
        pair_names = [("own", "base"), ("other", "base"), ("own", "other"), ("shared_only", "base"),
            ("swapped_condition", "base")]
        for k in scales:
            pair_names += [(f"own_x{k:g}", "base"), (f"own_x{k:g}", f"other_x{k:g}")]
        pairs = {f"{a}_vs_{b}": [] for a, b in pair_names}
        scale = dict(condition_rms=[], own_shift_rms=[], other_shift_rms=[], cond_proj_rms=[],
            own_cond_proj_shift_rms=[], depth_slot_rms=[], xyz_slot_rms=[], angle_slot_rms=[])
        for start in range(0, len(indices), batch_size):
            items = [dataset[i] for i in indices[start:start+batch_size]]
            batch = pretrain_collate_fn(items)
            if any(int(x) != own_id for x in batch["identity"]):
                raise ValueError("Window identity does not match its player")
            inputs = decoder_inputs(model, batch)
            cond = inputs["conditions"]
            ids = batch["identity"].long()
            adapted = dict(own=model.adapter(cond, ids), other=model.adapter(cond, torch.full_like(ids, others[0])),
                base=cond, swapped_condition=cond.roll(1, 0))
            adapted["shared_only"] = (adapted["own"] + adapted["other"]) / 2
            for k in scales:
                adapted[f"own_x{k:g}"] = cond + k * (adapted["own"] - cond)
                adapted[f"other_x{k:g}"] = cond + k * (adapted["other"] - cond)
            out = {k: decode(model, inputs, v) for k, v in adapted.items()}
            targets = out["base"][1]
            mask = targets != pad
            for k, (logits, _) in out.items():
                if k == "swapped_condition" and len(items) < 2:
                    continue  # rolling a batch of one gives the window its own condition back
                losses[k].extend(_loss_per_window(model, logits, targets).tolist())
                acc[k][0] += int((logits.argmax(-1)[mask] == targets[mask]).sum()); acc[k][1] += int(mask.sum())
            for k in ("own", "base"):
                loss, _ = model.backbone._compute_loss(out[k][0], targets)
                batch_losses[k].append(float(loss))
            for a, b in pair_names:
                if a == "swapped_condition" and len(items) < 2:
                    continue
                pairs[f"{a}_vs_{b}"].append(compare_logits(out[b][0], out[a][0], mask))
            dec = model.backbone.decoder
            rms = lambda t: float(t.float().square().mean().sqrt())
            scale["condition_rms"].append(rms(cond))
            scale["own_shift_rms"].append(rms(adapted["own"] - cond))
            scale["other_shift_rms"].append(rms(adapted["other"] - cond))
            scale["cond_proj_rms"].append(rms(dec.cond_proj(cond)))
            scale["own_cond_proj_shift_rms"].append(rms(dec.cond_proj(adapted["own"]) - dec.cond_proj(cond)))
            scale["depth_slot_rms"].append(rms(dec.depth_dec_adapter(inputs["depth_ctx"])))
            scale["xyz_slot_rms"].append(rms(dec.xyz_dec_adapter(inputs["xyz_ctx"])))
            scale["angle_slot_rms"].append(rms(dec.angle_dec_adapter(inputs["angle_ctx"])))
        L = {k: np.asarray(v) for k, v in losses.items()}
        def weighted(rows):
            total = sum(r["positions"] for r in rows)
            keys = [k for k in rows[0] if k not in ("positions", "max_abs_logit_change")]
            merged = {k: sum(r[k] * r["positions"] for r in rows) / total for k in keys}
            merged["max_abs_logit_change"] = max(r["max_abs_logit_change"] for r in rows)
            merged["positions"] = total
            return merged
        rounds = [dataset.index[i][0]["file"] for i in indices]
        report[name] = dict(windows=len(indices), rounds=len(set(rounds)),
            mean_loss={k: float(v.mean()) for k, v in L.items()},
            trainer_style_dev_loss={k: float(np.mean(v)) for k, v in batch_losses.items()},
            token_accuracy={k: a / n for k, (a, n) in acc.items()},
            own_minus_base=paired_difference(L["own"] - L["base"], rounds),
            own_minus_other=paired_difference(L["own"] - L["other"], rounds),
            shared_only_minus_base=paired_difference(L["shared_only"] - L["base"], rounds),
            **{f"own_x{k:g}_minus_other_x{k:g}": paired_difference(L[f"own_x{k:g}"] - L[f"other_x{k:g}"], rounds)
               for k in scales},
            logits={k: weighted(v) for k, v in pairs.items() if v},
            scale={k: float(np.mean(v)) for k, v in scale.items()})
    return report


def check_development_manifest(manifest: dict) -> None:
    """The decoder measurement loads development rounds only (data.Windows(cache, "dev")).

    Test-split entries in a full cache are never opened. A development entry from a held-out
    match means the cache is corrupt, so it is refused.
    """
    development = [e for e in manifest["rounds"] if e["split"] == "dev"]
    if not development:
        raise ValueError("The cache has no development rounds")
    if any(e["match_id"] in HOLDOUTS for e in development):
        raise ValueError("A held-out match is listed as development data; refusing the cache")


def load_for_decoder(csnet: Path, cache: Path, checkpoint: Path, adapter_path: Path, device: str = "cpu"):
    from common import configure
    configure(csnet)
    from data import Windows
    from model import LearnedClone, load_backbone
    manifest = json.loads((cache / "manifest.json").read_text())
    check_development_manifest(manifest)
    saved = load_adapter(adapter_path)
    if saved["registry"] != manifest["registry"]:
        raise ValueError("Adapter registry does not match the cache")
    backbone = load_backbone(csnet, checkpoint, device)
    if backbone.checkpoint_sha256 != saved["base_checkpoint_sha256"]:
        raise ValueError("Base checkpoint differs from the one the adapter was trained on")
    model = LearnedClone(backbone, saved["registry"]).to(device)
    model.adapter.load_state_dict(saved["adapter"], strict=True)
    dataset = Windows(cache, "dev")
    identity_of = {name: saved["registry"][sid] for name, sid in manifest["players"].items()}
    return model, dataset, identity_of, saved


# ---------------------------------------------------------------- CLI

def _print(value):
    print(json.dumps(value, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("adapter", help="Adapter-only analysis (no base model)")
    a.add_argument("--best", type=Path, required=True)
    a.add_argument("--last", type=Path)
    a.add_argument("--training", type=Path, help="training.json from the run")
    a.add_argument("--review", type=Path, help="development review JSON (cs2.clone.review.v1)")
    a.add_argument("--manifest", type=Path, help="run manifest.json, for player names")
    a.add_argument("--lr", type=float, help="learning rate used by the run (adds the Adam step bound)")
    a.add_argument("--csnet", type=Path, help="pinned CS-NET checkout: rebuild the initial identity table")
    a.add_argument("--out", type=Path, required=True)
    d = sub.add_parser("decoder", help="Teacher-forced decoder sensitivity on development windows")
    for flag in ("--csnet", "--cache", "--checkpoint", "--adapter", "--out"):
        d.add_argument(flag, type=Path, required=True)
    d.add_argument("--max-per-player", type=int, help="even subset per player (train.py's dev check used 24)")
    d.add_argument("--threads", type=int, default=4)
    d.add_argument("--scales", type=float, nargs="*", default=(), help="probe: multiply the FiLM change by these factors")
    args = parser.parse_args(argv)

    if args.command == "adapter":
        players = json.loads(args.manifest.read_text())["players"] if args.manifest else None
        best = load_adapter(args.best)
        init = initial_embedding(args.csnet, best["registry"], best["d_identity"]) if args.csnet else None
        report = dict(split_used="training log, adapter weights and development review only",
            best=adapter_summary(best, players, args.lr, init))
        if args.last:
            last = load_adapter(args.last)
            report["last"] = adapter_summary(last, players, args.lr, init)
            report["drift_best_to_last"] = drift_summary(best, last, players)
        if args.training:
            training = json.loads(args.training.read_text())
            report["training"] = training_summary(training)
            by_step = {h["step"]: h["regularizer"] for h in training["history"]}
            for key, saved in (("best", best), ("last", report.get("last") and last)):
                if saved and saved["step"] in by_step:
                    report[key]["implied_condition_rms"] = dict(
                        value=implied_condition_rms(by_step[saved["step"]], film_terms(saved["adapter"])),
                        regularizer_at_step=by_step[saved["step"]],
                        assumption="x independent of gamma/beta, zero-mean; one noisy batch value")
        if args.review:
            report["review"] = review_summary(json.loads(args.review.read_text()))
        write_json(args.out, report)
        _print(report)
    else:
        torch.set_num_threads(args.threads)
        model, dataset, identity_of, saved = load_for_decoder(args.csnet, args.cache, args.checkpoint, args.adapter)
        report = dict(split="dev", adapter_step=int(saved["step"]), max_per_player=args.max_per_player,
            precision="float32 on CPU (training ran bfloat16 autocast on GPU)",
            players=measure_decoder(model, dataset, identity_of, args.max_per_player, scales=tuple(args.scales)))
        write_json(args.out, report)
        _print(report)


if __name__ == "__main__":
    main()
