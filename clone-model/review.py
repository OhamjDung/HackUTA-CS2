"""Export deterministic development examples for offline review, without promoting routes.

Uses the same pinned CS-NET PredictionEngine and adapter checks as the identity test.
This is a small diagnostic selection, never a replacement for held-out validation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
import torch

from common import HOLDOUTS, sha256, write_json
from data import load_round
from validate import load_evaluator


def trace_payload(result, prefix):
    """Keep native path length and heading-used-for-step values; do not invent late steps."""
    points = result[f"{prefix}_points"]
    names = ("yaw", "pitch", "alive", "firing")
    values = {name: result[f"{prefix}_{name}"] for name in names}
    if any(len(v) != len(points) for v in values.values()):
        raise ValueError("Trajectory channels have different lengths")
    xyz = np.asarray(points, dtype=float).reshape(-1, 3)
    if not np.isfinite(xyz).all() or any(not np.isfinite(v).all() for v in values.values()):
        raise ValueError("Nonfinite review trajectory")
    return dict(path=[[round((i+1)*.25, 3), *map(float, p)] for i, p in enumerate(xyz)],
        yaw_degrees=list(map(float, values["yaw"])), pitch_degrees=list(map(float, values["pitch"])),
        alive_values=list(map(float, values["alive"])), firing_values=list(map(float, values["firing"])),
        end_stopped_at=result.get("end_stopped_at"))


def review_cases(manifest, cache, per_player):
    if per_player < 1:
        raise ValueError("At least one example per player is required")
    counts = Counter()
    for entry in manifest["rounds"]:
        if entry["split"] != "dev" or counts[entry["player"]] >= per_player:
            continue
        if entry["match_id"] in HOLDOUTS:
            raise ValueError("A held-out match cannot be a development review example")
        sample = load_round(str(cache / entry["file"]))
        p, ticks = entry["target_index"], entry["ticks"]
        # Same policy for every round: midpoint first, then the early anchor if already dead.
        candidates = [min(ticks // 2, ticks-17), 15]
        tick = next((t for t in candidates if t >= 15 and t+16 < ticks and sample["player_alive_mask"][t, p]), None)
        if tick is not None:
            counts[entry["player"]] += 1
            yield entry, sample, tick
    if any(counts[name] == 0 for name in manifest["players"]):
        raise ValueError("No eligible development examples for one or more players")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csnet", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="Review JSON file, outside playable clones")
    parser.add_argument("--per-player", type=int, default=4)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    args = parser.parse_args()
    torch.set_num_threads(4)
    manifest, saved, engine, adapter = load_evaluator(args.csnet, args.cache, args.checkpoint, args.adapter, args.device)
    cases = []
    for entry, sample, tick in review_cases(manifest, args.cache, args.per_player):
        p, own = entry["target_index"], entry["identity"]
        alternatives = [v for v in saved["registry"].values() if v != own]
        if len(alternatives) != 1:
            raise ValueError("This two-player review requires exactly one other identity")
        predictions = {}
        for label, identity in (("own", own), ("other", alternatives[0]), ("base", 0)):
            ids = torch.zeros((1, 10), device=args.device, dtype=torch.long)
            ids[0, p] = identity
            hook = engine.model.temporal.register_forward_hook(adapter.temporal_hook(ids))
            try:
                result = engine.predict_at_tick_player_sampled(sample, tick, player_idx=p,
                    num_samples=1, temperature=0, metric=None)
            finally:
                hook.remove()
            predictions[label] = dict(identity_id=identity, **trace_payload(result["samples"][0], "pred"))
        gt = result.get("gt")
        if not gt or not gt["gt_points"]:
            raise ValueError("Review example has no actual future path")
        cases.append(dict(player=entry["player"], steam_id=manifest["players"][entry["player"]],
            match_id=entry["match_id"], round_id=entry["round_id"], side=sample["meta"]["teams"][p],
            context_tick=tick, seconds_into_round=float(sample["round_seconds"][tick]),
            start_position=result["start_pos"], actual=trace_payload(gt, "gt"), predictions=predictions))
        print(f"EXPORTED_REVIEW {entry['player']} {entry['match_id']} round={entry['round_id']} tick={tick}", flush=True)
    write_json(args.out, dict(format="cs2.clone.review.v1", split="dev", deployed=False,
        manual_review_required=True, identity_quality="not_established", selected_step=saved["step"],
        map="de_mirage", interval_seconds=.25, position_units="Source game units",
        angles="Upstream heading used for the step, not a guaranteed post-step camera orientation",
        selection="First eligible development rounds per player; midpoint alive anchor, else tick 15",
        interpretation="Diagnostic samples, not a full validation or recorded CS2 bot match. Paths have not been collision-approved.",
        source=dict(csnet_revision=saved["csnet_revision"], adapter_sha256=sha256(args.adapter),
            base_checkpoint_sha256=saved["base_checkpoint_sha256"], manifest_sha256=saved["manifest_sha256"]),
        cases=cases))
    print(f"REVIEW_EXPORT_COMPLETE cases={len(cases)} out={args.out}", flush=True)


if __name__ == "__main__":
    main()
