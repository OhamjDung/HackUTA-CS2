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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csnet", type=Path, required=True)
    parser.add_argument("--demo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    configure(args.csnet)
    import demo_parser.extract as extract
    from demo_parser.cli import main as upstream_main
    original_map, original_metas = extract._player_index_map, extract._player_metas
    extract._player_index_map = lambda frame: original_map(active_roster(frame))
    extract._player_metas = lambda frame: original_metas(active_roster(frame))
    upstream_main(["--demo", str(args.demo), "--out", str(args.out), "--compress", "--compact", "--verbose"])


if __name__ == "__main__":
    main()
