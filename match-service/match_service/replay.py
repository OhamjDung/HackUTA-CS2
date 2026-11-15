"""Replay data: real players' recorded rounds, and where the bots went in a match.

- RouteLibrary reads the clone pipeline's output in `clones/` (Arjun's): each profile lists its
  recorded rounds, and each round is a CS2-Bot-Controller playback file (Brotli JSON, 64 ticks a
  second, positions in `Ticks[i].Pre.OriginX/Y`). It turns a file into a short path for drawing.
- Trace keeps each player's path per round in a match. The cs2 backend fills it from game state
  (`allplayers` positions, sent while the person at the PC spectates); the mock fills it from real
  recorded routes, marked `simulated`.
- closest() finds the real round most like a bot's round, for the side-by-side replay.

Written from zero: no existing tool reads these files for a web view.
"""

import json
import math
import random
import time
from functools import lru_cache
from pathlib import Path

import brotli

SAMPLE_HZ = 8  # path points per second sent to the browser
TICKRATE = 64
OUTLINE_CELL = 64  # world units per cell in the map outline


class RouteLibrary:
    def __init__(self, data_dir: Path):
        self.dir = data_dir
        self._outline: dict | None = None

    def profile(self, clone_id: str) -> dict | None:
        path = self.dir / f"{clone_id}.json"
        if not clone_id.replace("_", "").replace("-", "").isalnum() or not path.is_file():
            return None
        return _read_json(path, path.stat().st_mtime)

    def clone_ids(self) -> list[str]:
        return sorted(p.stem for p in self.dir.glob("*.json") if self.profile(p.stem))

    def routes(self, clone_id: str) -> list[dict]:
        """Route metadata, both sides, without the paths."""
        prof = self.profile(clone_id) or {}
        out = []
        for side, items in (prof.get("routes") or {}).items():
            for r in items:
                out.append({"side": side, "recording": r["recording"], "label": r.get("label"),
                            "route_key": r.get("route_key"), "buy_type": r.get("buy_type"),
                            "match_id": r.get("match_id"), "round": r.get("round"),
                            "seconds": r.get("seconds"), "file": r["file"]})
        return out

    def route(self, clone_id: str, recording: str) -> dict | None:
        meta = next((r for r in self.routes(clone_id) if r["recording"] == recording), None)
        if not meta:
            return None
        file = (self.dir / meta["file"]).resolve()
        if self.dir.resolve() not in file.parents or not file.is_file():
            return None
        return {**{k: v for k, v in meta.items() if k != "file"}, "path": _read_path(file, file.stat().st_mtime)}

    def outline(self) -> dict:
        """Grid cells any recorded route passed through: a rough map shape, drawn under the paths."""
        if self._outline is not None:
            return self._outline
        cells: set[tuple[int, int]] = set()
        for cid in self.clone_ids():
            for r in self.routes(cid):
                full = self.route(cid, r["recording"])
                for _, x, y in full["path"] if full else []:
                    cells.add((math.floor(x / OUTLINE_CELL), math.floor(y / OUTLINE_CELL)))
        self._outline = {"cell": OUTLINE_CELL, "cells": sorted(cells)}
        return self._outline

    def closest(self, clone_id: str, side: str, path: list[list[float]]) -> dict | None:
        """The clone's real recorded round on `side` whose path is nearest to `path`.

        Score: the average, over both paths, of each point's distance to the other path (world
        units; lower is closer). Only the first 20 s of the bot's round are used, since recorded
        routes are about 20 s long.
        """
        bot = [(x, y) for t, x, y in path if t <= 20.0][::2]
        if len(bot) < 2:
            return None
        best = None
        for r in self.routes(clone_id):
            if r["side"] != side:
                continue
            full = self.route(clone_id, r["recording"])
            real = [(x, y) for _, x, y in full["path"]][::2]
            score = (_mean_nearest(bot, real) + _mean_nearest(real, bot)) / 2
            if best is None or score < best["score"]:
                best = {"score": round(score, 1), **full}
        return best


def _mean_nearest(a, b) -> float:
    return sum(min(math.dist(p, q) for q in b) for p in a) / len(a)


@lru_cache(maxsize=64)
def _read_json(path: Path, mtime: float) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


@lru_cache(maxsize=512)
def _read_path(file: Path, mtime: float) -> list[list[float]]:
    data = json.loads(brotli.decompress(file.read_bytes()))
    step = TICKRATE // SAMPLE_HZ
    out = []
    for i, tick in enumerate(data.get("Ticks", [])[::step]):
        pre = tick.get("Pre") or {}
        out.append([round(i / SAMPLE_HZ, 3), round(pre.get("OriginX", 0.0), 1), round(pre.get("OriginY", 0.0), 1)])
    return out


# --- Match traces ---------------------------------------------------------------------------------

class Trace:
    """Each player's path per round: {round: {name: {"team", "clone_id", "path": [[t, x, y], ...]}}}."""

    MAX_SECONDS = 120.0

    def __init__(self, match_id: str, map_name: str, source: str, bots: str | None = None):
        self.match_id, self.map, self.source = match_id, map_name, source
        self.bots = bots  # who played the clones: "stand_in" (default bots) or "clone" (CloneDirector)
        self.rounds: dict[int, dict[str, dict]] = {}
        self.reveal: dict[int, tuple[float, float]] = {}  # round -> (wall start, wall seconds), mock only
        self.live_round: int | None = None

    def add(self, round_no: int, t: float, name: str, team: str, x: float, y: float,
            clone_id: str | None = None, alive: bool = True) -> None:
        if t > self.MAX_SECONDS:
            return
        player = self.rounds.setdefault(round_no, {}).setdefault(
            name, {"team": team, "clone_id": clone_id, "path": [], "died_at": None})
        path = player["path"]
        if not alive:
            if player["died_at"] is None and path:
                player["died_at"] = round(t, 2)
            return
        if path and t - path[-1][0] < 1 / SAMPLE_HZ:
            return  # keep about SAMPLE_HZ points a second
        path.append([round(t, 2), round(x, 1), round(y, 1)])

    def to_json(self, now: float | None = None) -> dict:
        now = time.monotonic() if now is None else now
        rounds = []
        for n in sorted(self.rounds):
            players = []
            for name, p in self.rounds[n].items():
                path = p["path"]
                if n in self.reveal:  # mock: show the round as if it were being played now
                    start, wall = self.reveal[n]
                    shown = (now - start) / wall * (path[-1][0] if path else 0)
                    path = [pt for pt in path if pt[0] <= shown]
                players.append({"name": name, "team": p["team"], "clone_id": p["clone_id"],
                                "died_at": p["died_at"], "path": path})
            rounds.append({"round": n, "players": players})
        return {"match_id": self.match_id, "map": self.map, "source": self.source, "bots": self.bots,
                "live_round": self.live_round, "rounds": rounds}

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        data = self.to_json(now=float("inf"))
        (folder / f"{self.match_id}.json").write_text(json.dumps(data))


def gsi_players(payload: dict) -> list[dict]:
    """Players in a game state update's `allplayers`: name, team, x, y, alive.

    CS2 only sends `allplayers` to a spectator, so this is empty while the person at the PC plays.
    Field shape from the CounterStrike2GSI docs (`position` is "x, y, z"); not checked in CS2.
    """
    out = []
    for key, p in (payload.get("allplayers") or {}).items():
        try:
            x, y, _ = (float(v) for v in str(p.get("position", "")).split(","))
        except ValueError:
            continue
        health = (p.get("state") or {}).get("health", 100)
        out.append({"key": key, "name": p.get("name") or key, "team": p.get("team"),
                    "x": x, "y": y, "alive": (health or 0) > 0})
    return out


def simulated_round(library: RouteLibrary, trace: Trace, round_no: int, players: list,
                    rng: random.Random) -> None:
    """Mock: give each player a real recorded route for its side, slightly shifted."""
    pool: dict[str, list[tuple[str, dict]]] = {"T": [], "CT": []}
    for cid in library.clone_ids():
        for r in library.routes(cid):
            pool.setdefault(r["side"], []).append((cid, r))
    for p in players:
        if not p.is_clone:
            continue  # CS2 sends no positions while a human plays, so the mock shows none either
        own = [(cid, r) for cid, r in pool.get(p.team, []) if cid == p.clone_id]
        choices = own or pool.get(p.team, [])
        if not choices:
            continue
        cid, meta = rng.choice(choices)
        route = library.route(cid, meta["recording"])
        dx, dy = rng.uniform(-40, 40), rng.uniform(-40, 40)
        for t, x, y in route["path"]:
            trace.add(round_no, t, p.display_name, p.team, x + dx, y + dy, p.clone_id)
