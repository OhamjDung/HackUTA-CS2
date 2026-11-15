"""CS-NET parser wrapper: exclude unassigned/spectator rows from its fixed 10-player roster."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import configure


def active_roster(frame):
    playing = frame[frame["team_num"].isin([2, 3])]
    counts = playing["team_num"].value_counts().to_dict()
    if len(playing) != 10 or playing["steamid"].nunique() != 10 or counts.get(2, 0) != 5 or counts.get(3, 0) != 5:
        raise ValueError("Ambiguous roster: require exactly five unique players on each playing team")
    return playing


class RosterParser:
    """Keep the checked first-tick roster through metadata and all later per-round tick passes."""
    def __init__(self, parser):
        self.parser = parser
        self.roster = None

    def __getattr__(self, name):
        return getattr(self.parser, name)

    def parse_ticks(self, *args, **kwargs):
        if self.roster is not None:
            kwargs.setdefault("players", [int(sid) for sid in self.roster])
        frame = self.parser.parse_ticks(*args, **kwargs)
        if "steamid" not in frame:
            return frame
        if self.roster is None and "team_num" in frame:
            first = frame[frame["tick"] == frame["tick"].min()]
            self.roster = tuple(active_roster(first)["steamid"].astype(str))
        if self.roster is not None:
            frame = frame[frame["steamid"].astype(str).isin(self.roster)]
        return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csnet", type=Path, required=True)
    parser.add_argument("--demo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    configure(args.csnet)
    import demo_parser.extract as extract
    original_parser = extract.DemoParser
    extract.DemoParser = lambda path: RosterParser(original_parser(path))
    original_map, original_metas = extract._player_index_map, extract._player_metas
    extract._player_index_map = lambda frame: original_map(active_roster(frame))
    extract._player_metas = lambda frame: original_metas(active_roster(frame))
    data = extract.parse_demo(str(args.demo), interval=.25, verbose=True)
    if not data["rounds"]:
        raise ValueError("Parser produced no rounds; refusing to save an empty training match")
    output = extract.save_demo_json(data, str(args.out), compact=True, compress=True)
    print(f"Saved {len(data['rounds'])} rounds to {output}", flush=True)


if __name__ == "__main__":
    main()
