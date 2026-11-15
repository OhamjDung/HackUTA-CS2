import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gamesense_audit import measure_round

def sample(distance):
 n=12;t=np.arange(n)*.25
 p=dict(x=(t*200).tolist(),y=[0]*n,z=[0]*n,yaw=[179]*n,alive=[1]*n,weapon=[0]*n,inventory=[[0]]*n,shots=[0]*n,footsteps=[1]*n)
 q={**p,'x':(t*200+distance).tolist(),'shots':[1]*n}
 return {'weapons':{'AWP':0}},dict(round_seconds=t.tolist(),teams=['T','CT'],players=[p,q])

def test_proximity_proxy_and_missing_inventory_are_explicit():
 d,r=sample(500);m=measure_round(d,r,0)
 assert m['noise_speed_proximity_proxy']==1 and m['active_awp_share']==1
 assert m['carried_awp_share']==1
 d,r=sample(5000);r['players'][0].pop('inventory')
 m=measure_round(d,r,0)
 assert m['noise_speed_proximity_proxy']==0 and m['sound_proxy_trials']==0
 assert m['carried_awp_share'] is None

def test_wraparound_is_not_a_full_rotation():
 d,r=sample(500);r['players'][0]['yaw']=[179,-179]*6
 m=measure_round(d,r,0)
 assert np.isclose(m['mean_turn_deg_per_second'],8)

def test_invalid_time_gap_not_scored_as_slow_movement():
 d,r=sample(500);r['round_seconds'][5]+=3
 m=measure_round(d,r,0)
 assert m['invalid_intervals']>=3

def test_heldout_and_consumed_rounds_are_excluded():
 from gamesense_audit import eligible_round
 from common import round_split
 for mid in ('2393242','2393024','2393226'):
  assert not any(eligible_round(mid,i) for i in range(30))
 for i in range(30):
  if i%6==3 or round_split('2393237',i)!='train': assert not eligible_round('2393237',i)

def test_missing_sounds_are_unknown_not_complete():
 d,r=sample(500)
 r['players'][1].pop('footsteps')
 assert measure_round(d,r,0)['sound_fields_complete'] is False
