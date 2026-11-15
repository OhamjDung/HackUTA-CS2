"""Do generated paths pass the map check if their height is snapped to the floor (keeping x, y)?

The Round 4 paths drift upward in height. A bot in the game stays on the floor, so the useful question
is whether the horizontal path is walkable. For each trace this walks the points in order and sets each
height to the floor found by a down ray from the previous height + 40 units (a step up of at most 40).
It then runs map_review's unchanged check on the snapped path.

    python feasibility_snap.py REVIEW.json --csnet CSNET
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

import numpy as np

from map_review import MESH_REL, MapGeometry, check_trace, trace_points


def snap(geom: MapGeometry, points: np.ndarray, step_up: float = 40.0) -> np.ndarray:
    out = points.copy()
    for i in range(1, len(out)):
        origin = np.array([out[i, 0], out[i, 1], out[i - 1, 2] + step_up])
        t, _ = geom.cast(origin, [0, 0, -1])
        if np.isfinite(t[0]):
            out[i, 2] = origin[2] - t[0]
    return out


def kinds(reasons):
    return {re.match(r"[a-z -]+", r).group(0).strip() for r in reasons}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("review", type=Path)
    p.add_argument("--csnet", type=Path, required=True)
    args = p.parse_args()
    geom = MapGeometry.from_obj(args.csnet / MESH_REL)
    review = json.loads(args.review.read_text())
    passed, total, fail_kinds, rows = collections.Counter(), collections.Counter(), collections.Counter(), []
    for i, case in enumerate(review["cases"]):
        for name in ("actual", "own", "other", "base"):
            pts, _ = trace_points(case, name)
            raw = check_trace(geom, pts)[0]
            snapped = check_trace(geom, snap(geom, pts))[0]
            total[name] += 1
            passed[(name, "raw")] += not raw
            passed[(name, "snapped")] += not snapped
            for k in kinds(snapped):
                fail_kinds[(name, k)] += 1
            rows.append(dict(case=i, player=case["player"], trace=name, raw_pass=not raw, snapped_pass=not snapped,
                             snapped_reasons=snapped[:3]))
    summary = {name: dict(traces=total[name], raw_pass=passed[(name, "raw")], snapped_pass=passed[(name, "snapped")])
               for name in total}
    print(json.dumps(dict(summary=summary, snapped_failure_kinds={f"{a}: {b}": n for (a, b), n in fail_kinds.items()},
                          rows=rows), indent=1))


if __name__ == "__main__":
    main()
