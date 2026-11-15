"""Score a bot's rounds in CS2 against a real player: SPEC.md section 10.2.

The clone side of that comparison had no data, because nothing recorded a bot match. The match
service now keeps a trace of every player's position per round, taken from CS2's game state
(`GET /matches/{id}/trace`). This module turns a trace into the same "stats" block that
build.py writes for real recordings, then scores it with similarity.compare():

    real player, held-back match  vs  real player, other matches   = the ceiling (in the profile)
    real player, held-back match  vs  the clone bot in CS2         = the result
    real player, held-back match  vs  a default bot in CS2         = the baseline

Game state gives positions but no map area names, so a lookup table maps a position to the area
name that CS2 itself reports there (`last_place_name`), built once from real Mirage recordings.

Commands (from clone-pipeline/):
    uv run python -m clone_pipeline.ingame places --demos <a.dem> <b.dem>
    uv run python -m clone_pipeline.ingame reference --player donk --demo <held-back.dem>
    uv run python -m clone_pipeline.ingame score --trace trace.json --player donk \\
        --reference references/donk_2393242.json --profile ../clones/donk_v1.json

Written from zero on top of this package's own measures; no existing tool scores these traces.
"""

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from .routes import MAX_SECONDS, MIN_SECONDS
from .similarity import compare

PACKAGE = Path(__file__).resolve().parent
PLACES_FILE = PACKAGE / "maps" / "de_mirage_places.json"
REFERENCE_DIR = PACKAGE.parent / "references"
CELL = 64    # world units per lookup cell, across
ZCELL = 128  # world units per lookup cell, up (Mirage has areas above each other, e.g. Underpass)


# --- Position to map area ----------------------------------------------------------------------

def _key(*parts: float) -> str:
    return ",".join(str(p) for p in parts)


class PlaceLookup:
    """Map area name at a position, from the most common `last_place_name` seen in each cell."""

    def __init__(self, cells3: dict[str, str], cells2: dict[str, str]):
        self.cells3, self.cells2 = cells3, cells2

    @classmethod
    def load(cls, path: Path = PLACES_FILE) -> "PlaceLookup":
        data = json.loads(Path(path).read_text())
        return cls(data["cells3"], data["cells2"])

    def place(self, x: float, y: float, z: float | None = None) -> str | None:
        cx, cy = math.floor(x / CELL), math.floor(y / CELL)
        if z is not None:
            found = self.cells3.get(_key(cx, cy, math.floor(z / ZCELL)))
            if found:
                return found
        found = self.cells2.get(_key(cx, cy))
        if found:
            return found
        # A bot can stand a little outside every cell the real players crossed: look one cell around.
        near = Counter(self.cells2[k] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                       if (k := _key(cx + dx, cy + dy)) in self.cells2)
        return near.most_common(1)[0][0] if near else None


def build_places(demo_paths: list[Path], every: int = 8) -> dict:
    """Count area names per cell over every player in these recordings (every `every`-th tick)."""
    from demoparser2 import DemoParser  # only needed here

    votes3: dict[str, Counter] = {}
    votes2: dict[str, Counter] = {}
    for path in demo_paths:
        ticks = DemoParser(str(path)).parse_ticks(["X", "Y", "Z", "last_place_name", "is_alive"])
        ticks = ticks[ticks["is_alive"].astype(bool) & ticks["last_place_name"].astype(bool)]
        ticks = ticks[ticks["tick"] % every == 0]
        for x, y, z, place in zip(ticks["X"], ticks["Y"], ticks["Z"], ticks["last_place_name"]):
            cx, cy, cz = math.floor(x / CELL), math.floor(y / CELL), math.floor(z / ZCELL)
            votes3.setdefault(_key(cx, cy, cz), Counter())[place] += 1
            votes2.setdefault(_key(cx, cy), Counter())[place] += 1
    return {
        "what": "Map area name (CS2's last_place_name) per cell, by majority of real players' ticks.",
        "source": [Path(p).name for p in demo_paths],
        "license": "Derived from OpenCS2 (Julien Blanchon), CC BY 4.0",
        "cell": CELL, "zcell": ZCELL,
        "cells3": {k: c.most_common(1)[0][0] for k, c in votes3.items()},
        "cells2": {k: c.most_common(1)[0][0] for k, c in votes2.items()},
    }


# --- Trace to stats ------------------------------------------------------------------------------

def _points(path: list[list[float]]):
    for pt in path:
        yield pt[0], pt[1], pt[2], (pt[3] if len(pt) > 3 else None)


def player_rounds(trace: dict, player: str) -> list[tuple[str, list[list[float]]]]:
    """(side, path) for each round the player appears in, matched by name or clone_id."""
    out = []
    for rnd in trace.get("rounds", []):
        for p in rnd.get("players", []):
            if player in (p.get("name"), p.get("clone_id")) and p.get("team") in ("T", "CT") and p.get("path"):
                out.append((p["team"], p["path"]))
    return out


def trace_stats(trace: dict, player: str, lookup: PlaceLookup) -> dict:
    """The stats block for one player in a trace, in build.stats_block()'s format.

    - positions: share of position samples (alive only) in each map area, per side.
    - route_shares: like routes.cut_segments(), the route is the areas passed in the first
      20 s, keyed by where it ends. Real routes also stop at the first damage; a trace has no
      damage, so a bot's route only stops at 20 s or death.
    - seconds_to_first_contact: not measured (a trace has no damage events).
    """
    rounds = Counter()
    positions = {"T": Counter(), "CT": Counter()}
    routes = {"T": Counter(), "CT": Counter()}
    for side, path in player_rounds(trace, player):
        rounds[side] += 1
        places, last_t = [], 0.0
        for t, x, y, z in _points(path):
            place = lookup.place(x, y, z)
            if not place:
                continue
            positions[side][place] += 1
            if t <= MAX_SECONDS:
                last_t = t
                if not places or places[-1] != place:
                    places.append(place)
        if places and last_t >= MIN_SECONDS:
            routes[side][places[-1]] += 1

    def shares(counts: Counter, top: int | None = None) -> dict[str, float]:
        total = sum(counts.values())
        return {k: round(n / total, 4) for k, n in counts.most_common(top)} if total else {}

    return {
        "rounds": {side: rounds[side] for side in ("T", "CT")},
        "positions": {side: shares(positions[side], 40) for side in ("T", "CT") if positions[side]},
        "route_shares": {side: shares(routes[side]) for side in ("T", "CT") if routes[side]},
        "seconds_to_first_contact": {},
    }


def score(trace: dict, player: str, reference: dict, lookup: PlaceLookup,
          profile: dict | None = None) -> dict:
    """Compare a bot's rounds in a trace with the real player's held-back match.

    `reference` is a stats block from `reference` (below). With the clone's profile, the report
    also carries the ceiling (the real player against himself) for the same table.
    """
    ingame = trace_stats(trace, player, lookup)
    report = {
        "player": player,
        "match_id": trace.get("match_id"),
        "trace_source": trace.get("source"),  # "gsi" (real CS2) or "simulated" (mock backend)
        "held_back_vs_bot": compare(reference, ingame),
        "bot_stats": ingame,
        "notes": [
            "Overlap runs from 0 (nothing shared) to 1 (identical). Rounds: [held-back, bot]; "
            "for the ceiling, [build matches, held-back].",
            "Bot routes stop at 20 s or death; real routes also stop at first damage.",
            "Time to first contact is not measured from a trace.",
        ],
    }
    if trace.get("source") != "gsi":
        report["notes"].insert(0, "Simulated trace (mock backend): NOT a measurement of a bot in CS2.")
    if profile and profile.get("similarity"):
        report["ceiling"] = profile["similarity"].get("player_vs_self")
    return report


def table(report: dict, baseline: dict | None = None) -> str:
    """The SPEC 10.2 table as text: ceiling, clone, baseline, with round counts."""
    lines = [f"{report['player']} - match {report['match_id']} ({report['trace_source']})", ""]
    head = f"{'side':<4} {'measure':<17} {'ceiling':>16} {'this bot':>16}" + (f" {'baseline':>16}" if baseline else "")
    lines += [head, "-" * len(head)]
    for side in ("T", "CT"):
        for key, name in (("position_overlap", "position overlap"), ("route_overlap", "route overlap")):
            def cell(block):
                if not block:
                    return "-"
                s = block.get(side) or {}
                v, r = s.get(key), s.get("rounds") or [0, 0]
                return "-" if v is None else f"{v:.3f} ({r[0]}/{r[1]} rd)"
            row = f"{side:<4} {name:<17} {cell(report.get('ceiling')):>16} {cell(report['held_back_vs_bot']):>16}"
            if baseline:
                row += f" {cell(baseline['held_back_vs_bot']):>16}"
            lines.append(row)
    return "\n".join(lines + [""] + [f"- {n}" for n in report["notes"]])


# --- Commands ------------------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Score bots' in-game rounds against real players (SPEC 10.2).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("places", help="build the position-to-area lookup from real recordings")
    p.add_argument("--demos", nargs="+", type=Path, required=True)
    p.add_argument("--out", type=Path, default=PLACES_FILE)

    r = sub.add_parser("reference", help="stats of a player's held-back match, the fixed side of the score")
    r.add_argument("--player", required=True)
    r.add_argument("--demo", type=Path, required=True)
    r.add_argument("--out", type=Path)

    s = sub.add_parser("score", help="score one player in a match trace")
    s.add_argument("--trace", type=Path, required=True, help="JSON from GET /matches/{id}/trace")
    s.add_argument("--player", required=True, help="bot name or clone_id in the trace")
    s.add_argument("--reference", type=Path, required=True)
    s.add_argument("--profile", type=Path, help="the clone profile, for the ceiling column")
    s.add_argument("--baseline-trace", type=Path, help="a trace with a default bot, for the baseline column")
    s.add_argument("--baseline-player", help="the default bot's name in that trace")
    s.add_argument("--places", type=Path, default=PLACES_FILE)
    s.add_argument("--out", type=Path, help="also write the report as JSON")
    args = ap.parse_args()

    if args.cmd == "places":
        data = build_places(args.demos)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(data, separators=(",", ":"), sort_keys=True))
        print(f"{len(data['cells2'])} cells ({len(data['cells3'])} with height), "
              f"{len(set(data['cells2'].values()))} areas -> {args.out}")
    elif args.cmd == "reference":
        from .build import stats_block
        from .parse import load_match
        from .routes import cut_segments

        match = load_match(args.demo, args.player)
        match_id = match.match_id.removesuffix(".dem")  # the id comes from "<id>_<name>.dem"
        block = {"player": match.player_name, "match_id": match_id,
                 **stats_block([match], cut_segments(match))}
        out = args.out or REFERENCE_DIR / f"{args.player.lower()}_{match_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(block, indent=1))
        print(f"{match.player_name} in {match.match_id}: rounds {block['rounds']} -> {out}")
    else:
        lookup = PlaceLookup.load(args.places)
        reference = json.loads(args.reference.read_text())
        profile = json.loads(args.profile.read_text()) if args.profile else None
        report = score(json.loads(args.trace.read_text()), args.player, reference, lookup, profile)
        baseline = None
        if args.baseline_trace and args.baseline_player:
            baseline = score(json.loads(args.baseline_trace.read_text()), args.baseline_player, reference, lookup)
            report["baseline"] = baseline
        print(table(report, baseline))
        if args.out:
            args.out.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
