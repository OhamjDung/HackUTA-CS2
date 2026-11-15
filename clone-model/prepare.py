"""Use CS-NET's parser output, filters, inventory mapping and wall rays unchanged.

Round caches are NPZ instead of WDS; arrays keep the upstream training format.
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path

import numpy as np

from common import CSNET_REVISION, PLAYERS, REGISTRY, configure, round_split, write_json


def build_cache(csnet: Path, json_dir: Path, out: Path, games: list) -> dict:
    configure(csnet)
    from create_training_data import _convert_inventory_indices
    from replay_tool.filter import filter_data
    from training_data.map_loader import get_map_geometry
    from training_data.round_processor import process_round

    out.mkdir(parents=True, exist_ok=True)
    geometry = get_map_geometry("de_mirage", csnet / "maps/optimized_obj_files")
    entries = []
    for name, mid, shard, slug, declared_split in games:
        if name not in PLAYERS or declared_split != ("test" if round_split(mid, 0) == "test" else "train"):
            raise ValueError(f"Unexpected source or split: {name} {mid}")
        source = json_dir / f"{mid}.json.gz"
        with gzip.open(source, "rt", encoding="utf-8") as file:
            data = json.load(file)
        if data.get("map") != "de_mirage":
            raise ValueError(f"Wrong map in {source}")
        if not data.get("rounds"):
            raise ValueError(f"No parsed rounds in {source}")
        players = data.get("players", [])
        if len(players) != 10:
            raise ValueError(f"Expected 10 identities in {mid}")
        matches = [i for i, p in enumerate(players) if str(p["steamid"]) == PLAYERS[name]]
        if len(matches) != 1:
            raise ValueError(f"Missing or duplicate target Steam ID in {mid}")
        target = matches[0]
        filter_data(data)
        _convert_inventory_indices(data)
        for r in data["rounds"]:
            rid = int(r["id"])
            split = round_split(mid, rid)
            filename = f"{mid}_r{rid:03d}.npz"
            path = out / filename
            if not path.exists():
                if len(r["ticks"]) < 31:
                    continue
                r["map"] = "de_mirage"
                sample = process_round(r, map_geom=geometry, source_file=f"{mid}.json.gz",
                    players_meta=players, tick_interval=.25, compute_depth=True, places=data.get("places"))
                meta = sample["meta"]
                meta.update(match_id=mid, target_name=name, target_index=target, split=split)
                arrays = {k: v for k, v in sample.items() if isinstance(v, np.ndarray)}
                if any(not np.isfinite(a).all() for a in arrays.values()):
                    raise ValueError(f"Nonfinite features in {mid} round {rid}")
                np.savez_compressed(path, **arrays, _meta=json.dumps(meta))
            with np.load(path, allow_pickle=False) as saved:
                meta = json.loads(str(saved["_meta"]))
                if meta["match_id"] != mid or meta["target_name"] != name or meta["split"] != split:
                    raise ValueError(f"Stale or conflicting cache {path}")
                ticks = len(saved["player_pos"])
            entries.append(dict(file=filename, match_id=mid, round_id=rid, split=split,
                player=name, target_index=target, identity=REGISTRY[PLAYERS[name]], ticks=ticks))
            print(f"cached {name} {mid} round={rid} split={split} ticks={ticks}", flush=True)
    counts = Counter(f"{e['player']}/{e['split']}" for e in entries)
    for name in PLAYERS:
        for split in ("train", "dev", "test"):
            if not counts[f"{name}/{split}"]:
                raise ValueError(f"No {split} rounds for {name}")
    manifest = dict(format_version=1, csnet_revision=CSNET_REVISION, registry=REGISTRY,
        players=PLAYERS, source_games=games, counts=dict(counts), rounds=entries)
    write_json(out / "manifest.json", manifest)
    print(json.dumps(dict(counts)), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csnet", type=Path, required=True)
    parser.add_argument("--json-dir", type=Path, required=True)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build_cache(args.csnet, args.json_dir, args.out, json.loads(args.games.read_text()))


if __name__ == "__main__":
    main()
