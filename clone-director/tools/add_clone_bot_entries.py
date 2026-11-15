"""Add one bot entry per clone to the bot base's packed profile file, so each clone can have its own name.

Why: the game takes a bot's name from an entry in botprofile.db (inside botprofile.vpk), and refuses a
second bot whose name is already in the game ("donk is already in the game"). donk_v1 and donkL are both
built on the entry "donk", so they could not share a match. Renaming the bot after it joins did not stick
(Tom's PC, 2026-11-14). This script copies the entries for donk and broky under the clone ids.

    python add_clone_bot_entries.py <game>/csgo/overrides/botprofile.vpk [out.vpk]

Needs `pip install vpk`. It never overwrites the input: with no `out.vpk` it writes botprofile.vpk.new next
to it. Keep a copy of the original, then replace the file while CS2 is closed. The clone profiles must name
the same bot in `stand_in_bot` (donk_v1 -> "donk_v1", donkL -> "donkL", and so on).
"""

import os
import re
import shutil
import sys
import tempfile

import vpk

# existing bot entry -> the clone ids that get a copy of it
COPIES = {"donk": ["donk_v1", "donkL"], "broky": ["broky_v1", "brokyL"]}


def main(src: str, dst: str) -> None:
    archive = vpk.open(src)
    files = {name: archive[name].read() for name in archive}
    db = files["botprofile.db"].decode("utf-8", "surrogateescape")
    added = ""
    for player, clone_ids in COPIES.items():
        block = re.search(r'^(\S+) "%s"[^\n]*\n(?:(?!^End\b).*\n)*?End[^\n]*\n' % re.escape(player), db, re.M)
        if not block:
            raise SystemExit(f"No entry named {player!r} in botprofile.db")
        for clone_id in clone_ids:
            if re.search(r'^\S+ "%s"' % re.escape(clone_id), db, re.M):
                continue  # already added
            added += block.group(0).replace(f'"{player}"', f'"{clone_id}"', 1)
    if not added:
        raise SystemExit("All clone entries are already present; nothing to do.")
    files["botprofile.db"] = (db + ("" if db.endswith("\n") else "\n")
                              + "\n// Clone names (HackUTA): same settings as donk and broky, distinct names.\n"
                              + added).encode("utf-8", "surrogateescape")
    with tempfile.TemporaryDirectory() as tmp:
        for name, data in files.items():
            path = os.path.join(tmp, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as out:
                out.write(data)
        vpk.new(tmp).save(dst)
    check = vpk.open(dst)  # version 2, like the original
    assert check.version == archive.version and all(check[n].read() == files[n] for n in files), "verify failed"
    print(f"wrote {dst}: {len(files)} files, archive version {check.version}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    source = sys.argv[1]
    main(source, sys.argv[2] if len(sys.argv) > 2 else source + ".new")
