"""In-game similarity score for a match (SPEC.md section 10.2), served to the proof page.

The scoring itself is the clone pipeline's (clone-pipeline/clone_pipeline/ingame.py): a bot's
rounds in a match trace against the real player's held-back match. This module only finds the
pieces: that package, the held-back reference for a clone, and the clone's ceiling.

ingame.py and the similarity module it uses need only the standard library, so the match service
imports them from the repository folder instead of installing the clone pipeline (and pandas).
"""

import importlib
import json
import sys
from functools import lru_cache
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent.parent / "clone-pipeline"


class ScoringUnavailable(Exception):
    pass


@lru_cache(maxsize=1)
def _ingame():
    if not (PIPELINE_DIR / "clone_pipeline" / "ingame.py").is_file():
        raise ScoringUnavailable(f"clone pipeline not found at {PIPELINE_DIR}")
    if str(PIPELINE_DIR) not in sys.path:
        sys.path.append(str(PIPELINE_DIR))
    return importlib.import_module("clone_pipeline.ingame")


@lru_cache(maxsize=1)
def _lookup():
    ingame = _ingame()
    return ingame.PlaceLookup.load()


def reference_for(name: str) -> dict | None:
    """The held-back stats block for a player, by name: references/<name>_<match id>.json."""
    ingame = _ingame()
    found = sorted(ingame.REFERENCE_DIR.glob(f"{name.lower()}_*.json"))
    return json.loads(found[0].read_text()) if found else None


def score_player(trace: dict, player: dict, profile: dict | None) -> dict:
    """Score one trace player ({"name", "clone_id"}) against that clone's real player."""
    ingame = _ingame()
    clone_id = player.get("clone_id")
    real_name = (profile or {}).get("display_name") or (clone_id or player["name"]).split("_")[0]
    reference = reference_for(real_name)
    if reference is None:
        raise ScoringUnavailable(f"no held-back reference for {real_name} in {ingame.REFERENCE_DIR}")
    report = ingame.score(trace, clone_id or player["name"], reference, _lookup(), profile)
    report["reference"] = {"player": reference.get("player"), "match_id": reference.get("match_id"),
                           "rounds": reference.get("rounds")}
    return report
