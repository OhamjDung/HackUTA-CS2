"""Authored persona coverage and native installation controls, no CS2 claim."""
import json
from pathlib import Path
import pytest
from make_odyssey_profiles import IDS, make_profile
from add_clone_bot_entries import HUMAN_AIM, odyssey_settings, patch_db
from test_add_clone_bot_entries import SAMPLE, entry, setting

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("name", IDS)
def test_all_quirks_point_to_real_controls_and_authored_files_are_reproducible(name):
    p = json.loads((ROOT / "clones" / (name + ".json")).read_text())
    assert p == make_profile(name)
    qs = p['odyssey']['quirks']
    assert len(qs) >= 14 and len({q['id'] for q in qs}) == len(qs)
    for q in qs:
        value = p
        for part in q['control'].split('.'): value = value[part]
        assert value is not None and q['effect']
    assert p['model'] is None and p['source_games'] == []
    assert p['routes'] == {'T': [], 'CT': []}  # never disguise a pro's recorded route as the character


def test_native_entries_have_distinct_difficulties_and_plain_keeps_them():
    desired = odyssey_settings()
    for limits in [HUMAN_AIM, None]:
        db = patch_db(SAMPLE, limits)
        for name in IDS:
            for key, value in desired[name].items(): assert setting(entry(db, name), key) == value
        assert [float(setting(entry(db, n), 'Skill')) for n in IDS] == [100, 100, 65, 20]
        assert patch_db(db, limits) == db
        assert entry(db, 'donk') == entry(SAMPLE, 'donk')
        assert entry(db, 'broky_v2') == entry(SAMPLE, 'broky').replace('"broky"', '"broky_v2"', 1)


def test_no_silent_fallback_when_persona_config_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError): odyssey_settings(tmp_path)
