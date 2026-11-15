"""Pinned upstream integration and player/match identities."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

CSNET_REVISION = "268dd2193c8a3d6e330c07dde5a851196c94eeaa"
PLAYERS = {"donk": "76561198018303780", "broky": "76561198201620490"}
REGISTRY = {sid: i + 1 for i, sid in enumerate(sorted(PLAYERS.values(), key=int))}
HOLDOUTS = {"2393242", "2393024"}


def configure(csnet: str | Path) -> Path:
    root = Path(csnet).resolve()
    if not (root / "scripts/pretrain_model.py").is_file():
        raise ValueError("--csnet must point to the pinned CS-NET checkout")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if revision != CSNET_REVISION:
        raise ValueError(f"Expected CS-NET {CSNET_REVISION}, got {revision}")
    for path in (root, root / "scripts"):
        if str(path) not in sys.path:
            sys.path.append(str(path))
    return root


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def round_split(match_id: str, round_id: int) -> str:
    if match_id in HOLDOUTS:
        return "test"
    # Entire rounds are reserved for tuning; overlapping windows cannot cross splits.
    value = int(hashlib.sha256(f"{match_id}:{round_id}:42".encode()).hexdigest()[:8], 16)
    return "dev" if value % 5 == 0 else "train"


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)
