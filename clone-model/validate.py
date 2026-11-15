"""Free-running identity-swap test through CS-NET's raycasting prediction engine.

No future target coordinates/angles are fed into generation. Short predictions are extended
with their final point, so predicting an early stop cannot hide later path error.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from common import CSNET_REVISION, HOLDOUTS, configure, write_json, sha256
from data import load_round
from identity import PlayerAdapter


def path_metrics(predicted, actual, start):
    actual = np.asarray(actual, dtype=float)
    if actual.ndim != 2 or actual.shape[1] != 3 or len(actual) == 0:
        raise ValueError("No valid ground-truth path")
    predicted = np.asarray(predicted or [start], dtype=float).reshape(-1, 3)
    if not np.isfinite(predicted).all() or not np.isfinite(actual).all():
        raise ValueError("Nonfinite trajectory")
    predicted = predicted[np.minimum(np.arange(len(actual)), len(predicted)-1)]
    distances = np.linalg.norm(predicted - actual, axis=1)
    pred_steps = np.linalg.norm(np.diff(np.vstack([start, predicted]), axis=0), axis=1)
    true_steps = np.linalg.norm(np.diff(np.vstack([start, actual]), axis=0), axis=1)
    return dict(ade=float(distances.mean()), fde=float(distances[-1]),
        stationary_share_error=float(abs(np.mean(pred_steps < 1) - np.mean(true_steps < 1))),
        mean_speed_error=float(abs(pred_steps.mean() - true_steps.mean()) / .25))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csnet", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--split", default="test", choices=["test", "dev"])
    args = parser.parse_args()
    configure(args.csnet)
    from prediction_engine import PredictionEngine
    torch.set_num_threads(4)
    manifest = json.loads((args.cache / "manifest.json").read_text())
    saved = torch.load(args.adapter, map_location="cpu", weights_only=True)
    if saved["registry"] != manifest["registry"] or saved["csnet_revision"] != CSNET_REVISION:
        raise ValueError("Adapter identity registry or upstream revision mismatch")
    if saved["base_checkpoint_sha256"] != sha256(args.checkpoint) or saved["manifest_sha256"] != sha256(args.cache / "manifest.json"):
        raise ValueError("Base checkpoint or data manifest differs from the training run")
    engine = PredictionEngine(str(args.csnet / "config/pretrain-a100-pro.yaml"), str(args.checkpoint),
        device=args.device, maps_dir=str(args.csnet / "maps/optimized_obj_files"))
    adapter = PlayerAdapter(saved["registry"], saved["d_model"], saved["d_identity"]).to(args.device).eval()
    adapter.load_state_dict(saved["adapter"], strict=True)
    selected = [e for e in manifest["rounds"] if e["split"] == args.split]
    if args.split == "test" and any(e["match_id"] not in HOLDOUTS for e in selected):
        raise ValueError("Test split contains a non-held-out match")
    records = []
    for entry in selected:
        sample = load_round(str(args.cache / entry["file"]))
        p, own = entry["target_index"], entry["identity"]
        candidates = [15, min(entry["ticks"] // 2, entry["ticks"] - 17)]
        for tick in sorted(set(candidates)):
            if tick < 15 or tick + 16 >= entry["ticks"] or not sample["player_alive_mask"][tick, p]:
                continue
            for label, identity in (("own", own), ("other", 3-own), ("base", 0)):
                ids = torch.zeros((1, 10), device=args.device, dtype=torch.long)
                ids[0, p] = identity
                hook = engine.model.temporal.register_forward_hook(adapter.temporal_hook(ids))
                try:
                    # temperature=0 is deterministic greedy generation, not best-of-many sampling.
                    result = engine.predict_at_tick_player_sampled(sample, tick, player_idx=p,
                        num_samples=1, temperature=0, metric=None)
                finally:
                    hook.remove()
                gt = result.get("gt")
                if not gt or not gt["gt_points"]:
                    continue
                metrics = path_metrics(result["samples"][0]["pred_points"], gt["gt_points"], result["start_pos"])
                records.append(dict(player=entry["player"], match_id=entry["match_id"], round_id=entry["round_id"],
                    tick=tick, identity=label, **metrics))
            print(f"VALIDATED {entry['player']} {entry['match_id']} round={entry['round_id']} tick={tick}", flush=True)
            write_json(args.out / "validation-progress.json", dict(windows=len(records)//3, latest=records[-3:]))
    grouped = defaultdict(list)
    for record in records:
        grouped[(record["player"], record["identity"])].append(record)
    summary = {}
    for name in manifest["players"]:
        summary[name] = {}
        for label in ("own", "other", "base"):
            group = grouped[(name, label)]
            if not group:
                raise ValueError(f"No validation samples for {name}/{label}")
            summary[name][label] = {key: float(np.mean([r[key] for r in group]))
                for key in ("ade", "fde", "stationary_share_error", "mean_speed_error")}
            summary[name][label]["windows"] = len(group)
        summary[name]["identity_test_pass"] = (
            summary[name]["own"]["ade"] < summary[name]["base"]["ade"] and
            summary[name]["own"]["ade"] < summary[name]["other"]["ade"])
    write_json(args.out / "validation.json", dict(split=args.split, selected_step=saved["step"],
        summary=summary, records=records, interpretation="Movement tests only; not proof of identical player quirks or combat skill."))
    print("VALIDATION_COMPLETE", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
