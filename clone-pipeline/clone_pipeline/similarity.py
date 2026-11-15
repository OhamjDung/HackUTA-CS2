"""Compare two sets of rounds: how alike are the positions, the routes, and the timing?

Used three ways (SPEC.md section 10.2): the real player against their own held-back match (the
ceiling), the clone against the held-back match (the result), and a default bot against it (the baseline).
"""

import math
from statistics import median


def overlap(a: dict[str, float], b: dict[str, float]) -> float | None:
    """How alike two share tables are, from 0 (nothing in common) to 1 (identical).

    This is 1 minus the Jensen-Shannon distance, a standard measure of the difference between
    two distributions.
    """
    if not a or not b:
        return None
    keys = set(a) | set(b)
    total_a, total_b = sum(a.values()), sum(b.values())
    p = {k: a.get(k, 0.0) / total_a for k in keys}
    q = {k: b.get(k, 0.0) / total_b for k in keys}
    mid = {k: (p[k] + q[k]) / 2 for k in keys}

    def divergence(x: dict[str, float]) -> float:
        return sum(x[k] * math.log2(x[k] / mid[k]) for k in keys if x[k] > 0)

    return round(1 - math.sqrt(max(0.0, (divergence(p) + divergence(q)) / 2)), 3)


def compare(a: dict, b: dict) -> dict:
    """Compare two "stats" blocks as written by build.py (positions, route_shares, contact seconds)."""
    out: dict = {}
    for side in ("T", "CT"):
        times_a = a["seconds_to_first_contact"].get(side, [])
        times_b = b["seconds_to_first_contact"].get(side, [])
        out[side] = {
            "position_overlap": overlap(a["positions"].get(side, {}), b["positions"].get(side, {})),
            "route_overlap": overlap(a["route_shares"].get(side, {}), b["route_shares"].get(side, {})),
            "median_seconds_to_first_contact": [
                round(median(times_a), 2) if times_a else None,
                round(median(times_b), 2) if times_b else None,
            ],
            "rounds": [a["rounds"].get(side, 0), b["rounds"].get(side, 0)],
        }
    return out
