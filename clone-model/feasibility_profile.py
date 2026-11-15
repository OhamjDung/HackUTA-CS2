"""Where one Round 4 prediction spends its time (cProfile), and the cost of the wall-depth input, timed twice.

    python feasibility_profile.py --csnet CSNET --cache CACHE --checkpoint BASE --donk LORA --device cuda
"""
from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import time
from pathlib import Path

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
    args = p.parse_args()
    configure(args.csnet)
    from prediction_engine import PredictionEngine
    torch.set_num_threads(4)
    engine = PredictionEngine(str(args.csnet / "config/pretrain-a100-pro.yaml"), str(args.checkpoint),
                              device=args.device, maps_dir=str(args.csnet / "maps/optimized_obj_files"))
    loras = donk.add_lora(engine.model.decoder, 16)
    use(loras, load_states(args.donk, "donk", 16, loras)["states"])
    manifest = json.loads((args.cache / "manifest.json").read_text())
    entry = next(e for e in manifest["rounds"] if e["player"] == "donk" and e["split"] == "dev" and e["ticks"] > 40)
    sample = load_round(str(args.cache / entry["file"]))

    def predict():
        return engine.predict_at_tick_player_sampled(sample, CONTEXT_TICK, player_idx=entry["target_index"], num_samples=1,
                                                     temperature=donk.TEMPERATURE, top_p=donk.TOP_P, metric=None)
    predict()
    prof = cProfile.Profile()
    t = time.perf_counter()
    prof.enable(); predict(); prof.disable()
    print(f"PREDICTION_SECONDS {time.perf_counter() - t:.2f}")
    s = io.StringIO()
    pstats.Stats(prof, stream=s).sort_stats("cumulative").print_stats(28)
    print(s.getvalue())
    s = io.StringIO()
    pstats.Stats(prof, stream=s).sort_stats("tottime").print_stats(15)
    print(s.getvalue())


if __name__ == "__main__":
    main()
