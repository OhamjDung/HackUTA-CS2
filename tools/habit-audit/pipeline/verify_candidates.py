"""Compare SAME-input before/after builds; never read adaptation holdouts.
Run using clone-pipeline's uv environment; see README.md in this directory.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'clone-pipeline'))
from clone_pipeline.parse import load_match, is_combat_weapon
from clone_pipeline.habits import opening_inventory, PRIMARY_GUNS, buy_plan
from clone_pipeline.routes import buy_type


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024**2), b''): h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--raw-dir', type=Path, required=True)
    p.add_argument('--games', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--candidates', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    games = json.loads(a.games.read_text())
    evidence = []
    for who, mid, shard, stem, split in games:
        if split != 'train': continue
        if mid in {'2393226', '2393242', '2393024'}:
            raise ValueError('Unverified identity/holdout cannot enter build evidence')
        file = a.raw_dir/who/f'{mid}_{stem}.dem'
        m = load_match(file, who)
        for side in ['T','CT']:
            rounds = m.rounds[m.rounds.side == side]
            selected = m.shots[m.shots['round'].isin(rounds['round'])]
            shots = Counter(selected.loc[selected.weapon.map(is_combat_weapon).astype(bool),'weapon'])
            opening, missing, empty = {}, 0, 0
            for r in rounds.itertuples():
                inv = opening_inventory(m, r.round)
                if inv is None: missing += 1; continue
                empty += not bool(inv)
                key = buy_type(r.round, r.equip_value)
                opening.setdefault(key, Counter()).update(inv & PRIMARY_GUNS)
            evidence.append(dict(player=who, steam_id=m.steam_id, match_id=mid, split='train',side=side,
                rounds=len(rounds), missing_opening_inventory=missing, empty_opening_inventory=empty,
                opening_primaries={k:dict(v) for k,v in opening.items()},
                shots=dict(shots),gun_shot_count=sum(shots.values()),file=file.name,sha256=sha(file)))
    comparisons = {}
    for who in ['donk','broky']:
        cid=f'{who}_v1'
        before=json.loads((a.baseline/f'{cid}.json').read_text())
        after=json.loads((a.candidates/f'{cid}.json').read_text())
        changed=[k for k in before if before[k]!=after[k]]
        unexpected=set(changed)-{'weapons','buy_plan','built_at'}
        if unexpected: raise AssertionError(f'Unexpected same-input changes: {unexpected}')
        b_routes = {f.relative_to(a.baseline/cid):sha(f) for f in (a.baseline/cid/'routes').rglob('*.json.br')}
        a_routes = {f.relative_to(a.candidates/cid):sha(f) for f in (a.candidates/cid/'routes').rglob('*.json.br')}
        if b_routes != a_routes: raise AssertionError('Route payloads changed on same input')
        b_text=(a.baseline/cid/'botprofile.txt').read_text()
        a_text=(a.candidates/cid/'botprofile.txt').read_text()
        strip=lambda s: '\n'.join(x for x in s.splitlines() if 'WeaponPreference' not in x)
        if strip(b_text)!=strip(a_text):raise AssertionError('Non-weapon botprofile settings changed')
        comparisons[who]=dict(changed_profile_keys=changed,weapons_before=before['weapons'],weapons_after=after['weapons'],
            plans_before=before['buy_plan'],plans_after=after['buy_plan'],identical_route_payloads=len(a_routes),
            nonweapon_botprofile_identical=True,source_matches=[x['match_id'] for x in after['source_games']],
            rounds=after['rounds'],similarity=after['similarity'])
    report=dict(data_credit='Julien Blanchon / OpenCS2, CC BY 4.0. Tournament recordings retain organizer terms.',
        parser='demoparser2 0.42.2',selection_sha256=sha(a.games),raw_training_evidence=evidence,
        comparisons=comparisons,limits=['No CS2 purchases or botplay tested.',
        'Price table is a static conservative policy assumption, not a queried current game price table.',
        'Full AWP costs $4750 before armor; Director full starts at $4000. Static schema cannot guarantee affordability.',
        'First live tick possession measures opening loadout, not all later pickups or whole-round role.',
        'No held-out data enters candidate builds or purchase-policy selection.'])
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({k:{x:v for x,v in r.items() if x not in {'plans_before','plans_after'}} for k,r in comparisons.items()},indent=2))

if __name__=='__main__':main()
