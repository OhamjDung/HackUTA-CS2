"""CPU-only observational audit of CS-NET parser JSON, not live/game/model evidence.

Uses the source format already consumed by clone-model/prepare.py. It deliberately does
not treat sparse parser JSON as demoparser2 Match tables or infer freeze-end inventory.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

PLAYERS = {"donk": "76561198386265483", "broky": "76561198201620490"}
HOLDOUTS = {"2393242", "2393024"}
PRIMARY = {"AK-47", "M4A4", "M4A1-S", "AWP", "Galil AR", "FAMAS", "SSG 08", "AUG", "SG 553",
           "MAC-10", "MP9", "MP7", "MP5-SD", "UMP-45", "P90", "PP-Bizon", "Nova", "XM1014",
           "MAG-7", "Sawed-Off", "Negev", "M249"}
PISTOLS = {"Glock-18", "USP-S", "P2000", "Desert Eagle", "Dual Berettas", "Five-SeveN", "Tec-9",
           "P250", "CZ75-Auto", "R8 Revolver"}
METHOD = {
    "version": 1,
    "source": "CS-NET parser JSON; OpenCS2 professional source recordings, not bot traces",
    "intervals": "left sample held until next sample; positive elapsed round_seconds; no tail extrapolation; clip at death event",
    "alive": "only intervals whose left sample is alive; no pre-first-sample extrapolation",
    "possession": "deduplicated inventory primary names per interval; unknown inventory is missing, empty list known empty",
    "opening_inventory": "first KNOWN alive sampled inventory; may be delayed if early inventory missing; explicitly not freeze-end; count per primary per round",
    "shots": "events.sound ty=fire with target roster index and gun weapon ID, live to last sample; counts distinct events",
    "kills": "events.kills attacker roster index with valid victim and weapon; live to last sample",
    "speed": "horizontal position difference / actual elapsed seconds, not parser v/vx/vy arrays",
    "pause_threshold_units_per_second": 10.0,
    "turn": "absolute shortest wrapped yaw difference / elapsed seconds; interval-weighted degrees/s",
    "position": "left-sample horizontal 64-unit occupied grid cells and per-file named places, weighted seconds",
    "opening": "observed interval until first target damage dealt/taken, death, 20s or last sample; omitted first 0.5s typical",
    "splits": "canonical IDs; seven build matches; two whole-match holdouts described only after method/policy lock",
    "uncertainty": "descriptive per-match ranges, not independent-tick statistical confidence or skill estimates",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def method_hash() -> str:
    return hashlib.sha256(json.dumps(METHOD, sort_keys=True).encode()).hexdigest()


def finite(x):
    return isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x)


def inverse(mapping, label):
    if not isinstance(mapping, dict) or any(not isinstance(k, str) or not isinstance(v, int) or isinstance(v, bool) for k, v in mapping.items()):
        raise ValueError(f"Invalid {label} map")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError(f"Duplicate {label} IDs")
    return {v: k for k, v in mapping.items()}


def decoded(mapping, value):
    return mapping.get(value) if isinstance(value, int) and not isinstance(value, bool) else None


def index_for(data, steam_id):
    ids = [str(p.get('steamid')) for p in data.get('players', [])]
    if len(ids) != len(set(ids)) or ids.count(steam_id) != 1:
        raise ValueError('Missing or duplicate canonical Steam ID / ambiguous roster')
    return ids.index(steam_id)


def value_at(player, key, i):
    seq = player.get(key)
    return seq[i] if isinstance(seq, list) and i < len(seq) else None


def weighted_quantile(samples, q):
    if not samples:
        return None
    samples = sorted(samples)
    cutoff = sum(w for _, w in samples) * q
    running = 0
    for v, w in samples:
        running += w
        if running >= cutoff:
            return v
    return samples[-1][0]


def share(n, d):
    return n / d if d else None


def valid_index(x, n):
    return isinstance(x, int) and not isinstance(x, bool) and 0 <= x < n


def round_metrics(data, rnd, player_index):
    """Measure one aligned round. Source round IDs are zero-based; no joining by name."""
    weapons, places = inverse(data['weapons'], 'weapon'), inverse(data.get('places', {}), 'place')
    nplayers = len(data['players'])
    if len(rnd.get('players', [])) != nplayers or len(rnd.get('teams', [])) != nplayers:
        raise ValueError('Round roster not aligned with metadata')
    side = rnd['teams'][player_index]
    if side not in ('T', 'CT'):
        raise ValueError('Target not on playing side')
    times, ticks = rnd.get('round_seconds', []), rnd.get('ticks', [])
    if len(times) < 2 or len(times) != len(ticks) or any(not finite(t) for t in times + ticks):
        raise ValueError('Missing or invalid time axis')
    if times[0] < 0 or any(b <= a for a, b in zip(times, times[1:])) or any(b <= a for a,b in zip(ticks,ticks[1:])):
        raise ValueError('Time axis must strictly increase and start nonnegative')
    if not isinstance(rnd.get('id'), int):
        raise ValueError('Missing integer source round ID')
    p = rnd['players'][player_index]
    freeze = ticks[0] - times[0] * 64
    events = rnd.get('events') or {}
    missing = Counter()
    invalid_events = Counter()
    death, contact = None, None
    kills, shots = Counter(), Counter()
    def event_time(e):
        if not finite(e.get('t')):
            return None
        t = (e['t'] - freeze) / 64
        return t if 0 <= t <= times[-1] else None
    for key in ('kills', 'damage', 'sound'):
        if key not in events:
            missing['events_' + key] += 1
    for e in events.get('kills', []):
        if not isinstance(e, dict):
            invalid_events['kills'] += 1
            continue
        t = event_time(e)
        if t is None:
            continue
        if not valid_index(e.get('v'), nplayers) or not (valid_index(e.get('a'), nplayers) or e.get('a') == -1):
            invalid_events['kills'] += 1
            continue
        if e['v'] == player_index:
            death = min(death, t) if death is not None else t
        if e['a'] == player_index:
            weapon = decoded(weapons, e.get('w'))
            if weapon is None:
                invalid_events['kill_weapon'] += 1
            else:
                kills[weapon] += 1
    for e in events.get('damage', []):
        if not isinstance(e, dict):
            invalid_events['damage'] += 1
            continue
        t = event_time(e)
        if t is not None and player_index in (e.get('a'), e.get('v')):
            if not valid_index(e.get('v'), nplayers) or not (valid_index(e.get('a'), nplayers) or e.get('a') == -1):
                invalid_events['damage'] += 1
                continue
            contact = min(contact, t) if contact is not None else t
    for e in events.get('sound', []):
        if not isinstance(e, dict):
            invalid_events['sound'] += 1
            continue
        if e.get('ty') == 'fire' and not valid_index(e.get('p'), nplayers):
            invalid_events['sound_player'] += 1
            continue
        if e.get('ty') == 'fire' and e.get('p') == player_index and event_time(e) is not None:
            w = decoded(weapons, e.get('w'))
            if w is None:
                invalid_events['shot_weapon'] += 1
            elif w in PRIMARY | PISTOLS:
                shots[w] += 1
    possessed_seconds, active_seconds, area_seconds, cells_seconds = Counter(), Counter(), Counter(), Counter()
    seen_primaries, first_inventory = set(), None
    alive_seconds = inv_seconds = active_known_seconds = area_known_seconds = position_known_seconds = 0.0
    speed_samples, turn_samples = [], []
    opening_seconds = 0.0
    limit = min([20.0, times[-1]] + ([contact] if contact is not None else []) + ([death] if death is not None else []))
    for i, (t, nxt) in enumerate(zip(times, times[1:])):
        alive = value_at(p, 'alive', i)
        if not isinstance(alive, bool):
            missing['alive_samples'] += 1
            continue
        if not alive:
            continue
        stop = min(nxt, death) if death is not None else nxt
        dt = max(0.0, stop - t)
        if dt <= 0:
            continue
        alive_seconds += dt
        opening_seconds += max(0.0, min(stop, limit) - t)
        inv = value_at(p, 'inventory', i)
        if isinstance(inv, list) and all(isinstance(w, int) and not isinstance(w, bool) and w in weapons for w in inv):
            known = {weapons[w] for w in inv} & PRIMARY
            if first_inventory is None:
                first_inventory = {'seconds': t, 'primaries': sorted(known)}
            inv_seconds += dt
            seen_primaries.update(known)
            for w in known:
                possessed_seconds[w] += dt
        else:
            missing['inventory_samples'] += 1
        active = decoded(weapons, value_at(p, 'weapon', i))
        if active is not None:
            active_known_seconds += dt
            active_seconds[active] += dt
        else:
            missing['active_weapon_samples'] += 1
        area = decoded(places, value_at(p, 'place', i))
        if area is not None:
            area_known_seconds += dt
            area_seconds[area] += dt
        else:
            missing['place_samples'] += 1
        x, y = value_at(p, 'x', i), value_at(p, 'y', i)
        nx, ny = value_at(p, 'x', i+1), value_at(p, 'y', i+1)
        if finite(x) and finite(y):
            position_known_seconds += dt
            cells_seconds[f'{math.floor(x/64)},{math.floor(y/64)}'] += dt
        else:
            missing['position_samples'] += 1
        # Do not derive movement into a dead/missing endpoint or an endpoint after death.
        if all(finite(v) for v in (x, y, nx, ny)) and value_at(p, 'alive', i+1) is True and (death is None or nxt <= death):
            speed_samples.append((math.hypot(nx-x, ny-y)/(nxt-t), dt))
        else:
            missing['speed_intervals'] += 1
        yaw, nyaw = value_at(p, 'yaw', i), value_at(p, 'yaw', i+1)
        if finite(yaw) and finite(nyaw) and value_at(p, 'alive', i+1) is True and (death is None or nxt <= death):
            turn_samples.append((abs((nyaw-yaw+180)%360-180)/(nxt-t), dt))
        else:
            missing['yaw_intervals'] += 1
    return dict(source_round_id_zero_based=rnd['id'], pipeline_round_number_one_based=rnd['id']+1,
        side=side, samples=len(times), first_sample_seconds=times[0], last_sample_seconds=times[-1],
        missing_start_seconds=times[0], sampled_alive_seconds=alive_seconds,
        known_inventory_alive_seconds=inv_seconds, known_active_weapon_alive_seconds=active_known_seconds,
        known_place_alive_seconds=area_known_seconds, known_position_alive_seconds=position_known_seconds,
        primary_seen_anytime=sorted(seen_primaries), first_sampled_inventory=first_inventory,
        primary_possession_seconds=dict(possessed_seconds), active_weapon_seconds=dict(active_seconds),
        gun_shots=dict(shots), kill_weapons=dict(kills), area_seconds=dict(area_seconds), occupied_cell_seconds=dict(cells_seconds),
        first_contact_seconds=contact, death_seconds=death, observed_opening_seconds=opening_seconds,
        opening_end_seconds=limit, observed_opening_share_of_alive_time=share(opening_seconds, alive_seconds),
        missing=dict(missing), invalid_events=dict(invalid_events), _speed=speed_samples, _turn=turn_samples)


def summarize(rows):
    result = dict(rounds=len(rows), matches=len({r['match_id'] for r in rows}),
        match_ids=sorted({r['match_id'] for r in rows}))
    for k in ('sampled_alive_seconds', 'known_inventory_alive_seconds', 'known_active_weapon_alive_seconds',
              'known_place_alive_seconds', 'known_position_alive_seconds', 'observed_opening_seconds', 'missing_start_seconds'):
        result[k] = sum(r[k] for r in rows)
    for k in ('primary_possession_seconds','active_weapon_seconds','gun_shots','kill_weapons','area_seconds','occupied_cell_seconds','missing','invalid_events'):
        c = Counter()
        for r in rows:
            c.update(r[k])
        result[k] = dict(c.most_common())
    counts = Counter(w for r in rows for w in r['primary_seen_anytime'])
    result['primary_possession_rounds_anytime'] = dict(counts.most_common())
    result['rounds_with_any_known_inventory'] = sum(r['known_inventory_alive_seconds']>0 for r in rows)
    counts = Counter(w for r in rows if r['first_sampled_inventory'] is not None for w in r['first_sampled_inventory']['primaries'])
    result['sampled_opening_primary_rounds'] = dict(counts.most_common())
    result['sampled_opening_inventory_rounds_known'] = sum(r['first_sampled_inventory'] is not None for r in rows)
    result['rounds_inventory_known_at_first_sample'] = sum(r['first_sampled_inventory'] is not None and r['first_sampled_inventory']['seconds'] == r['first_sample_seconds'] for r in rows)
    result['first_known_inventory_seconds'] = [r['first_sampled_inventory']['seconds'] for r in rows if r['first_sampled_inventory'] is not None]
    for key, prefix in (('_speed','horizontal_speed'),('_turn','yaw_turn_rate')):
        samples = [p for r in rows for p in r[key]]
        seconds = sum(w for _,w in samples)
        result[prefix] = dict(known_seconds=seconds, mean=share(sum(v*w for v,w in samples),seconds),
            p10=weighted_quantile(samples,.1), median=weighted_quantile(samples,.5), p90=weighted_quantile(samples,.9))
        if key == '_speed':
            result['pause_share'] = share(sum(w for v,w in samples if v < METHOD['pause_threshold_units_per_second']), seconds)
    result['observed_opening_share_of_alive_time'] = share(result['observed_opening_seconds'],result['sampled_alive_seconds'])
    result['awp_possession_share_of_known_inventory_time'] = share(result['primary_possession_seconds'].get('AWP',0),result['known_inventory_alive_seconds'])
    return result


def selection(games, split):
    seen, result = set(), []
    for entry in games:
        if len(entry) != 5:
            raise ValueError('Expected five-column game tuple')
        name, mid, _, _, declared = entry
        mid = str(mid)
        if name not in PLAYERS or mid in seen or mid == '2393226' or declared not in ('train','test'):
            raise ValueError('Unverified player, excluded/duplicate match, or invalid split')
        if (mid in HOLDOUTS) != (declared == 'test'):
            raise ValueError('Holdout split mismatch')
        seen.add(mid)
        if declared == split:
            result.append(entry)
    if not result:
        raise ValueError('Empty selected split')
    return result


def run(json_dir, games_path, out, split='train', method_lock=None, clones_dir=None):
    out = Path(out)
    if split == 'test':
        if method_lock is None:
            raise ValueError('Holdout requires --method-lock after train methodology and pipeline policy are frozen')
        lock = json.loads(Path(method_lock).read_text())
        if lock.get('method_sha256') != method_hash() or lock.get('audit_source_sha256') != digest(Path(__file__)) or lock.get('pipeline_policy_frozen') is not True:
            raise ValueError('Method/code mismatch or pipeline policy not frozen')
        if (out/'audit.json').exists():
            raise ValueError('Holdout output exists: refusing another descriptive audit')
    games_path, json_dir = Path(games_path), Path(json_dir)
    games = selection(json.loads(games_path.read_text()),split)
    rows, inputs = [], []
    for name, mid, shard, stem, declared in games:
        path = json_dir/f'{mid}.json.gz'
        with gzip.open(path,'rt',encoding='utf-8') as stream:
            data = json.load(stream)
        if data.get('map') != 'de_mirage' or not data.get('rounds'):
            raise ValueError(f'Wrong map or empty source: {mid}')
        ix = index_for(data,PLAYERS[name])
        ids = [r.get('id') for r in data['rounds']]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate source round IDs')
        inputs.append(dict(player=name,steam_id=PLAYERS[name],match_id=mid,split=declared,path=str(path.resolve()),sha256=digest(path),shard=shard,stem=stem))
        for rnd in data['rounds']:
            rows.append(dict(player=name,steam_id=PLAYERS[name],match_id=mid,split=declared,**round_metrics(data,rnd,ix)))
    groups = []
    for name, side in sorted({(r['player'],r['side']) for r in rows}):
        group = [r for r in rows if r['player']==name and r['side']==side]
        summary = dict(player=name,side=side,split=split,**summarize(group))
        per_match = [dict(match_id=mid,**summarize([r for r in group if r['match_id']==mid])) for mid in summary['match_ids']]
        summary['by_match'] = per_match
        awp = [m['awp_possession_share_of_known_inventory_time'] for m in per_match if m['awp_possession_share_of_known_inventory_time'] is not None]
        summary['awp_possession_per_match_range'] = [min(awp),max(awp)] if awp else None
        if clones_dir:
            profile = json.loads((Path(clones_dir)/f'{name}_v1.json').read_text())
            summary['committed_comparison'] = dict(weapons=profile['weapons'],buy_plan=profile.get('buy_plan',{}).get(side,{}),
                note='Committed profile is historical. donk includes excluded account match 2393226; no direct before/after causal claim.')
        groups.append(summary)
    try:
        revision = subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=Path(__file__).resolve().parents[2]).strip()
    except (OSError,subprocess.CalledProcessError):
        revision = None
    report = dict(method=METHOD,method_sha256=method_hash(),audit_source_sha256=digest(Path(__file__)),source_revision=revision,
        preparation_archive_sha256='0e46914cbca514efbb5727b64f9e753116da4afaa98f764be66d15d97cb8ad25',
        source_url='https://huggingface.co/datasets/blanchon/opencs2_dataset_demo',
        games_sha256=digest(games_path),data_attribution='Julien Blanchon / OpenCS2, CC BY 4.0; tournament terms apply to recordings',
        split=split,inputs=inputs,summaries=groups,rounds=[{k:v for k,v in r.items() if not k.startswith('_')} for r in rows])
    out.mkdir(parents=True,exist_ok=True)
    (out/'audit.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    with (out/'rounds.csv').open('w',newline='') as f:
        keys=['player','steam_id','match_id','split','side','source_round_id_zero_based','pipeline_round_number_one_based',
            'first_sample_seconds','sampled_alive_seconds','known_inventory_alive_seconds','observed_opening_seconds','observed_opening_share_of_alive_time']
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows({k:r[k] for k in keys} for r in rows)
    lines=[f'# Source-recording habit audit: {split}', '', 'Observational source-player proxies only; no bot, model identity, human aim or professional skill measurement.', '',
        '| Player / side | Matches / rounds | AWP first-known inventory rounds / known | AWP held seconds / inventory-known alive seconds | Gun shots (AWP / all) | Kills (AWP / all) | Pause share | Opening / alive time |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in groups:
        fmt=lambda x: 'missing' if x is None else f'{x:.3f}'
        lines.append(f"| {s['player']} {s['side']} | {s['matches']} / {s['rounds']} | {s['sampled_opening_primary_rounds'].get('AWP',0)} / {s['sampled_opening_inventory_rounds_known']} | {s['primary_possession_seconds'].get('AWP',0):.2f} / {s['known_inventory_alive_seconds']:.2f} | {s['gun_shots'].get('AWP',0)} / {sum(s['gun_shots'].values())} | {s['kill_weapons'].get('AWP',0)} / {sum(s['kill_weapons'].values())} | {fmt(s['pause_share'])} | {fmt(s['observed_opening_share_of_alive_time'])} |")
    for s in groups:
        if s.get('committed_comparison'):
            plan=s['committed_comparison']['buy_plan'].get('full',{}).get('aliases',[])
            lines.extend(['',f"{s['player']} {s['side']} committed full-buy aliases: `{', '.join(plan)}`. Top possessed primaries by seconds: `{list(s['primary_possession_seconds'])[:3]}`. These are source observations, not proof a new buy plan will execute in CS2.",''])
    lines += ['', 'First-known inventory is not freeze-end possession: if early inventories are missing it may be delayed. JSON records each observation time and rounds with inventory known at the first sample. Fire counts are source parser sound events, not sampled shots-array sums; this is an event-count proxy pending comparison with the raw parser.', '', 'Denominators, per-match ranges, missing fields, source checksums, per-round positions/areas and metric definitions are in audit.json. One holdout match per player is weak descriptive evidence; ticks are correlated. No pre-first-sample inventory/alive time is invented; last interval is not extrapolated. Pause threshold is <10 horizontal units/s; yaw wraps at 180 degrees. Opening windows stop at damage/death/20 s and are shorter than whole-round alive time.']
    (out/'report.md').write_text('\n'.join(lines)+'\n')
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--json-dir',type=Path,required=True)
    ap.add_argument('--games',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--split',choices=['train','test'],default='train')
    ap.add_argument('--method-lock',type=Path)
    ap.add_argument('--clones-dir',type=Path,default=Path(__file__).resolve().parents[2]/'clones')
    args=ap.parse_args()
    r=run(args.json_dir,args.games,args.out,args.split,args.method_lock,args.clones_dir)
    print(json.dumps(dict(split=r['split'],matches=len(r['inputs']),rounds=len(r['rounds']),out=str(args.out))))


if __name__=='__main__':
    main()
