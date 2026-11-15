"""Reproduce Round 4's development numbers on this machine, to check the local setup.

Uses imagine.free_run with the same dev-A moments (Random(1), 32), seed 11, 8 samples, temperature 1.0,
top_p 0.9, as round4.py/imagine.run. Reports mean path error (ADE) for the base model and one adapter.
Round 4's published values (results/round4-development.json): donk base 133.200 -> selected 129.413,
broky base 125.357 -> selected 119.798.

    python feasibility_reproduce.py --csnet CSNET --cache CACHE --checkpoint BASE --lora LORA --player donk
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
import imagine
from common import configure
from round4_review import load_states, use


def main():
    p = argparse.ArgumentParser()
    for name in ("csnet", "cache", "checkpoint", "lora"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--player", choices=["donk", "broky"], required=True)
    p.add_argument("--moments", type=int, default=32)
    p.add_argument("--device", default="cuda")
    args = p.parse_args()
    configure(args.csnet)
    from data import Windows
    from prediction_engine import PredictionEngine
    donk.PLAYER = args.player
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    development = Windows(args.cache, "dev")
    dev_a = imagine.moments(development, donk.donk_indices(development, "A"))
    dev_a = random.Random(1).sample(dev_a, min(args.moments, len(dev_a)))
    engine = PredictionEngine(str(args.csnet / "config/pretrain-a100-pro.yaml"), str(args.checkpoint), device=args.device,
                              maps_dir=str(args.csnet / "maps/optimized_obj_files"))
    engine.model.eval().requires_grad_(False)
    loras = donk.add_lora(engine.model.decoder, 16)
    states = load_states(args.lora, args.player, 16, loras)
    recorder = imagine.Recorder(engine)
    out = dict(player=args.player, moments=len(dev_a), adapter_iteration=states["iteration"])
    for label, s in (("base", None), ("adapter", states["states"])):
        use(loras, s)
        t = time.perf_counter()
        run, real = imagine.free_run(recorder, args.cache, dev_a, donk.SAMPLES, seed=11)
        summary = imagine.summary(run, real)
        out[label] = dict(mean_ade=round(summary["mean_ade"], 3), turn_w1=round(summary["turn_w1"], 3),
                          move_w1=round(summary["move_w1"], 3), seconds=round(time.perf_counter() - t))
        print(label, out[label], flush=True)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
