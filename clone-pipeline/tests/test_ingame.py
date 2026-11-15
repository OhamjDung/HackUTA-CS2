"""In-game scoring (ingame.py): synthetic traces, then the real lookup, references and routes.

No CS2 here. The real-data test replays the clones' recorded routes as a stand-in "bot", which is
what a perfect playback of the first 20 s would look like, not a measurement of a bot in the game.
"""

import json
from pathlib import Path

from clone_pipeline.ingame import REFERENCE_DIR, PlaceLookup, score, trace_stats
from clone_pipeline.recording import read_recording
from clone_pipeline.similarity import compare

CLONES = Path(__file__).resolve().parents[2] / "clones"
LOOKUP = PlaceLookup({"0,0,0": "TSpawn"}, {"0,0": "TSpawn", "1,0": "TopofMid", "2,0": "Middle"})


def trace(*rounds):
    return {"match_id": "m1", "source": "gsi",
            "rounds": [{"round": i + 1, "players": players} for i, players in enumerate(rounds)]}


def walk(name, team, places_per_second, seconds=25, cell_x=None):
    """A path that steps one 64-unit cell to the right every 1/places_per_second seconds."""
    pts = []
    for i in range(seconds * 8):
        t = i / 8
        x = (cell_x if cell_x is not None else min(2, int(t * places_per_second))) * 64 + 10
        pts.append([t, float(x), 10.0])
    return {"name": name, "team": team, "clone_id": f"{name}_v1", "path": pts}


def test_place_lookup():
    assert LOOKUP.place(10, 10, 10) == "TSpawn"
    assert LOOKUP.place(70, 10) == "TopofMid"
    assert LOOKUP.place(64 * 3 + 5, 10) == "Middle"  # one cell outside: nearest known area
    assert LOOKUP.place(5000, 5000) is None


def test_trace_stats_routes_and_positions():
    t = trace([walk("donk", "T", 0.2)],                     # TSpawn > TopofMid > Middle
              [walk("donk", "T", 0.0, cell_x=1)],           # stays in TopofMid
              [walk("donk", "CT", 0.2), walk("broky", "T", 0.2)])
    s = trace_stats(t, "donk", LOOKUP)
    assert s["rounds"] == {"T": 2, "CT": 1}
    assert s["route_shares"]["T"] == {"Middle": 0.5, "TopofMid": 0.5}
    assert s["positions"]["T"]["TopofMid"] > s["positions"]["T"]["TSpawn"]
    assert s["seconds_to_first_contact"] == {}
    assert trace_stats(t, "donk_v1", LOOKUP)["rounds"] == s["rounds"]  # by clone_id too


def test_short_round_has_no_route():
    t = trace([{"name": "donk", "team": "T", "clone_id": None, "path": [[0, 10, 10], [1, 70, 10]]}])
    assert trace_stats(t, "donk", LOOKUP)["route_shares"] == {}


def test_score_report():
    ref = trace_stats(trace([walk("donk", "T", 0.2)]), "donk", LOOKUP)
    rep = score(trace([walk("donk", "T", 0.2)]), "donk", ref, LOOKUP)
    assert rep["held_back_vs_bot"]["T"]["route_overlap"] == 1.0
    assert rep["trace_source"] == "gsi" and "Simulated" not in rep["notes"][0]
    sim = score({**trace([walk("donk", "T", 0.2)]), "source": "simulated"}, "donk", ref, LOOKUP)
    assert sim["notes"][0].startswith("Simulated")


# --- Real data: the committed lookup, held-back references and route files -------------------

def routes_trace(clone_id: str) -> dict:
    prof = json.loads((CLONES / f"{clone_id}.json").read_text())
    rounds = []
    for side, items in prof["routes"].items():
        for r in items:
            ticks = read_recording(CLONES / r["file"])["Ticks"][::8]
            path = [[i / 8, t["Pre"]["OriginX"], t["Pre"]["OriginY"]] for i, t in enumerate(ticks)]
            rounds.append([{"name": "bot", "team": side, "clone_id": clone_id, "path": path}])
    return trace(*rounds)


def test_references_reproduce_the_profile_ceiling():
    for cid, ref in (("donk_v1", "donk_2393242"), ("broky_v1", "broky_2393024")):
        stats = json.loads((CLONES / cid / "stats.json").read_text())
        reference = json.loads((REFERENCE_DIR / f"{ref}.json").read_text())
        want = json.loads((CLONES / f"{cid}.json").read_text())["similarity"]["player_vs_self"]
        assert compare(stats, reference) == want


def test_own_routes_beat_the_other_players_routes():
    lookup = PlaceLookup.load()
    for target, other, ref in (("donk_v1", "broky_v1", "donk_2393242"), ("broky_v1", "donk_v1", "broky_2393024")):
        reference = json.loads((REFERENCE_DIR / f"{ref}.json").read_text())
        own = score(routes_trace(target), "bot", reference, lookup)["held_back_vs_bot"]
        swap = score(routes_trace(other), "bot", reference, lookup)["held_back_vs_bot"]
        for side in ("T", "CT"):
            assert own[side]["route_overlap"] > swap[side]["route_overlap"], (target, side)
