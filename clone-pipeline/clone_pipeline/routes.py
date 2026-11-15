"""Cut a player's opening routes out of a parsed match.

A route segment is the player's movement from the tick a round goes live until the first of:
the player meets an enemy, 20 seconds pass, or the player dies.
"""

from dataclasses import dataclass

import pandas as pd

from .parse import TICKRATE, Match

MAX_SECONDS = 20
MIN_SECONDS = 3


@dataclass
class Segment:
    match_id: str
    round: int
    side: str            # "T" or "CT"
    buy_type: str        # "pistol", "eco", "force" or "full"
    end_reason: str      # "contact", "time_limit" or "death"
    seconds: float
    places: list[str]    # named map areas passed through, in order, without repeats
    route_key: str       # short label used to group similar routes
    ticks: pd.DataFrame  # the per-tick rows of this segment

    @property
    def label(self) -> str:
        return " > ".join(self.places)


def buy_type(round_number: int, equip_value: float, rounds_per_half: int = 12) -> str:
    """Name the kind of purchase from the value of the player's equipment when the round goes live."""
    if round_number in (1, rounds_per_half + 1):
        return "pistol"
    if equip_value < 1500:
        return "eco"
    if equip_value < 3700:
        return "force"
    return "full"


def first_contact_tick(match: Match, round_number: int) -> int | None:
    """First tick in the round where the player dealt damage or took damage.

    Gunshots alone do not count. Professionals often fire a few shots at nothing while leaving
    spawn, so a shot is not proof of a fight.
    """
    hurts = match.hurts[match.hurts["round"] == round_number]
    return int(hurts["tick"].min()) if not hurts.empty else None


def _places_in_order(place_names: pd.Series) -> list[str]:
    out: list[str] = []
    for place in place_names:
        if isinstance(place, str) and place and (not out or out[-1] != place):
            out.append(place)
    return out


def cut_segments(match: Match) -> list[Segment]:
    segments = []
    for row in match.rounds.itertuples():
        ticks = match.ticks[match.ticks["round"] == row.round]
        if ticks.empty or row.side not in ("T", "CT"):
            continue
        start = int(row.freeze_end)
        limit = start + MAX_SECONDS * TICKRATE
        end, reason = limit, "time_limit"

        contact = first_contact_tick(match, row.round)
        if contact is not None and contact < end:
            end, reason = contact, "contact"

        dead = ticks[(ticks["tick"] >= start) & (~ticks["is_alive"].astype(bool))]
        if not dead.empty and int(dead["tick"].min()) < end:
            end, reason = int(dead["tick"].min()), "death"

        part = ticks[(ticks["tick"] >= start) & (ticks["tick"] < end)].reset_index(drop=True)
        seconds = len(part) / TICKRATE
        if seconds < MIN_SECONDS:
            continue

        places = _places_in_order(part["last_place_name"])
        if not places:
            continue
        # Group routes by where they end. The full path stays in "places" for display.
        route_key = places[-1]

        segments.append(Segment(
            match_id=match.match_id,
            round=int(row.round),
            side=row.side,
            buy_type=buy_type(int(row.round), float(row.equip_value)),
            end_reason=reason,
            seconds=round(seconds, 2),
            places=places,
            route_key=route_key,
            ticks=part,
        ))
    return segments
