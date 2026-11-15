import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from round4_report import assess


def record(best=1):
    return dict(player="broky",settings={"dev_only":"True"},best_iteration=best,iterations=[
        dict(iteration=0,mean_ade=100.,selection_score=120.,turn_w1=4.,move_w1=3.,violation_share=.01),
        dict(iteration=1,mean_ade=90.,selection_score=110.,turn_w1=5.,move_w1=2.,violation_share=.005)])


def test_better_joint_score_does_not_hide_bad_turning_or_claim_gameplay():
    r=assess(record())
    assert r['development_component_checks']['path'] is True
    assert r['development_component_checks']['view'] is False
    assert not r['all_measured_dev_components_nonregressing']
    assert r['deployed'] is False and r['all_feedback_fixed'] is False and r['final_test_run'] is False


def test_no_candidate_is_not_a_trained_base_identity():
    r=assess(record(0))
    assert r['selected'] is None and r['state']=='no_development_candidate'


def test_invalid_or_final_results_cannot_be_mislabelled():
    r=record();r['iterations'][1]['mean_ade']=float('nan')
    with pytest.raises(ValueError):assess(r)
    r=record();r['settings']['dev_only']='False'
    with pytest.raises(ValueError):assess(r)
    with pytest.raises(ValueError):assess(record(99))
