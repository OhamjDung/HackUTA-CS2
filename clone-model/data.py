"""Upstream window extraction and shuffling with Steam IDs kept aligned."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset


@lru_cache(maxsize=32)
def load_round(path: str) -> dict:
    with np.load(path, allow_pickle=False) as saved:
        sample = {k: saved[k] for k in saved.files if k != "_meta"}
        sample["meta"] = json.loads(str(saved["_meta"]))
        sample["__key__"] = Path(path).stem
    return sample


def shuffle_aligned(window: dict, identities: np.ndarray, target: int, permutation: np.ndarray):
    from training_data.pretrain_processor import shuffle_players
    if sorted(permutation.tolist()) != list(range(10)):
        raise ValueError("Expected a permutation of 10 players")
    class FixedPermutation:
        def permutation(self, n):
            assert n == 10
            return permutation
    shuffle_players(window, rng=FixedPermutation())
    return window, identities[permutation], int(np.where(permutation == target)[0][0])


class Windows(Dataset):
    def __init__(self, cache: Path, split: str, shuffle: bool = False, stride: int = 16):
        from training_data.pretrain_processor import PretrainWindowExtractor
        self.cache, self.shuffle = cache, shuffle
        self.manifest = json.loads((cache / "manifest.json").read_text())
        self.extractor = PretrainWindowExtractor(n_ticks=16, stride=stride,
            min_input_ticks=16, min_output_ticks=15, jitter=False, require_camera=True)
        self.index = []
        self.by_player = {name: [] for name in self.manifest["players"]}
        for entry in self.manifest["rounds"]:
            if entry["split"] != split:
                continue
            sample = load_round(str(cache / entry["file"]))
            for s in range(0, entry["ticks"] - 30, stride):
                if not sample["player_alive_mask"][s + 15, entry["target_index"]]:
                    continue
                self.by_player[entry["player"]].append(len(self.index))
                self.index.append((entry, s))
        if not self.index or any(not v for v in self.by_player.values()):
            raise ValueError(f"Insufficient windows for {split}")

    def __len__(self):
        return len(self.index)

    def __getitem__(self, i):
        from training_data.torch_dataset import augment_depth_with_angles, sample_to_torch
        entry, s = self.index[i]
        sample = load_round(str(self.cache / entry["file"]))
        meta = sample["meta"]
        window = self.extractor._build_window(sample, s, entry["ticks"], s, s+16, s+16, s+31,
            sample["round_seconds"], .25, meta)
        identities = np.array([self.manifest["registry"].get(str(p["steamid"]), 0)
            for p in meta["players"]], dtype=np.int64)
        target = entry["target_index"]
        if self.shuffle:
            window, identities, target = shuffle_aligned(window, identities, target, np.random.permutation(10))
        window = sample_to_torch(augment_depth_with_angles(window))
        window["target_index"] = torch.tensor(target)
        window["identity"] = torch.tensor(identities[target])
        if identities[target] != entry["identity"]:
            raise ValueError("Identity detached from target player")
        return window
