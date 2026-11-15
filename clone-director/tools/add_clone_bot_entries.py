"""Add one bot entry per clone to the bot base's packed profile file, with human aim limits.

Why one entry per clone: the game takes a bot's name from an entry in botprofile.db (inside
botprofile.vpk), and refuses a second bot whose name is already in the game ("donk is already in the
game"). donk_v1 and donkL are both built on the entry "donk", so they could not share a match.
Renaming the bot after it joins did not stick (Tom's PC, 2026-11-14). This script copies the entries
for donk and broky under the clone ids.

Why human aim limits (added 2026-11-15, clone-model/ROUND3_DESIGN.md section 6, step 1): the bot
base's donk and broky entries have no limit on view acceleration and zero reaction time, so the
clones snapped onto targets like an aimbot. The copies named in HUMAN_AIM_IDS (donkL2 and brokyL2, the
new versions) get finite settings instead (HUMAN_AIM). donk_v1, donkL, broky_v1 and brokyL stay plain
copies, so earlier versions keep behaving as they did and versions can be compared. The original donk
and broky entries are left unchanged.

    python add_clone_bot_entries.py <game>/csgo/overrides/botprofile.vpk [out.vpk]
    python add_clone_bot_entries.py --plain ...   # every copy without the aim limits

Needs `pip install vpk`. It never overwrites the input: with no `out.vpk` it writes botprofile.vpk.new
next to it. Keep a copy of the original, then replace the file while CS2 is closed. Running it again on
a file that already has clone entries replaces those entries. The clone profiles must name the same bot
in `stand_in_bot` (donk_v1 -> "donk_v1", donkL -> "donkL", and so on).
"""

import os
import re
import sys
import tempfile

# existing bot entry -> the clone ids that get a copy of it
COPIES = {"donk": ["donk_v1", "donkL", "donkL2"], "broky": ["broky_v1", "brokyL", "brokyL2"]}
# the copies that get human aim settings; the others stay plain copies of the original entry
HUMAN_AIM_IDS = {"donkL2", "brokyL2"}

# Starting values chosen by simulating the bot's view as a damped spring with capped acceleration
# (the model in the original Counter-Strike bot code; assumed, not confirmed, to hold in CS2). With these,
# a 45 degree flick settles in about 0.34 s (human median 0.36 s), turning stays under 1,200 deg/s even for
# 150 degrees, and acceleration stays at or under 20,000 deg/s^2 (elite pros measured up to 34,400).
# ReactionTime, AttackDelay and the AimFocus values are not simulated: they are starting points to be
# tuned by measuring recorded matches with `clone_pipeline.limits check`.
HUMAN_AIM = {
    "LookAngleMaxAccelNormal": "12000.0",
    "LookAngleStiffnessNormal": "300.0",
    "LookAngleDampingNormal": "35.0",
    "LookAngleMaxAccelAttacking": "20000.0",
    "LookAngleStiffnessAttacking": "600.0",
    "LookAngleDampingAttacking": "60.0",
    "ReactionTime": "0.18",
    "AttackDelay": "0.05",
    "AimFocusInitial": "1.5",
    "AimFocusDecay": "0.2",
    "AimFocusOffsetScale": "0.12",
    "AimfocusInterval": "0.25",
}
MARKER = "// Clone names (HackUTA)"


def entry_pattern(name: str) -> re.Pattern:
    """One entry: a header line naming the bot in quotes, its settings, and the closing End line."""
    return re.compile(r'^(\S+) "%s"[^\n]*\n(?:(?!^End\b).*\n)*?End[^\n]*\n' % re.escape(name), re.M)


def with_settings(block: str, settings: dict) -> str:
    """Set each setting inside one entry: replace the line if it exists, otherwise add it before End."""
    lines = block.splitlines(keepends=True)
    seen = set()
    for i, line in enumerate(lines):
        match = re.match(r"(\s*)(\w+)\s*=", line)
        if match and match.group(2) in settings:
            lines[i] = f"{match.group(1)}{match.group(2)} = {settings[match.group(2)]}\n"
            seen.add(match.group(2))
    end = next(i for i in range(len(lines) - 1, -1, -1) if lines[i].startswith("End"))
    missing = [f"\t{key} = {value}\n" for key, value in settings.items() if key not in seen]
    return "".join(lines[:end] + missing + lines[end:])


def patch_db(db: str, settings: dict | None) -> str:
    """Return botprofile.db text with one fresh entry per clone. Existing clone entries are replaced."""
    for clone_ids in COPIES.values():
        for clone_id in clone_ids:
            db = entry_pattern(clone_id).sub("", db)
    db = re.sub(r"\n*" + re.escape(MARKER) + r"[^\n]*\n", "\n", db)
    added = ""
    for player, clone_ids in COPIES.items():
        block = entry_pattern(player).search(db)
        if not block:
            raise SystemExit(f"No entry named {player!r} in botprofile.db")
        for clone_id in clone_ids:
            copy = block.group(0).replace(f'"{player}"', f'"{clone_id}"', 1)
            added += with_settings(copy, settings) if settings and clone_id in HUMAN_AIM_IDS else copy
    note = " (" + ", ".join(sorted(HUMAN_AIM_IDS)) + " with human aim limits)" if settings else ""
    return (db.rstrip("\n") + "\n\n" + MARKER + ": copies of donk and broky under the clone ids"
            + note + ".\n" + added)


def main(src: str, dst: str, plain: bool) -> None:
    import vpk
    archive = vpk.open(src)
    files = {name: archive[name].read() for name in archive}
    db = files["botprofile.db"].decode("utf-8", "surrogateescape")
    files["botprofile.db"] = patch_db(db, None if plain else HUMAN_AIM).encode("utf-8", "surrogateescape")
    with tempfile.TemporaryDirectory() as tmp:
        for name, data in files.items():
            path = os.path.join(tmp, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as out:
                out.write(data)
        vpk.new(tmp).save(dst)
    check = vpk.open(dst)  # version 2, like the original
    assert check.version == archive.version and all(check[n].read() == files[n] for n in files), "verify failed"
    print(f"wrote {dst}: {len(files)} files, archive version {check.version}, "
          f"{'plain copies' if plain else 'human aim limits'}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--plain"]
    if not args:
        raise SystemExit(__doc__)
    main(args[0], args[1] if len(args) > 1 else args[0] + ".new", "--plain" in sys.argv[1:])
