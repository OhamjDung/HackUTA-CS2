import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import round4,donk

def trace(step,yaw):
 return dict(pred_points=[[step*(i+1),0,0] for i in range(16)],pred_yaw=[yaw]*16,pred_pitch=[0]*16)
def result():
 t=trace(20,0)
 return dict(start_pos=[0,0,0],gt={k.replace('pred_','gt_'):v for k,v in t.items()},samples=[trace(20,90),trace(21,0),trace(21,0),trace(23,0)])
def test_view_and_diversity_affect_judge():
 r=result();chosen=round4.ranked_samples(r)
 assert chosen[0][0]==1 and len(chosen)==2
 assert chosen[1][0]!=2

def test_circular_heading_and_player_tempo():
 r=result();r['gt']['gt_yaw']=[179]*16
 c=round4.components(trace(20,-179),r['gt'],r['start_pos'])
 assert np.isclose(c['view'],2/45) and c['tempo']==0
 slow=round4.components(trace(0,179),r['gt'],r['start_pos'])
 assert slow['still_share']>c['still_share']

def test_impossible_motion_rejected():
 r=result();r['samples']=[trace(100,0)]
 assert not round4.ranked_samples(r)

def test_broky_indices_are_selected_without_donk():
 from types import SimpleNamespace
 old=donk.PLAYER
 try:
  donk.PLAYER='broky'
  d=SimpleNamespace(by_player={'donk':[0],'broky':[1]},index=[({'match_id':'1','round_id':2},0),({'match_id':'2','round_id':4},0)])
  assert donk.donk_indices(d)==[1]
 finally:donk.PLAYER=old

def test_noise_proxy_does_not_force_all_players_to_walk():
 start=[0,0,0]
 fast=[[50,0,0],[100,0,0]]
 assert round4.noise_proxy(fast,start,[[200,0,0]])==1
 assert round4.noise_proxy(fast,start,[[5000,0,0]])==0
 assert round4.noise_proxy([[10,0,0],[20,0,0]],start,[[200,0,0]])==0
 assert round4.noise_proxy(fast,start,[])==0
