"""Latency of one Round 4 prediction under cheap speed-ups: adapter merged into the weights, fp16 autocast.

Also checks that merging does not change the output (greedy decoding, same input).

    python feasibility_speedups.py --csnet CSNET --cache CACHE --checkpoint BASE --donk LORA --device cuda
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np
import torch

import donk
from common import configure
from data import load_round
from round4_review import CONTEXT_TICK, load_states, use


def main():
    p = argparse.ArgumentParser()
    for name in ("csnet", "cache", "checkpoint", "donk"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--device", default="cuda")
    p.add_argument("--repeats", type=int, default=5)
    args = p.parse_args()
    configure(args.csnet)
    from prediction_engine import PredictionEngine
    torch.set_num_threads(4)
    engine = PredictionEngine(str(args.csnet / "config/pretrain-a100-pro.yaml"), str(args.checkpoint),
                              device=args.device, maps_dir=str(args.csnet / "maps/optimized_obj_files"))
    manifest = json.loads((args.cache / "manifest.json").read_text())
    entry = next(e for e in manifest["rounds"] if e["player"] == "donk" and e["split"] == "dev" and e["ticks"] > 40)
    sample = load_round(str(args.cache / entry["file"]))
    out = {"device": args.device}

    def predict(k=1, temperature=donk.TEMPERATURE):
        return engine.predict_at_tick_player_sampled(sample, CONTEXT_TICK, player_idx=entry["target_index"], num_samples=k,
                                                     temperature=temperature, top_p=donk.TOP_P, metric=None)

    def timed(label, k=1, autocast=False):
        def run():
            if autocast:
                with torch.autocast(args.device, dtype=torch.float16 if args.device == "cuda" else torch.bfloat16):
                    return predict(k)
            return predict(k)
        run()
        times = []
        for _ in range(args.repeats):
            if args.device == "cuda":
                torch.cuda.synchronize()
            t = time.perf_counter(); run()
            if args.device == "cuda":
                torch.cuda.synchronize()
            times.append(time.perf_counter() - t)
        out[label] = dict(median_s=round(statistics.median(times), 2), min_s=round(min(times), 2), n=len(times))
        print(label, out[label], flush=True)

    timed("base_no_adapter_samples1")
    loras = donk.add_lora(engine.model.decoder, 16)
    use(loras, load_states(args.donk, "donk", 16, loras)["states"])
    unmerged = predict(1, 0)["samples"][0]["pred_points"]
    timed("adapter_unmerged_samples1")
    donk.merge_lora(engine.model.decoder)
    merged = predict(1, 0)["samples"][0]["pred_points"]
    a, b = np.asarray(unmerged).reshape(-1, 3), np.asarray(merged).reshape(-1, 3)
    n = min(len(a), len(b))
    out["merge_changes_greedy_path_mean_units"] = round(float(np.linalg.norm(a[:n] - b[:n], axis=1).mean()), 3) if n else None
    timed("adapter_merged_samples1")
    timed("adapter_merged_samples8", k=8)
    timed("adapter_merged_fp16_samples1", autocast=True)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
