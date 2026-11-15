"""Conservative completion report: a dev score is not a final test or a gameplay fix."""
import argparse
import json
import math
from pathlib import Path
from common import write_json, sha256


def assess(record):
    if str(record.get("settings",{}).get("dev_only")).lower()!="true":
        raise ValueError("Expected a development-only experiment")
    rows=record["iterations"]
    base=next(r for r in rows if r["iteration"]==0)
    best=int(record["best_iteration"])
    candidate=next((r for r in rows if r["iteration"]==best),None) if best else None
    if best < 0 or (best and candidate is None):
        raise ValueError("Selected iteration is absent from the run")
    keys=("mean_ade","selection_score","turn_w1","move_w1","violation_share")
    for row in [base]+([candidate] if candidate else []):
        if any(not math.isfinite(float(row[k])) for k in keys):
            raise ValueError("Nonfinite or missing development result")
    passed=None if candidate is None else dict(
        path=candidate["mean_ade"]<base["mean_ade"],
        view=candidate["turn_w1"]<=base["turn_w1"],
        tempo=candidate["move_w1"]<=base["move_w1"],
        human_limits=candidate["violation_share"]<=base["violation_share"],
        joint_selection=candidate["selection_score"]<base["selection_score"])
    return dict(player=record["player"],state="no_development_candidate" if candidate is None else "development_candidate_unvalidated",
        best_iteration=best,completed_iterations=max(r["iteration"] for r in rows),baseline={k:base[k] for k in keys},
        optimizer_updates=max(r["iteration"] for r in rows)*int(record["settings"].get("steps_per_iteration",100)),
        elapsed_minutes=record.get("minutes_before_test"),
        selected=None if candidate is None else {k:candidate[k] for k in keys},
        development_component_checks=passed,all_measured_dev_components_nonregressing=False if passed is None else all(passed.values()),
        final_test_run=False,deployed=False,all_feedback_fixed=False,
        unestablished=["actual CS2 audibility","causal hearing/visibility","utility strategy","whole-round adaptation",
            "live controller behavior","self-kill resolution","jump/AWP quirk fidelity","new-match generalization"],
        interpretation="Development selection only. Component regression remains a limitation even when the joint objective improves.")


def main():
    p=argparse.ArgumentParser();p.add_argument("--runs",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    args=p.parse_args();reports={}
    for player in ("donk","broky"):
        folder=args.runs/("v1-"+player)
        record=json.loads((folder/"imagination.json").read_text())
        if record.get("player")!=player:raise ValueError("Wrong player in run")
        reports[player]=assess(record)
        adapter=folder/"imagined_lora.pt"
        if reports[player]["best_iteration"] and not adapter.exists():
            raise ValueError("Selected candidate has no saved adapter")
        if not reports[player]["best_iteration"] and adapter.exists():
            raise ValueError("A baseline-only run must not present a trained adapter")
        reports[player]["adapter_sha256"]=sha256(adapter) if adapter.exists() else None
        reports[player]["base_checkpoint_sha256"]=record["base_checkpoint_sha256"]
        reports[player]["manifest_sha256"]=record["manifest_sha256"]
    for key in ("base_checkpoint_sha256","manifest_sha256"):
        if len({r[key] for r in reports.values()})!=1:raise ValueError("Runs have different "+key)
    write_json(args.out,dict(scope="round4_development_only",players=reports))
    print(json.dumps(reports,indent=2))


if __name__=="__main__":main()
