"""Export Round 4 LoRA paths as a `cs2.clone.review.v1` file, for the map check and the candidate converter.

`review.py` loads the older identity (FiLM) adapter. This file does the same job for the Round 4 decoder
LoRA adapters (`imagined_lora.pt`, saved by `imagine.run`), using the same loading path as training:
CS-NET's PredictionEngine, `donk.add_lora`, then the saved LoRA states. Nothing here promotes a route.

    python round4_review.py --csnet CSNET --cache CACHE --checkpoint BASE \\
        --donk RUNS/v1-donk/imagined_lora.pt --broky RUNS/v1-broky/imagined_lora.pt --out data/reviews/round4.json

Each case is one development round of one player, at the earliest moment the model can predict from
(tick 15: 3.75 s after the round goes live, because it needs 16 steps of context). Traces:
  own    the player's own Round 4 adapter
  other  the other player's Round 4 adapter, same moment and seed
  base   CS-NET with the adapters switched off, same moment and seed
Each trace is the medoid of `--samples` sampled futures (the sample closest to the others), so no
real future path is used to choose it. Sampling settings are the ones Round 4 was judged with.

Refuses to write unless every adapter loads strictly, names the expected player and rank, and changes
the model's output: at least one case must have own != base.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import torch

import donk
from common import CSNET_REVISION, HOLDOUTS, configure, sha256, write_json
from data import load_round
from review import trace_payload

CONTEXT_TICK = 15
HORIZON = 16


def load_states(path: Path, player: str, rank: int, loras) -> dict:
    saved = torch.load(path, map_location="cpu", weights_only=True)
    if saved.get("player") != player or saved.get("rank") != rank:
        raise ValueError(f"{path} is for player {saved.get('player')!r} rank {saved.get('rank')!r}, "
                         f"expected {player!r} rank {rank}")
    states = saved["lora"]
    if len(states) != len(loras):
        raise ValueError(f"{path} has {len(states)} LoRA states; the decoder has {len(loras)} adapters")
    tensors = [t for s in states for t in s.values()]
    if any(not torch.isfinite(t).all() for t in tensors):
        raise ValueError(f"{path} has nonfinite weights")
    return dict(states=states, iteration=saved["iteration"], sha256=sha256(path),
                tensors=len(tensors), parameters=int(sum(t.numel() for t in tensors)))


def use(loras, states) -> None:
    """Switch the decoder to one adapter (strict load), or to the base model when states is None."""
    donk.set_lora(loras, states is not None)
    if states is not None:
        for lora, state in zip(loras, states):
            lora.load_state_dict(state, strict=True)


def medoid(samples: list[dict]) -> int:
    """Index of the sampled future closest on average to the others. Uses no real path."""
    paths = [np.asarray(s["pred_points"], dtype=float).reshape(-1, 3) for s in samples]
    usable = [i for i, p in enumerate(paths) if len(p)]
    if not usable:
        raise ValueError("No sampled future has a path")
    def distance(a, b):
        n = min(len(a), len(b))
        return float(np.linalg.norm(a[:n] - b[:n], axis=1).mean())
    return min(usable, key=lambda i: sum(distance(paths[i], paths[j]) for j in usable))


def eligible(manifest, cache, per_player):
    """Development rounds, never a held-out match, where the player is alive through the horizon."""
    counts = {}
    for entry in manifest["rounds"]:
        player = entry["player"]
        if entry["split"] != "dev" or counts.get(player, 0) >= per_player:
            continue
        if entry["match_id"] in HOLDOUTS:
            raise ValueError("A held-out match cannot be a development review example")
        if entry["ticks"] <= CONTEXT_TICK + HORIZON:
            continue
        sample = load_round(str(cache / entry["file"]))
        p = entry["target_index"]
        if not sample["player_alive_mask"][CONTEXT_TICK:CONTEXT_TICK + HORIZON + 1, p].all():
            continue
        counts[player] = counts.get(player, 0) + 1
        yield entry, sample


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("csnet", "cache", "checkpoint", "donk", "broky", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--per-player", type=int, default=12)
    parser.add_argument("--samples", type=int, default=donk.SAMPLES)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    args = parser.parse_args()
    configure(args.csnet)
    from prediction_engine import PredictionEngine
    import json
    torch.set_num_threads(4)
    manifest = json.loads((args.cache / "manifest.json").read_text())
    engine = PredictionEngine(str(args.csnet / "config/pretrain-a100-pro.yaml"), str(args.checkpoint),
                              device=args.device, maps_dir=str(args.csnet / "maps/optimized_obj_files"))
    engine.model.eval().requires_grad_(False)
    loras = donk.add_lora(engine.model.decoder, args.rank)
    adapters = {name: load_states(getattr(args, name), name, args.rank, loras) for name in ("donk", "broky")}
    for name, a in adapters.items():
        print(f"ADAPTER {name} iteration={a['iteration']} tensors={a['tensors']} parameters={a['parameters']} "
              f"sha256={a['sha256']}", flush=True)

    cases, differs = [], 0
    for entry, sample in eligible(manifest, args.cache, args.per_player):
        player, p = entry["player"], entry["target_index"]
        other = next(n for n in adapters if n != player)
        predictions, result = {}, None
        for label, name in (("own", player), ("other", other), ("base", None)):
            use(loras, adapters[name]["states"] if name else None)
            seed = args.seed + entry["round_id"]
            torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
            result = engine.predict_at_tick_player_sampled(sample, CONTEXT_TICK, player_idx=p, num_samples=args.samples,
                                                           temperature=donk.TEMPERATURE, top_p=donk.TOP_P, metric=None)
            chosen = result["samples"][medoid(result["samples"])]
            predictions[label] = dict(identity_id=name or "base", adapter_sha256=adapters[name]["sha256"] if name else None,
                                      **trace_payload(chosen, "pred"))
        gt = result.get("gt")
        if not gt or not gt["gt_points"]:
            raise ValueError("Review example has no actual future path")
        differs += predictions["own"]["path"] != predictions["base"]["path"]
        cases.append(dict(player=player, steam_id=manifest["players"][player], match_id=entry["match_id"],
                          round_id=entry["round_id"], side=sample["meta"]["teams"][p], context_tick=CONTEXT_TICK,
                          seconds_into_round=float(sample["round_seconds"][CONTEXT_TICK]),
                          start_position=result["start_pos"], actual=trace_payload(gt, "gt"), predictions=predictions))
        print(f"EXPORTED_REVIEW {player} {entry['match_id']} round={entry['round_id']} "
              f"own_differs_from_base={predictions['own']['path'] != predictions['base']['path']}", flush=True)
    use(loras, None)
    if not cases:
        raise ValueError("No eligible development rounds")
    if not differs:
        raise ValueError("The adapters did not change any path: own equals base in every case. Not written.")
    write_json(args.out, dict(
        format="cs2.clone.review.v1", split="dev", deployed=False, manual_review_required=True,
        identity_quality="round4 development candidate, not promoted (results/round4-development.md)",
        selected_step={n: a["iteration"] for n, a in adapters.items()},
        map="de_mirage", interval_seconds=.25, position_units="Source game units",
        angles="Upstream heading used for the step, not a guaranteed post-step camera orientation",
        selection=f"Up to {args.per_player} development rounds per player, tick {CONTEXT_TICK}, alive through the horizon; "
                  f"medoid of {args.samples} sampled futures (temperature {donk.TEMPERATURE}, top_p {donk.TOP_P})",
        interpretation="Round 4 decoder LoRA adapters. own: the player's adapter; other: the other player's adapter; "
                       "base: adapters off. Movement and view only. Paths have not been collision-approved.",
        model=dict(kind="decoder LoRA", rank=args.rank, release="round4-development-v1",
                   adapters={n: {k: a[k] for k in ("iteration", "sha256", "tensors", "parameters")}
                             for n, a in adapters.items()},
                   cases_where_own_differs_from_base=int(differs), cases=len(cases)),
        source=dict(csnet_revision=CSNET_REVISION, adapter_sha256={n: a["sha256"] for n, a in adapters.items()},
                    base_checkpoint_sha256=sha256(args.checkpoint),
                    manifest_sha256=sha256(args.cache / "manifest.json")),
        cases=cases))
    print(f"REVIEW_EXPORT_COMPLETE cases={len(cases)} own_differs={differs} out={args.out}", flush=True)


if __name__ == "__main__":
    main()
