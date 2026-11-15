"""Donk model, self-trained on its own imagined play (expert iteration). Design: ROUND3_DESIGN.md 8.5.

Why: the first donk model (donk.py) learned only from donk's recorded moves. When it generates play,
its small mistakes lead it into situations the recordings never show, and its paths got worse than the
generic model's (behaviour cloning's "exposure bias"). The fix used here trains the model inside its
own imagined futures:

  1. Imagine. From moments in donk's training rounds, CS-NET's own engine samples 8 four-second
     futures with the current donk model. While it does so, the decoder inputs it computes along each
     imagined path (what the player would see and where he would be) are recorded.
  2. Judge. Futures that break a human per-step limit (H8 to H10) are thrown away. Of the rest, the
     one closest to what donk really did from that moment is kept (best-of-N, as in expert
     iteration and reward-ranked fine-tuning).
  3. Learn. The model is trained on the kept futures, in the situations its own play created, plus
     donk's real windows, with the same KL anchor to CS-NET as donk.py (AlphaStar).
  4. Repeat. Each iteration is scored by free-running play on donk's dev-A rounds; the best is kept.

The recording of decoder inputs reuses the engine's own code: the engine's context functions and
generate_group are wrapped, not copied (CS-NET, MIT, revision pinned in common.py).

Rounds. Matches 2393242 and 2393024 (round 2 final tests) and dev-B (donk.py's final test) are spent
and never used. A new final test, test-C, is cut from donk's training rounds before anything runs:
rounds with round_id % 6 == 3. They are excluded from real-data training, from imagination and from
selection. The first donk model trained on them, so it is not compared here; only the base is.

Pass rule for "test", fixed before any run (same as donk.py, on test-C): P1 free-running mean path
error lower than the base's with the 95% paired bootstrap interval below zero; P2 closer than the base
to real donk on at least 2 of 3 behaviour measures; P3 human-limit breaks no more often than the base.

    python imagine.py run --csnet <csnet> --cache <cache> --checkpoint <base.pt> --out <run> --device cuda
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch

import donk
from common import CSNET_REVISION, HOLDOUTS, configure, sha256, write_json

TEST_MOD, TEST_REST = 6, 3


def is_test_round(entry) -> bool:
    return entry["round_id"] % TEST_MOD == TEST_REST


def split_training(dataset):
    """donk's training windows into (pool for learning and imagination, test-C)."""
    pool, test = [], []
    for i in donk.donk_indices(dataset):
        (test if is_test_round(dataset.index[i][0]) else pool).append(i)
    return pool, test


def moments(dataset, indices):
    """(round file, tick, player index) for each window, as donk.evaluate builds them."""
    out = []
    for i in indices:
        entry, s = dataset.index[i]
        out.append((entry["file"], s + 15, entry["target_index"]))
    return out


# --------------------------------------------------------------------------------------- imagining
class Recorder:
    """Wraps a PredictionEngine so that one sampled call also returns each sample's decoder inputs."""

    def __init__(self, engine):
        self.engine, self.on = engine, False
        self.depth, self.xyz, self.angle, self.tokens, self.cond = [], [], [], [], None
        dec, model = engine.model.decoder, engine.model
        depth_fn, xyz_fn, angle_fn = engine._compute_depth_emb, engine._compute_xyz_emb, engine._compute_angle_emb
        group_fn, players_fn = dec.generate_group, model.get_player_embeddings

        def depth(*a, **k):
            out = depth_fn(*a, **k)
            if self.on:
                self.depth.append(None if out is None else (out[0] if isinstance(out, tuple) else out).detach())
            return out

        def xyz(*a, **k):
            out = xyz_fn(*a, **k)
            if self.on:
                self.xyz.append(None if out is None else out.detach())
            return out

        def angle(*a, **k):
            out = angle_fn(*a, **k)
            if self.on:
                self.angle.append(None if out is None else out.detach())
            return out

        def group(*a, **k):
            tokens, x = group_fn(*a, **k)[:2]
            if self.on:
                self.tokens.append(tokens.detach())
            return tokens, x

        def players(batch):
            out = players_fn(batch)
            if self.on:
                self.cond = out.detach()
            return out

        engine._compute_depth_emb, engine._compute_xyz_emb, engine._compute_angle_emb = depth, xyz, angle
        dec.generate_group, model.get_player_embeddings = group, players

    def sample(self, round_sample, tick, player, k):
        self.depth, self.xyz, self.angle, self.tokens, self.cond = [], [], [], [], None
        self.on = True
        try:
            result = self.engine.predict_at_tick_player_sampled(round_sample, tick, player_idx=player, num_samples=k,
                                                               temperature=donk.TEMPERATURE, top_p=donk.TOP_P)
        finally:
            self.on = False
        if not result["samples"] or len(self.tokens) != self.engine.model_cfg.n_ticks:
            return result, None
        d = self.engine.model_cfg.d_model

        def stack(items):
            return torch.stack([torch.zeros(k, d, device=self.tokens[0].device) if t is None else t.float()
                                for t in items], 1)                           # [K, n_ticks, d]

        inputs = {"start": self.cond[0, -1, player].float().expand(k, -1), "depth": stack(self.depth),
                  "xyz": stack(self.xyz), "angle": stack(self.angle), "tokens": torch.cat(self.tokens, 1)}
        return result, inputs


def judge_samples(result):
    """Index of the kept imagined future, or None. Keeps the closest to the real future among those
    that break no human per-step limit; never keeps one if the real future itself breaks a limit."""
    gt = result.get("gt")
    if not gt or not gt.get("gt_points"):
        return None, None
    start = result["start_pos"]
    mv, tn, pt, _ = donk.path_steps(start, gt["gt_points"], gt["gt_yaw"], gt.get("gt_pitch", []))
    if donk.violation_share(mv, tn, pt) > 0:
        return None, None
    best, best_ade = None, None
    for i, smp in enumerate(result["samples"]):
        if not smp["pred_points"]:
            continue
        mv, tn, pt, _ = donk.path_steps(start, smp["pred_points"], smp["pred_yaw"], smp.get("pred_pitch", []))
        if donk.violation_share(mv, tn, pt) > 0:
            continue
        a = donk.ade(smp["pred_points"], gt["gt_points"], start)
        if best_ade is None or a < best_ade:
            best, best_ade = i, a
    return best, best_ade


def imagine(recorder, cache, chosen, k):
    from data import load_round
    kept, rounds, tried = [], {}, 0
    for file, tick, player in chosen:
        if file not in rounds:
            rounds[file] = load_round(str(cache / file))
        result, inputs = recorder.sample(rounds[file], tick, player, k)
        tried += 1
        if inputs is None:
            continue
        i, a = judge_samples(result)
        if i is None:
            continue
        kept.append({key: v[i].cpu() for key, v in inputs.items()} | {"ade": a})
    return kept, tried


# ---------------------------------------------------------------------------------------- scoring
def free_run(recorder, cache, chosen, k, seed):
    """Free-running futures from each moment: per-moment mean path error and pooled step measures."""
    from data import load_round
    torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    out = {"mean_ade": [], "min_ade": [], "move": [], "turn": [], "pitch": [], "back": []}
    real = {"move": [], "turn": [], "pitch": [], "back": []}
    rounds = {}
    for file, tick, player in chosen:
        if file not in rounds:
            rounds[file] = load_round(str(cache / file))
        torch.manual_seed(seed + tick)
        res = recorder.engine.predict_at_tick_player_sampled(rounds[file], tick, player_idx=player, num_samples=k,
                                                             temperature=donk.TEMPERATURE, top_p=donk.TOP_P)
        gt = res.get("gt")
        if not res["samples"] or not gt or not gt.get("gt_points"):
            out["mean_ade"].append(float("nan")); out["min_ade"].append(float("nan"))
            continue
        start = res["start_pos"]
        for key, v in zip(("move", "turn", "pitch", "back"),
                          donk.path_steps(start, gt["gt_points"], gt["gt_yaw"], gt.get("gt_pitch", []))):
            real[key].extend(v.tolist())
        ades = [donk.ade(s["pred_points"], gt["gt_points"], start) for s in res["samples"]]
        out["mean_ade"].append(float(np.mean(ades))); out["min_ade"].append(float(np.min(ades)))
        for s in res["samples"]:
            if s["pred_points"]:
                for key, v in zip(("move", "turn", "pitch", "back"),
                                  donk.path_steps(start, s["pred_points"], s["pred_yaw"], s.get("pred_pitch", []))):
                    out[key].extend(v.tolist())
    return out, real


def compare(donk_run, base_run, real):
    """Drop moments either model could not score, then apply donk.judge (the fixed rule)."""
    ok = [i for i, (a, b) in enumerate(zip(donk_run["mean_ade"], base_run["mean_ade"]))
          if np.isfinite(a) and np.isfinite(b)]
    per = {}
    for name, run in (("donk", donk_run), ("base", base_run)):
        per[name] = {k: v for k, v in run.items()} | {"mean_ade": [run["mean_ade"][i] for i in ok],
                                                      "min_ade": [run["min_ade"][i] for i in ok]}
    result = donk.judge(per, real)
    result.update(windows=len(ok), mean_ade={n: float(np.mean(per[n]["mean_ade"])) for n in per},
                  min_ade={n: float(np.mean(per[n]["min_ade"])) for n in per})
    return result


def summary(run, real):
    v = donk.violation_share(np.asarray(run["move"]), np.asarray(run["turn"]), np.asarray(run["pitch"]))
    return {"mean_ade": float(np.nanmean(run["mean_ade"])), "violation_share": v,
            "backwards_share": float(np.mean(run["back"])) if run["back"] else float("nan"),
            "move_w1": donk.w1(run["move"], real["move"]), "turn_w1": donk.w1(run["turn"], real["turn"])}


# --------------------------------------------------------------------------------------- learning
def imagined_batch(kept, size, device):
    chosen = random.sample(kept, min(size, len(kept)))
    stack = {key: torch.stack([c[key] for c in chosen]).to(device) for key in ("start", "depth", "xyz", "angle", "tokens")}
    return stack["start"], stack["depth"], stack["xyz"], stack["angle"], stack["tokens"].long()


def learn(model, loras, params, optimizer, training, pool, kept, args):
    from training_data.torch_dataset import pretrain_collate_fn
    log = []
    for step in range(1, args.steps_per_iteration + 1):
        chosen = random.sample(pool, min(args.batch_size, len(pool)))
        batch = donk.to_device(pretrain_collate_fn([training[i] for i in chosen]), args.device)
        b = torch.arange(len(chosen), device=args.device)
        p = batch["target_index"].long()
        labels = batch["label_camera"][b, :, p][:, model.cfg.n_ticks - 1:2 * model.cfg.n_ticks - 1]
        keep = ~donk.step_violations(labels)
        model.decoder.train()
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=args.device, dtype=torch.bfloat16, enabled=args.device == "cuda"):
            nll_real = kl_real = torch.zeros((), device=args.device)
            if keep.any():
                nll_real, kl_real = donk.losses(model, loras, donk.encode(model, batch, b[keep], p[keep]))
            nll_im, kl_im = donk.losses(model, loras, imagined_batch(kept, args.batch_size, args.device))
            objective = nll_real + args.imagined_weight * nll_im + args.kl * (kl_real + kl_im)
        if not torch.isfinite(objective):
            raise RuntimeError("Nonfinite loss; stopping before saving a corrupt model")
        objective.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        optimizer.step()
        model.decoder.eval()
        if step == 1 or step % 25 == 0:
            log.append(dict(step=step, nll_real=float(nll_real), nll_imagined=float(nll_im),
                            kl=float(kl_real + kl_im)))
            print("TRAIN", json.dumps(log[-1]), flush=True)
    return log


# -------------------------------------------------------------------------------------------- run
def run(args):
    from data import Windows
    from prediction_engine import PredictionEngine
    from training_data.torch_dataset import pretrain_collate_fn  # noqa: F401  (fail early if missing)
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    started = time.time()
    args.out.mkdir(parents=True, exist_ok=True)
    training, development = Windows(args.cache, "train"), Windows(args.cache, "dev")
    pool, test = split_training(training)
    for i in pool + test:
        if training.index[i][0]["match_id"] in HOLDOUTS:
            raise ValueError("A held-back match reached the data")
    pool_moments = moments(training, pool)
    test_moments = moments(training, test)
    dev_a = moments(development, donk.donk_indices(development, "A"))
    dev_a = random.Random(1).sample(dev_a, min(args.select_moments, len(dev_a)))
    engine = PredictionEngine(str(args.csnet / "config/pretrain-a100-pro.yaml"), str(args.checkpoint), device=args.device,
                              maps_dir=str(args.csnet / "maps/optimized_obj_files"))
    model = engine.model.eval().requires_grad_(False)
    loras = donk.add_lora(model.decoder, args.rank)
    params = [prm for lora in loras for prm in lora.parameters()]
    for prm in params:
        prm.requires_grad_(True)
    optimizer = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
    recorder = Recorder(engine)
    print(f"STARTED pool_windows={len(pool)} test_C_windows={len(test)} dev_A_moments={len(dev_a)} "
          f"trainable_parameters={sum(prm.numel() for prm in params)}", flush=True)

    donk.set_lora(loras, False)
    base_dev, real_dev = free_run(recorder, args.cache, dev_a, args.samples, seed=11)
    donk.set_lora(loras, True)
    base_summary = summary(base_dev, real_dev)
    print("SELECT", json.dumps(dict(iteration=0, model="base", **base_summary)), flush=True)
    iterations = [dict(iteration=0, **base_summary, kept=0, tried=0)]
    best, best_score = 0, base_summary.get("selection_score", base_summary["mean_ade"])
    torch.save({"lora": [lora.state_dict() for lora in loras], "iteration": 0}, args.out / "best_lora.pt")
    kept_all = []
    for it in range(1, args.iterations + 1):
        if time.time() - started > args.budget_minutes * 60:
            print("BUDGET_REACHED", flush=True)
            break
        chosen = random.sample(pool_moments, min(args.moments_per_iteration, len(pool_moments)))
        t0 = time.time()
        kept, tried = imagine(recorder, args.cache, chosen, args.samples)
        kept_all = (kept_all + kept)[-args.keep_last:]
        print(f"IMAGINED iteration={it} tried={tried} kept={len(kept)} seconds={time.time() - t0:.0f}", flush=True)
        if not kept_all:
            raise RuntimeError("No imagined future passed the judge")
        log = learn(model, loras, params, optimizer, training, pool, kept_all, args)
        run_dev, _ = free_run(recorder, args.cache, dev_a, args.samples, seed=11)
        s = summary(run_dev, real_dev)
        ok = s["violation_share"] <= base_summary["violation_share"]
        print("SELECT", json.dumps(dict(iteration=it, model=donk.PLAYER, limits_ok=ok, **s)), flush=True)
        iterations.append(dict(iteration=it, **s, limits_ok=ok, kept=len(kept), tried=tried, train=log,
                               kept_mean_ade=float(np.mean([c["ade"] for c in kept])) if kept else None))
        score = s.get("selection_score", s["mean_ade"])
        if ok and score < best_score:
            best, best_score = it, score
            torch.save({"lora": [lora.state_dict() for lora in loras], "iteration": it}, args.out / "best_lora.pt")
        write_json(args.out / "imagination.json", dict(iterations=iterations, best_iteration=best,
                   settings={k: str(v) for k, v in vars(args).items()}))

    record = dict(player=donk.PLAYER, experiment="player model, self-trained on imagined play (clone-model/imagine.py)",
                  csnet_revision=CSNET_REVISION, base_checkpoint_sha256=sha256(args.checkpoint),
                  manifest_sha256=sha256(args.cache / "manifest.json"), iterations=iterations, best_iteration=best,
                  settings={k: str(v) for k, v in vars(args).items()}, test_C_windows=len(test),
                  pool_windows=len(pool), minutes_before_test=round((time.time() - started) / 60, 1))
    if best == 0:
        record["test"] = "not run: no iteration beat the base on dev-A, so there is nothing to test"
        record["pass"] = False
        write_json(args.out / "imagination.json", record)
        print("NO_IMPROVEMENT test-C not used", flush=True)
        return
    saved = torch.load(args.out / "best_lora.pt", map_location="cpu")
    for lora, state in zip(loras, saved["lora"]):
        lora.load_state_dict(state)
    if getattr(args, "dev_only", False):
        torch.save({"lora": saved["lora"], "iteration": best, "rank": args.rank, "player": donk.PLAYER}, args.out / "imagined_lora.pt")
        record.update(player=donk.PLAYER, test="not run: development experiment; consumed final sets remain untouched", deployed=False)
        write_json(args.out / "imagination.json", record)
        print("DEVELOPMENT_COMPLETE player=" + donk.PLAYER, flush=True)
        return
    donk.set_lora(loras, False)
    base_test, real_test = free_run(recorder, args.cache, test_moments, args.samples, seed=7)
    donk.set_lora(loras, True)
    donk_test, _ = free_run(recorder, args.cache, test_moments, args.samples, seed=7)
    result = compare(donk_test, base_test, real_test)
    result.update(split="test-C (donk training rounds with round_id % 6 == 3, never trained on here)",
                  interpretation="Free-running 4-second futures sampled by CS-NET's own engine. Movement and "
                                 "view only; not combat, not in CS2, not a people panel.")
    record["test"] = result
    record["pass"] = result["pass"]
    record["minutes_total"] = round((time.time() - started) / 60, 1)
    torch.save({"lora": saved["lora"], "iteration": best, "rank": args.rank}, args.out / "imagined_lora.pt")
    write_json(args.out / "imagination.json", record)
    print("TEST_COMPLETE", json.dumps({k: v for k, v in result.items() if k != "P2_behaviour"}), flush=True)
    print("BEHAVIOUR", json.dumps(result["P2_behaviour"]), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["run"])
    ap.add_argument("--csnet", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    ap.add_argument("--iterations", type=int, default=4)
    ap.add_argument("--moments-per-iteration", type=int, default=200)
    ap.add_argument("--keep-last", type=int, default=600, help="imagined futures kept across iterations")
    ap.add_argument("--steps-per-iteration", type=int, default=100)
    ap.add_argument("--select-moments", type=int, default=80, help="dev-A moments used to pick the iteration")
    ap.add_argument("--samples", type=int, default=donk.SAMPLES)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--kl", type=float, default=0.1)
    ap.add_argument("--imagined-weight", type=float, default=1.0)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--budget-minutes", type=float, default=60, help="no new iteration starts after this")
    args = ap.parse_args()
    configure(args.csnet)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested a GPU, but no CUDA device is connected")
    torch.set_num_threads(4)
    run(args)


if __name__ == "__main__":
    main()
