"""Tests for add_clone_bot_entries.patch_db on a small botprofile.db. Run: python -m pytest clone-director/tools"""
import re

from add_clone_bot_entries import HUMAN_AIM, patch_db

SAMPLE = """Default
\tSkill = 100
End

ProTop+RiflePro+RiflePersonality "donk"
    LookAngleMaxAccelAttacking = 99999999999999999999.9.9.9
    LookAngleStiffnessAttacking = 3000.0
End
ProSlow+SniperPro+SniperPersonality "broky"
\tVoicePitch = 90
End
ProSteady+RiflePro+RiflePersonality "zont1x"
\tLookAngleStiffnessAttacking = 1150.0
End
"""


def entry(db: str, name: str) -> str:
    return re.search(r'^\S+ "%s"[^\n]*\n(?:(?!^End\b).*\n)*?End[^\n]*\n' % name, db, re.M).group(0)


def setting(block: str, key: str) -> str:
    return re.search(r"^\s*%s = (\S+)$" % key, block, re.M).group(1)


def test_clone_entries_get_human_aim_and_originals_stay():
    db = patch_db(SAMPLE, HUMAN_AIM)
    for clone_id in ("donk_v1", "donkL", "broky_v1", "brokyL"):
        block = entry(db, clone_id)
        assert block.startswith(("ProTop", "ProSlow"))          # keeps the original templates
        for key, value in HUMAN_AIM.items():
            assert setting(block, key) == value
        assert block.count("LookAngleMaxAccelAttacking") == 1   # replaced, not duplicated
    assert "99999999999999999999.9.9.9" in entry(db, "donk")    # the original entry is unchanged
    assert entry(db, "zont1x") == entry(SAMPLE, "zont1x")


def test_running_twice_replaces_clone_entries_instead_of_adding_more():
    once = patch_db(SAMPLE, HUMAN_AIM)
    twice = patch_db(once, HUMAN_AIM)
    assert twice == once
    assert len(re.findall(r'^\S+ "donkL"', twice, re.M)) == 1


def test_plain_copies_keep_the_original_settings():
    db = patch_db(SAMPLE, None)
    assert setting(entry(db, "donkL"), "LookAngleStiffnessAttacking") == "3000.0"
    # A file already patched with human aim can be turned back into plain copies.
    back = patch_db(patch_db(SAMPLE, HUMAN_AIM), None)
    assert back == db
