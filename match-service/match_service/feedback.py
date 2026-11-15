"""Key-mistake feedback for a death (SPEC.md, replay puzzles).

Rule-based, over the saved window of a death or puzzle: where everyone was, what the hero held and
fired, and who killed whom. No model, no network, so it can show the moment the player dies.

The rules are distance and timing heuristics. They do not see walls, so "enemy close" means close, not
"had a line of sight". The thresholds are starting values, not tuned against real deaths.
Written from zero: no existing open-source tool gives this feedback for CS2 bot matches.
"""

from __future__ import annotations

import math

# World units (CS2: a player is about 72 tall; a typical duel is 500 to 1500).
ALONE_DISTANCE = 900        # nearest living teammate farther than this at the first contact: peeked alone
CROSSFIRE_DISTANCE = 1500   # enemies within this at the death count toward a crossfire
STILL_SPEED = 25            # units per second under which a player is standing still
SHOOTING_MOVE_SPEED = 140   # moving faster than this while firing is a spray on the move
LOOKBACK = 3.0              # seconds before the death that the rules look at
MAX_ITEMS = 3

GRENADES = ("flashbang", "smokegrenade", "hegrenade", "molotov", "incgrenade", "decoy")


def _hero(puzzle: dict) -> dict | None:
    return next((p for p in puzzle["players"] if p.get("hero")), None)


def _at(track: list[dict], t: float) -> dict | None:
    """The last sample at or before t (None before the first sample)."""
    best = None
    for s in track:
        if s["t"] <= t + 1e-9:
            best = s
        else:
            break
    return best


def _speed(track: list[dict], t0: float, t1: float) -> float:
    pts = [s for s in track if t0 <= s["t"] <= t1]
    if len(pts) < 2:
        return 0.0
    dist = sum(math.dist((a["x"], a["y"]), (b["x"], b["y"])) for a, b in zip(pts, pts[1:]))
    span = pts[-1]["t"] - pts[0]["t"]
    return dist / span if span > 0 else 0.0


def _alive_at(player: dict, t: float) -> bool:
    s = _at(player["track"], t)
    return bool(s and s.get("hp", 0) > 0)


def death_time(puzzle: dict, hero: dict) -> float | None:
    for e in puzzle.get("events", []):
        if e["type"] == "kill" and e["victim"] == hero["name"]:
            return e["t"]
    return None


def feedback_for(puzzle: dict) -> list[dict]:
    """Up to three ranked mistakes for the hero's death in this window.

    Each item: {id, title, detail, t, severity 1-3}. Empty when the hero did not die or nothing fires.
    """
    hero = _hero(puzzle)
    if not hero or not hero["track"]:
        return []
    t_death = death_time(puzzle, hero)
    if t_death is None:
        return []
    start = max(0.0, t_death - LOOKBACK)
    mates = [p for p in puzzle["players"] if p is not hero and p["side"] == hero["side"]]
    enemies = [p for p in puzzle["players"] if p["side"] != hero["side"]]
    killer = next((e["attacker"] for e in puzzle["events"]
                   if e["type"] == "kill" and e["victim"] == hero["name"]), None)
    found: list[dict] = []

    def add(id_: str, title: str, detail: str, t: float, severity: int) -> None:
        found.append({"id": id_, "title": title, "detail": detail, "t": round(max(t, 0.0), 2),
                      "severity": severity})

    def dist_to(sample: dict, other: dict, t: float) -> float | None:
        o = _at(other["track"], t)
        return math.dist((sample["x"], sample["y"]), (o["x"], o["y"])) if o else None

    # The first time any enemy came within range before the death: the moment of contact.
    contact_t = t_death
    for s in hero["track"]:
        if s["t"] < start or s["t"] > t_death:
            continue
        if any(_alive_at(e, s["t"]) and (d := dist_to(s, e, s["t"])) is not None and d < CROSSFIRE_DISTANCE
               for e in enemies):
            contact_t = s["t"]
            break

    # 1. Alone at contact (only counts when teammates were alive to be near).
    h = _at(hero["track"], contact_t)
    living = [m for m in mates if _alive_at(m, contact_t)]
    if h and living:
        gaps = [d for m in living if (d := dist_to(h, m, contact_t)) is not None]
        if gaps and min(gaps) > ALONE_DISTANCE:
            add("alone", "You took the fight without your team",
                f"Your nearest teammate was about {min(gaps):.0f} units away when the enemy appeared. "
                "Stay within one callout of a teammate so you can trade.", contact_t, 3)

    # 2. Died holding utility that was never thrown.
    carried = {w for w in (hero.get("start") or {}).get("weapons", []) if w in GRENADES}
    thrown = any(e["type"] == "throw" and e.get("attacker") == hero["name"] for e in puzzle["events"])
    if carried and not thrown:
        add("no_utility", "You died holding utility",
            f"You still had {', '.join(sorted(carried))} when you died. A flash or smoke before the peek "
            "gives you the first shot.", t_death, 2)

    # 3. Standing still and never firing right before the death.
    fired_recent = any(s.get("fire") for s in hero["track"] if t_death - 1.5 <= s["t"] <= t_death)
    if _speed(hero["track"], max(start, t_death - 1.5), t_death) < STILL_SPEED and not fired_recent:
        add("still", "You stood still and never fired",
            "You were not moving or shooting in the last 1.5 seconds. Either hold an angle you can "
            "fire from or break line of sight.", t_death - 1.5, 2)

    # 4. Shooting while moving.
    moving_shots = [s for s in hero["track"] if s.get("fire") and start <= s["t"] <= t_death
                    and _speed(hero["track"], s["t"] - 0.25, s["t"] + 0.25) > SHOOTING_MOVE_SPEED]
    if len(moving_shots) >= 2:
        add("moving_shots", "You fired while running",
            "Most rifle shots are inaccurate while moving. Stop (or counter-strafe) before you shoot.",
            moving_shots[0]["t"], 2)

    # 5. Weapon changed in the two seconds before the death, during the fight.
    w_then, w_now = _at(hero["track"], max(start, t_death - 2.0)), _at(hero["track"], t_death)
    if w_then and w_now and w_then.get("weapon") != w_now.get("weapon") and t_death - contact_t < 3:
        add("switched", "You switched weapons in the fight",
            f"You went from {w_then.get('weapon')} to {w_now.get('weapon')} in the last 2 seconds. "
            "Switch before contact, not during it.", t_death - 2.0, 1)

    # 6. Crossfire: two or more enemies close at the death.
    d_sample = _at(hero["track"], t_death)
    if d_sample:
        close = [e for e in enemies if _alive_at(e, t_death - 0.01)
                 and (d := dist_to(d_sample, e, t_death)) is not None and d < CROSSFIRE_DISTANCE]
        if len(close) >= 2:
            add("crossfire", "Two enemies could both shoot you",
                f"{len(close)} enemies were within {CROSSFIRE_DISTANCE} units when you died. A peek two "
                "players can both shoot is hard to win; fall back or ask for a flash.", t_death, 3)

    # 7. Low health and still moving toward the fight.
    low = [s for s in hero["track"] if start <= s["t"] <= t_death and s.get("hp", 100) < 40]
    if low and killer and _speed(hero["track"], low[0]["t"], t_death) > STILL_SPEED:
        add("low_hp_push", "You pushed at low health",
            f"You were at {low[0].get('hp')} HP and still moved toward the fight. At low health, "
            "back off and let a teammate take it.", low[0]["t"], 2)

    found.sort(key=lambda f: (-f["severity"], f["t"]))
    return found[:MAX_ITEMS]
