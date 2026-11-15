"""Write clones/donk_v2.json and clones/broky_v2.json: v1's routes and buys, LF's quirks, rule-based game sense.

    python clone-director/tools/make_v2_profiles.py

Built from the newest quirk version, `<player>LF.json` (its routes and buy plan equal v1's; checked below).
Changes from LF:
  - ids and bot name become `<player>_v2`; no neural model is named (`model` null);
  - quirk control `slow_share` is added from the player's measured quirk, so quiet walking happens at the
    player's own slow-movement rate instead of an average pro's;
  - a `game_sense` section turns on hearing and sight hand-offs, grenade-safe hand-off, route variety and
    quiet walking, and turns off the wall-blind "enemy close" hand-off (sight replaces it).
The bot entry for `<player>_v2` is a plain copy of the original (full-strength aim, no human-aim limits);
see add_clone_bot_entries.py. Plan and reasons: .plans/v2-quirks-gamesense-plan.md and v2-quirk-inventory.md.
"""
import json
from pathlib import Path

CLONES = Path(__file__).resolve().parents[2] / "clones"

GAME_SENSE = {
    "hear_handoff": True,
    "sight_handoff": True,
    "enemy_close_handoff": False,
    "grenade_safe_handoff": True,
    "route_variety": True,
    "quiet_walk": True,
    "note": ("Rule-based game sense (CloneDirector Core/GameSense.cs). Distances are historical CS1.6 bot values, "
             "not verified CS2 audibility; tune here. Not yet run in CS2."),
}


def make(player: str) -> dict:
    lf = json.loads((CLONES / f"{player}LF.json").read_text(encoding="utf-8"))
    v1 = json.loads((CLONES / f"{player}_v1.json").read_text(encoding="utf-8"))
    if lf["routes"] != v1["routes"] or lf["buy_plan"] != v1["buy_plan"]:
        raise SystemExit(f"{player}LF routes or buy plan differ from {player}_v1; check before building v2")
    v2 = dict(lf)
    clone_id = f"{player}_v2"
    v2.update(clone_id=clone_id, display_name=clone_id, stand_in_bot=clone_id, model=None)
    controls = dict(lf["quirk_controls"])
    slow = lf["quirks"]["slow_share"]["player"]
    controls["slow_share"] = {
        "value": round(float(slow), 4),
        "applied_by": "CloneDirector game sense: chance per second to walk silently while a heard enemy is near",
        "status": "implemented in the plugin; not run in CS2",
    }
    v2["quirk_controls"] = controls
    v2["game_sense"] = GAME_SENSE
    v2["learned"] = dict(lf.get("learned") or {}, neural_model=None,
                         note=f"v2: {player}_v1 routes and buys, {player}LF quirks, rule-based game sense, full-strength bot entry.")
    return v2


def main():
    for player in ("donk", "broky"):
        out = CLONES / f"{player}_v2.json"
        out.write_text(json.dumps(make(player), indent=2) + "\n", encoding="utf-8")
        print("wrote", out)


if __name__ == "__main__":
    main()
