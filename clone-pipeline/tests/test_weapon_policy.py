"""Role extraction regressions use synthetic inventories, not held-out policy tuning."""
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from clone_pipeline import habits, build
from clone_pipeline.parse import resolve_player
from tests.test_pipeline import fake_match


def sample(inventories, side='T', kind='full'):
    m = fake_match()
    rows, ticks = [], []
    equip = {'full': 6000, 'force': 2500, 'eco': 800, 'pistol': 800}[kind]
    for i, inventory in enumerate(inventories):
        n = 1 if kind == 'pistol' and i == 0 else i + 2
        rows.append({'round': n, 'freeze_end': 1000+i*100, 'end': 1099+i*100,
                     'winner': side, 'side': side, 'equip_value': equip})
        ticks.append({'round': n, 'tick': 1001+i*100, 'is_alive': True,
                      'inventory': inventory, 'item_def_idx': 42})  # active knife
    m.rounds, m.ticks = pd.DataFrame(rows), pd.DataFrame(ticks)
    m.purchases = pd.DataFrame(columns=['tick','item_name','round'])
    return m


def test_retained_awp_beats_rifle_shots_without_new_purchases():
    m = sample([['Knife','AWP'], ['Knife','AWP','AWP'], ['Knife','AK-47']])
    m.shots = pd.DataFrame({'weapon': ['weapon_ak47']*30+['weapon_awp'], 'round':[2]*31})
    assert habits.weapon_preferences([m])[0] == 'awp'
    assert habits.buy_plan([m])['T']['full']['aliases'] == ['awp']


def test_rifle_role_stays_rifle_and_dropped_inventory_is_not_opening():
    m = sample([['Knife','AK-47'], ['Knife','AK-47'], ['AWP']])
    later = m.ticks.iloc[0].copy()
    later['tick'], later['inventory'] = 1010, ['AWP']
    m.ticks = pd.concat([m.ticks, pd.DataFrame([later])], ignore_index=True)
    assert habits.weapon_preferences([m])[0] == 'ak47'
    assert habits.buy_plan([m])['T']['full']['aliases'] == ['ak47']


def test_missing_inventory_warns_and_falls_back_to_purchase():
    m = sample([None])
    m.shots = pd.DataFrame(columns=['weapon','round'])
    m.purchases = pd.DataFrame({'round':[2,2], 'item_name':['AK-47','Smoke Grenade']})
    with pytest.warns(RuntimeWarning, match='purchase-frequency'):
        assert habits.buy_plan([m])['T']['full']['aliases'] == ['ak47','smokegrenade']
    with pytest.warns(RuntimeWarning, match='missing'):
        assert habits.weapon_preferences([m]) == []


def test_known_empty_inventory_does_not_invent_possession_from_drop_purchases():
    m = sample([[]])
    m.purchases = pd.DataFrame({'round':[2], 'item_name':['AWP']})
    assert habits.opening_inventory(m, 2) == set()
    assert habits.buy_plan([m])['T']['full']['aliases'] == []


def test_late_or_dead_inventory_is_missing():
    m = sample([['AWP']])
    m.ticks.loc[0,'tick'] = 1003
    assert habits.opening_inventory(m, 2) is None
    m.ticks.loc[0,'tick'], m.ticks.loc[0,'is_alive'] = 1001, False
    assert habits.opening_inventory(m, 2) is None


@pytest.mark.parametrize('side,allowed,illegal',[('T','AK-47','M4A4'),('CT','M4A4','AK-47')])
def test_side_legal_one_primary_and_order(side, allowed, illegal):
    m = sample([[allowed,illegal], [illegal]],side=side)
    m.purchases = pd.DataFrame({'round':[2,2,3,3],
                              'item_name':['Smoke Grenade','Kevlar Vest','Smoke Grenade','Kevlar Vest']})
    plan=habits.buy_plan([m])[side]['full']
    assert plan['items']==[allowed,'Kevlar Vest','Smoke Grenade']
    assert set(plan)=={'items','aliases','unmapped_items','rounds_of_this_type','share_of_rounds_bought'}


def test_force_never_promotes_retained_awp_and_uses_affordable_observed_primary():
    m=sample([['AWP'],['Galil AR']],kind='force')
    assert habits.buy_plan([m])['T']['force']['aliases']==['galilar']
    m=sample([['AWP']],kind='force')
    assert habits.buy_plan([m])['T']['force']['aliases']==[]
    m.purchases=pd.DataFrame({'round':[2], 'item_name':['MAC-10']})
    assert habits.buy_plan([m])['T']['force']['aliases']==['mac10']


def test_pistol_and_eco_never_promote_awp():
    for kind in ['pistol','eco']:
        m=sample([['AWP']],kind=kind)
        assert habits.buy_plan([m])['T'][kind]['aliases']==[]


def test_identity_resolution_rejects_namesakes_and_wrong_canonical_ids():
    info=pd.DataFrame({'name':['someone','someone','donk'], 'steamid':['76561198000000001','76561198000000002','76561198018303780']})
    with pytest.raises(ValueError,match='ambiguous'): resolve_player(info,'someone')
    with pytest.raises(ValueError,match='Missing'): resolve_player(info,'donk')
    assert resolve_player(info,'76561198000000002')==('76561198000000002','someone')


def test_build_never_uses_held_out_weapon_for_policy(monkeypatch,tmp_path):
    train=fake_match(); train.match_id='train'
    held=deepcopy(train); held.match_id='holdout'
    held.shots=pd.DataFrame({'weapon':['weapon_awp']*100,'round':[2]*100})
    lookup={'train':train,'holdout':held}
    monkeypatch.setattr(build,'load_match',lambda path, player: lookup[str(path)])
    monkeypatch.setattr(build,'write_recording',lambda ticks,path: len(ticks)-1)
    with pytest.warns(RuntimeWarning):
        p=build.build_clone('me',[Path('train'),Path('holdout')],{'holdout'},'me',tmp_path)
    assert p['weapons']==['ak47']
    assert [s['match_id'] for s in p['source_games']]==['train']
    held.steam_id='different'
    with pytest.raises(ValueError,match='same Steam ID'):
        build.build_clone('me',[Path('train'),Path('holdout')],{'holdout'},'me',tmp_path)
