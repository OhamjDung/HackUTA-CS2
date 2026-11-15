"""Training-data-only measurements from pinned CS-NET parser JSON.

Historical hearing radii define an offline proximity proxy, not verified CS2 audibility.
Enemy truth is used only for labels. No policy/controller consumes this report.
"""
import argparse
import gzip
import json
from pathlib import Path
from collections import Counter, defaultdict
import math
import numpy as np
from common import PLAYERS, HOLDOUTS, write_json, round_split


def wrap(a): return (a+180)%360-180


def eligible_round(mid,rid):
    return mid not in HOLDOUTS and mid!="2393226" and round_split(mid,int(rid))=="train" and int(rid)%6!=3


def measure_round(data, r, player):
    t=np.asarray(r["round_seconds"],float)
    p=r["players"][player]
    n=len(t)
    def channel(name):
        a=np.asarray(p[name],float)
        if len(a)!=n: raise ValueError("Unaligned player channel: "+name)
        return a
    xyz=np.column_stack([channel(k) for k in ("x","y","z")])
    yaw=channel("yaw"); alive=channel("alive").astype(bool)
    dt=np.r_[np.nan,np.diff(t)]
    valid=(dt>0)&(dt<=.5)&np.r_[False,alive[:-1]]&alive
    speed=np.zeros(n);speed[valid]=np.linalg.norm(np.diff(xyz[:,:2],axis=0)[valid[1:]],axis=1)/dt[valid]
    turn=np.zeros(n);turn[valid]=np.abs(wrap(np.diff(yaw)[valid[1:]]))/dt[valid]
    distance=np.full(n,np.inf); sounds=[];sound_fields_complete=True
    teams=r["teams"]
    for j,q in enumerate(r["players"]):
        if teams[j]==teams[player]: continue
        sound_fields_complete &= "shots" in q and "footsteps" in q
        qpos=np.column_stack([q[k] for k in ("x","y","z")])
        dist=np.linalg.norm(qpos-xyz,axis=1)
        qalive=np.asarray(q["alive"],bool)
        distance=np.minimum(distance,np.where(qalive,dist,np.inf))
        shots=np.asarray(q.get("shots",[0]*n))>0
        steps=np.asarray(q.get("footsteps",[0]*n))>0
        for i in np.flatnonzero(valid & qalive & ((shots&(dist<=2000))|(steps&(dist<=1100)))):
            sounds.append((int(i),2 if shots[i] else 1,float(dist[i]),qpos[i]))
    # At most one event per two seconds, priority then nearer source; future is label-only.
    sounds.sort(key=lambda e:(e[0],-e[1],e[2]))
    trials=[];last=-np.inf
    for i,priority,dist,source in sounds:
        if t[i]-last<2: continue
        bearing=np.degrees(np.arctan2(source[1]-xyz[i,1],source[0]-xyz[i,0]))
        if abs(wrap(yaw[i]-bearing))<=30: continue # already oriented, no reaction credit
        later=np.flatnonzero(valid & (t>t[i]) & (t<=t[i]+1))
        if not len(later) or t[later[-1]]<t[i]+.75: continue
        last=t[i];latency=None
        for k in later:
            current_bearing=np.degrees(np.arctan2(source[1]-xyz[k,1],source[0]-xyz[k,0]))
            toward=abs(wrap(yaw[k]-current_bearing))<=30
            quieter=speed[i]>150 and speed[k]<=150
            if toward or quieter:
                latency=float(t[k]-t[i]);break
        trials.append(dict(time=float(t[i]),response_latency=latency,kind="shot" if priority==2 else "step"))
    elapsed=float(dt[valid].sum())
    if not elapsed: raise ValueError("No usable alive intervals")
    weighted=lambda mask:float(dt[valid & mask].sum()/elapsed)
    inverse={int(v):k for k,v in data["weapons"].items()}
    weapons=[inverse.get(int(w),"unknown") for w in p["weapon"]]
    active_awp=np.array([w=="AWP" for w in weapons])
    inventory=p.get("inventory")
    carried_awp=np.array([any(inverse.get(int(w))=="AWP" for w in items) for items in inventory]) if inventory is not None else None
    fields=dict(alive_seconds=elapsed,fast_over_150_share=weighted(speed>150),still_under_4_share=weighted(speed<4),
        noise_speed_proximity_proxy=weighted((speed>150)&(distance<1100)),
        mean_speed=float(np.sum(speed[valid]*dt[valid])/elapsed),
        mean_turn_deg_per_second=float(np.sum(turn[valid]*dt[valid])/elapsed),
        active_awp_share=weighted(active_awp),carried_awp_share=None if carried_awp is None else weighted(carried_awp),
        sound_proxy_trials=len(trials),sound_proxy_responses=sum(e["response_latency"] is not None for e in trials),
        sound_fields_complete=bool(sound_fields_complete),
        sound_proxy_latencies=[e["response_latency"] for e in trials if e["response_latency"] is not None],
        invalid_intervals=int((~valid).sum()))
    return fields


def main():
    p=argparse.ArgumentParser();p.add_argument("--json-dir",type=Path,required=True)
    p.add_argument("--games",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    args=p.parse_args();games=json.loads(args.games.read_text());rows=[]
    for name,mid,*rest in games:
        if mid in HOLDOUTS or rest[-1]=="test":continue
        if mid=="2393226":raise ValueError("Ambiguous account must remain quarantined")
        with gzip.open(args.json_dir/(mid+".json.gz"),"rt",encoding="utf-8") as f:d=json.load(f)
        ids=[i for i,x in enumerate(d["players"]) if str(x["steamid"])==PLAYERS[name]]
        if len(ids)!=1:raise ValueError("Target identity mismatch")
        for r in d["rounds"]:
            if not eligible_round(mid,r["id"]): continue
            m=measure_round(d,r,ids[0]);rows.append(dict(player=name,match_id=mid,round_id=r["id"],side=r["teams"][ids[0]],**m))
    summary={}
    for name in PLAYERS:
        group=[r for r in rows if r["player"]==name]
        if not group:raise ValueError("No training records for "+name)
        seconds=sum(r["alive_seconds"] for r in group)
        trials=sum(r["sound_proxy_trials"] for r in group)
        latencies=[x for r in group for x in r["sound_proxy_latencies"]]
        summary[name]=dict(rounds=len(group),matches=len(set(r["match_id"] for r in group)),alive_seconds=seconds,
            **{key:sum(r[key]*r["alive_seconds"] for r in group)/seconds for key in
               ("fast_over_150_share","still_under_4_share","noise_speed_proximity_proxy","mean_speed","mean_turn_deg_per_second","active_awp_share")},
            sound_fields_complete=all(r["sound_fields_complete"] for r in group),
            sound_proxy_trials=trials,response_share=None if not trials or not all(r["sound_fields_complete"] for r in group) else sum(r["sound_proxy_responses"] for r in group)/trials,
            response_median_seconds=None if not latencies else float(np.median(latencies)))
    write_json(args.out,dict(scope="round4_training_pool_only_no_dev_no_test_C",summary=summary,rounds=rows,
        interpretation="Observational proxies, not actual hearing or causal responses. Radii 1100/2000 and speed150 are historical hypotheses. No crouch/smoke/FOV verification; no sub-250ms claims. True enemy positions are offline labels only; no policy or runtime input change."))
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
