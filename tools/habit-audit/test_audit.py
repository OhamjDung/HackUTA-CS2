"""Synthetic sparse parser records; no raw dataset is needed."""
import copy
import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('audit',Path(__file__).with_name('audit.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def source(awp_id=1,knife_id=2):
    p = dict(x=[0,0,40,40],y=[0,0,0,0],yaw=[179,-179,-177,-177],alive=[True,True,True,False],
        inventory=[[awp_id,awp_id,knife_id],[awp_id,knife_id],[],[awp_id]],weapon=[knife_id,awp_id,knife_id,awp_id],place=[0,0,0,0])
    r = dict(id=0,teams=['CT','T'],ticks=[1032,1064,1128,1160],round_seconds=[.5,1,2,2.5],players=[p,copy.deepcopy(p)],
        events=dict(kills=[dict(t=1152,a=1,v=0,w=awp_id)],damage=[dict(t=1080,a=0,v=1)],sound=[dict(t=1060,ty='fire',p=0,w=awp_id)]))
    return dict(map='de_mirage',weapons={'AWP':awp_id,'Knife':knife_id},places={'A':0},
        players=[dict(steamid=audit.PLAYERS['broky'],name='any'),dict(steamid='123',name='broky')],rounds=[r])


class AuditTests(unittest.TestCase):
    def test_retained_awp_knife_active_dedup_and_death(self):
        d=source();r=audit.round_metrics(d,d['rounds'][0],0)
        self.assertEqual(r['primary_possession_seconds'],{'AWP':1.5})
        self.assertEqual(r['primary_seen_anytime'],['AWP'])
        self.assertEqual(r['active_weapon_seconds']['AWP'],1)
        self.assertEqual(r['sampled_alive_seconds'],1.875)  # capped at real death 2.375
        self.assertEqual(r['first_sampled_inventory'],{'seconds':.5,'primaries':['AWP']})
        self.assertEqual(r['gun_shots'],{'AWP':1})
        self.assertEqual(r['observed_opening_seconds'],.75)  # contact1.25, firstsample.5
        self.assertEqual(r['source_round_id_zero_based'],0)
        self.assertEqual(r['pipeline_round_number_one_based'],1)

    def test_weapon_maps_are_per_source(self):
        a,b=source(1,2),source(42,18)
        self.assertEqual(audit.round_metrics(a,a['rounds'][0],0),audit.round_metrics(b,b['rounds'][0],0))

    def test_wraparound_time_weighting_and_position_speed(self):
        d=source();r=audit.round_metrics(d,d['rounds'][0],0)
        self.assertEqual(r['_turn'],[(4.0,.5),(2.0,1.0)])
        s=audit.summarize([dict(match_id='1',**r)])
        self.assertAlmostEqual(s['yaw_turn_rate']['mean'],8/3)
        self.assertAlmostEqual(s['pause_share'],1/3)
        self.assertEqual(s['horizontal_speed']['median'],40)
        self.assertEqual(s['missing_start_seconds'],.5)

    def test_missing_inventory_is_not_zero_and_empty_is_known(self):
        d=source();p=d['rounds'][0]['players'][0];p['inventory']=[None,[],None,[]]
        r=audit.round_metrics(d,d['rounds'][0],0)
        self.assertEqual(r['known_inventory_alive_seconds'],1)
        self.assertEqual(r['primary_possession_seconds'],{})
        self.assertEqual(r['first_sampled_inventory'],{'seconds':1,'primaries':[]})
        self.assertEqual(r['missing']['inventory_samples'],2)
        s=audit.summarize([dict(match_id='1',**r)])
        self.assertEqual(s['rounds_inventory_known_at_first_sample'],0)

    def test_steam_id_resolution_never_uses_names(self):
        d=source();self.assertEqual(audit.index_for(d,audit.PLAYERS['broky']),0)
        d['players'][1]['steamid']=audit.PLAYERS['broky']
        with self.assertRaises(ValueError):audit.index_for(d,audit.PLAYERS['broky'])
        with self.assertRaises(ValueError):audit.index_for(source(),'missing')

    def test_unknown_ids_and_nonfinite_positions_are_missing(self):
        d=source();p=d['rounds'][0]['players'][0];p['inventory'][0]=[999];p['x'][0]=float('nan')
        r=audit.round_metrics(d,d['rounds'][0],0)
        self.assertEqual(r['missing']['inventory_samples'],1)
        self.assertEqual(r['missing']['position_samples'],1)
        json.dumps({k:v for k,v in r.items() if not k.startswith('_')},allow_nan=False)

    def test_invalid_event_fields_are_counted_not_reinterpreted(self):
        d=source();d['rounds'][0]['events']['sound'] += [dict(t=1060,ty='fire',p=False,w=1),dict(t=1060,ty='fire',p=0,w=[])]
        r=audit.round_metrics(d,d['rounds'][0],0)
        self.assertEqual(r['gun_shots'],{'AWP':1})
        self.assertEqual(r['invalid_events'],{'sound_player':1,'shot_weapon':1})

    def test_missing_events_no_combat_explicit(self):
        d=source();d['rounds'][0]['events']={}
        r=audit.round_metrics(d,d['rounds'][0],0)
        self.assertEqual(r['gun_shots'],{})
        self.assertIsNone(r['first_contact_seconds'])
        self.assertEqual(r['missing']['events_sound'],1)

    def test_invalid_time_and_roster_rejected(self):
        d=source();d['rounds'][0]['round_seconds'][1]=.5
        with self.assertRaises(ValueError):audit.round_metrics(d,d['rounds'][0],0)
        d=source();d['rounds'][0]['teams']=[]
        with self.assertRaises(ValueError):audit.round_metrics(d,d['rounds'][0],0)

    def test_holdout_and_ambiguous_account_selection_guards(self):
        games=[['broky','2392601','s','f','train'],['broky','2393024','s','f','test']]
        self.assertEqual([g[1] for g in audit.selection(games,'train')],['2392601'])
        for bad in ([['donk','2393226','s','f','train']],[['broky','2393024','s','f','train']]):
            with self.assertRaises(ValueError):audit.selection(bad,'train')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):audit.run(Path(tmp),Path(tmp)/'games.json',Path(tmp)/'out','test')

    def test_cli_output_and_delayed_inventory_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);games=root/'games.json';games.write_text(json.dumps([['broky','2392601','s','f','train']]))
            with gzip.open(root/'2392601.json.gz','wt') as f:json.dump(source(),f)
            result=audit.run(root,games,root/'out')
            self.assertEqual(len(result['rounds']),1)
            self.assertTrue((root/'out'/'rounds.csv').is_file())
            self.assertEqual(result['summaries'][0]['primary_possession_rounds_anytime'],{'AWP':1})


if __name__=='__main__':unittest.main()
