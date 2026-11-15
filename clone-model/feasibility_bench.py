"""Measure what running the Round 4 model inside a live match would cost on this machine.

    python feasibility_bench.py --csnet CSNET --cache CACHE --checkpoint BASE \\
        --donk RUNS/v1-donk/imagined_lora.pt --broky RUNS/v1-broky/imagined_lora.pt \\
        --device cuda --out results.json

Measures, for one device: model load time and memory, whether the adapters load and change the output,
latency of one prediction (CS-NET's own sampled predictor, 1 and 8 samples), and the cost of building the
model's input features (wall-depth rays) for one round. Prints one JSON object.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np
import psutil
import torch

import donk
from common import configure
from data import load_round
from round4_review import CONTEXT_TICK, load_states, use

PROC = psutil.Process()


def mem() -> dict:
    out = dict(process_rss_mib=round(PROC.memory_info().rss / 2**20),
               system_free_mib=round(psutil.virtual_memory().available / 2**20))
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        out.update(cuda_allocated_mib=round(torch.cuda.memory_allocated() / 2**20),
                   cuda_peak_mib=round(torch.cuda.max_memory_allocated() / 2**20),
                   gpu_free_mib=round(free / 2**20), gpu_total_mib=round(total / 2**20))
    return out


def sync(device):
    if device == "cuda":
        torch.cuda.synchronize()


def timed(fn, device, repeats):
    times = []
    for _ in range(repeats):
        sync(device)
        t = time.perf_counter()
        fn()
        sync(device)
        times.append((time.perf_counter() - t) * 1000)
    return dict(median_ms=round(statistics.median(times), 1), p90_ms=round(sorted(times)[int(.9 * (len(times) - 1))], 1),
                min_ms=round(min(times), 1), max_ms=round(max(times), 1), n=len(times))


def main():
    p = argparse.ArgumentParser()
    for name in ("csnet", "cache", "checkpoint", "donk", "broky", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    p.add_argument("--repeats", type=int, default=10)
    args = p.parse_args()
    configure(args.csnet)
    from prediction_engine import PredictionEngine
    torch.set_num_threads(4)
    result = dict(device=args.device, torch=torch.__version__,
                  gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                  cpu_threads=torch.get_num_threads(), before_load=mem())

    t = time.perf_counter()
    engine = PredictionEngine(str(args.csnet / "config/pretrain-a100-pro.yaml"), str(args.checkpoint),
                              device=args.device, maps_dir=str(args.csnet / "maps/optimized_obj_files"))
    engine.model.eval().requires_grad_(False)
    loras = donk.add_lora(engine.model.decoder, 16)
    adapters = {n: load_states(getattr(args, n), n, 16, loras) for n in ("donk", "broky")}
    result["load_seconds"] = round(time.perf_counter() - t, 1)
    result["model_parameters"] = int(sum(x.numel() for x in engine.model.parameters()))
    result["adapters"] = {n: {k: a[k] for k in ("iteration", "tensors", "parameters", "sha256")} for n, a in adapters.items()}
    result["after_load"] = mem()

    manifest = json.loads((args.cache / "manifest.json").read_text())
    entry = next(e for e in manifest["rounds"] if e["player"] == "donk" and e["split"] == "dev" and e["ticks"] > 40)
    sample = load_round(str(args.cache / entry["file"]))
    pidx = entry["target_index"]
    result["round"] = dict(file=entry["file"], ticks=entry["ticks"])

    def predict(k, temperature=donk.TEMPERATURE):
        return engine.predict_at_tick_player_sampled(sample, CONTEXT_TICK, player_idx=pidx, num_samples=k,
                                                     temperature=temperature, top_p=donk.TOP_P, metric=None)

    # Do the adapters change the output? Greedy decoding (temperature 0) removes sampling noise.
    use(loras, None); base = predict(1, 0)["samples"][0]["pred_points"]
    use(loras, adapters["donk"]["states"]); own = predict(1, 0)["samples"][0]["pred_points"]
    use(loras, adapters["broky"]["states"]); other = predict(1, 0)["samples"][0]["pred_points"]
    def gap(a, b):
        a, b = np.asarray(a).reshape(-1, 3), np.asarray(b).reshape(-1, 3)
        n = min(len(a), len(b))
        return round(float(np.linalg.norm(a[:n] - b[:n], axis=1).mean()), 1) if n else None
    result["adapter_effect_greedy"] = dict(own_vs_base_mean_units=gap(own, base), other_vs_base_mean_units=gap(other, base),
                                           own_vs_other_mean_units=gap(own, other), path_points=len(np.asarray(own).reshape(-1, 3)))

    use(loras, adapters["donk"]["states"])
    predict(1)  # warm-up
    result["latency_one_prediction"] = {f"samples_{k}": timed(lambda: predict(k), args.device, args.repeats) for k in (1, 8)}
    result["after_predict"] = mem()

    # Cost of the model's inputs: CS-NET's round processor with wall-depth rays, for one parsed round.
    import gzip
    from create_training_data import _convert_inventory_indices
    from replay_tool.filter import filter_data
    from training_data.map_loader import get_map_geometry
    from training_data.round_processor import process_round
    src = Path(__file__).resolve().parents[1] / "data/round4/rounds/round_json" / f"{entry['match_id']}.json.gz"
    if src.is_file():
        data = json.load(gzip.open(src, "rt", encoding="utf-8"))
        filter_data(data); _convert_inventory_indices(data)
        rnd = next(r for r in data["rounds"] if int(r["id"]) == entry["round_id"])
        rnd["map"] = "de_mirage"
        geometry = get_map_geometry("de_mirage", args.csnet / "maps/optimized_obj_files")
        t = time.perf_counter()
        process_round(rnd, map_geom=geometry, source_file=src.name, players_meta=data["players"], tick_interval=.25,
                      compute_depth=True, places=data.get("places"))
        sec = time.perf_counter() - t
        result["features_with_depth"] = dict(round_ticks=len(rnd["ticks"]), seconds=round(sec, 2),
                                             ms_per_tick_all_10_players=round(sec * 1000 / len(rnd["ticks"]), 1))
    result["end"] = mem()
    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
