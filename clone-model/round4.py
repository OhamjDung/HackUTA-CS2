"""Development-only path/view/tempo expert iteration for either player.

Reuses imagine.py and the pinned CS-NET engine. This first ablation does not claim
causal hearing, utility strategy or runtime adaptability; those need separate input/controller work.
"""
import argparse
import random
from pathlib import Path
import numpy as np
import torch
import donk
import imagine
from common import configure, write_json


def aligned(points, n, start):
    a = np.asarray(points or [start], dtype=float).reshape(-1, 3)
    return a[np.minimum(np.arange(n), len(a)-1)]


def noise_proxy(points, start, enemies, speed=150., radius=1100.):
    """Offline evaluator-only speed/proximity proxy, NOT measured CS2 audibility.

    No future enemy location is used; crouch/occlusion are unknown, so this is not a hearing model.
    """
    p=np.asarray(points,dtype=float).reshape(-1,3)
    if not len(p) or not len(enemies): return 0.
    fast=np.linalg.norm(np.diff(np.vstack([start,p]),axis=0)[:,:2],axis=1)/.25 > speed
    near=np.linalg.norm(p[:,None,:]-np.asarray(enemies)[None,:,:],axis=-1).min(axis=1)<radius
    return float(np.mean(fast & near))


def components(sample, gt, start, enemies=()):
    n = len(gt["gt_points"])
    pred, real = aligned(sample["pred_points"], n, start), np.asarray(gt["gt_points"], dtype=float)
    pm = np.linalg.norm(np.diff(np.vstack([start, pred]), axis=0), axis=1)
    rm = np.linalg.norm(np.diff(np.vstack([start, real]), axis=0), axis=1)
    yaw = np.asarray(sample["pred_yaw"], dtype=float)
    if not len(yaw): return None
    yaw = yaw[np.minimum(np.arange(n), len(yaw)-1)]
    gy = np.asarray(gt["gt_yaw"], dtype=float)
    if len(gy) != n: raise ValueError("Ground-truth angle/path misalignment")
    return dict(path=float(np.linalg.norm(pred-real, axis=1).mean()/68),
        view=float(np.abs(donk.wrap(yaw-gy)).mean()/45),
        tempo=float(np.abs(pm-rm).mean()/68),
        fast_share=float(abs(np.mean(pm > 37.5)-np.mean(rm > 37.5))),
        still_share=float(abs(np.mean(pm < 1)-np.mean(rm < 1))),
        noise_proxy_gap=abs(noise_proxy(pred,start,enemies)-noise_proxy(real,start,enemies)))


def ranked_samples(result, count=2):
    gt = result.get("gt")
    if not gt or not gt.get("gt_points"): return []
    start = result["start_pos"]
    if donk.violation_share(*donk.path_steps(start,gt["gt_points"],gt["gt_yaw"],gt.get("gt_pitch",[]))[:3]) > 0: return []
    ranked = []
    for i, sample in enumerate(result["samples"]):
        if not sample["pred_points"]: continue
        if donk.violation_share(*donk.path_steps(start,sample["pred_points"],sample["pred_yaw"],sample.get("pred_pitch",[]))[:3]) > 0: continue
        c = components(sample, gt, start, result.get("judge_context_enemies",()))
        if c is None or not all(np.isfinite(v) for v in c.values()): continue
        # Player-specific tempo/fast/still targets come from this player's expert future,
        # not an average pro's preferred speed. 150u/s is only a historical proxy boundary.
        score = c["path"] + c["view"] + 2*(c["tempo"]+c["fast_share"]+c["still_share"]) + c["noise_proxy_gap"]
        ranked.append((score,i,c))
    chosen = []
    for score,i,c in sorted(ranked):
        p = aligned(result["samples"][i]["pred_points"],len(gt["gt_points"]),start)
        if any(np.mean(np.linalg.norm(p-aligned(result["samples"][j]["pred_points"],len(p),start),axis=1)) < 8 for j,_ in chosen): continue
        chosen.append((i, c))
        if len(chosen) == count: break
    return chosen


def imagine_diverse(recorder, cache, chosen, k):
    from data import load_round
    kept=[]
    for file,tick,player in chosen:
        sample=load_round(str(cache/file))
        result,inputs=recorder.sample(sample,tick,player,k)
        from training_data.config import denormalize_position
        teams=sample["meta"]["teams"]
        # Privileged positions are used only by the offline judge, not added to policy inputs.
        result["judge_context_enemies"]=[denormalize_position(*map(float,sample["player_pos"][tick,j]),"de_mirage")
            for j in range(10) if teams[j]!=teams[player] and sample["player_alive_mask"][tick,j]]
        if inputs is None: continue
        for i,c in ranked_samples(result):
            kept.append({key:v[i].cpu() for key,v in inputs.items()} | {"ade":c["path"]*68,"judge":c})
    return kept,len(chosen)


def main():
    p=argparse.ArgumentParser()
    for name in ("csnet","cache","checkpoint","out"): p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--player",choices=["donk","broky"],required=True)
    p.add_argument("--device",default="cuda",choices=["cuda","cpu"])
    p.add_argument("--iterations",type=int,default=4)
    p.add_argument("--moments-per-iteration",type=int,default=200)
    p.add_argument("--select-moments",type=int,default=80)
    p.add_argument("--steps-per-iteration",type=int,default=100)
    p.add_argument("--budget-minutes",type=float,default=60)
    args=p.parse_args()
    configure(args.csnet)
    args.dev_only=True; args.samples=8; args.batch_size=6; args.lr=3e-4
    args.kl=.1; args.imagined_weight=1.; args.rank=16; args.keep_last=1200
    donk.PLAYER=args.player
    imagine.imagine=imagine_diverse
    # Select using path AND view/tempo deviation on development, not path alone.
    original_summary=imagine.summary
    def joint_summary(run,real):
        s=original_summary(run,real)
        s["path_ade"]=s["mean_ade"]
        s["mean_ade"]=s["path_ade"]+68*(s["turn_w1"]/45+2*s["move_w1"]/68)
        s["selection_score"]=s["mean_ade"]
        return s
    imagine.summary=joint_summary
    args.out.mkdir(parents=True,exist_ok=True)
    write_json(args.out/"protocol.json",dict(player=args.player,scope="development_only",final_test=False,
        judge="path + circular view + 2*(tempo + expert fast-share gap + expert still-share gap) + context noise-proxy gap",
        noise_proxy="Offline speed>150u/s within1100 units of an enemy's context position; historical proxy, not CS2 hearing; not policy input",
        selection="path ADE + 68*(turn W1/45 + 2*movement W1/68)",
        limits="unchanged human per-step gates",diversity="up to two paths; mean XY/XYZ distance >=8 units",
        excluded_features=["causal hearing","fog of war","utility lineups","whole-round tactics","runtime controller fixes"]))
    torch.set_num_threads(4)
    imagine.run(args)


if __name__ == "__main__": main()
