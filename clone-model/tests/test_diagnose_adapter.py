"""CPU tests for diagnose_adapter.py on synthetic adapter states (no downloads, no base weights)."""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import PLAYERS, REGISTRY, configure
from identity import PlayerAdapter
import diagnose_adapter as diag


def synthetic_saved(step=400, seed=0, d=8, d_identity=4, zero_film=False):
    torch.manual_seed(seed)
    adapter = PlayerAdapter(REGISTRY, d, d_identity)
    if not zero_film:
        with torch.no_grad():
            adapter.film.to_scale_shift.weight.normal_(0, .05)
            adapter.film.to_scale_shift.bias.normal_(0, .05)
    return dict(adapter={k: v.detach().clone() for k, v in adapter.state_dict().items()}, registry=dict(REGISTRY),
        d_model=d, d_identity=d_identity, step=step, metrics={}), adapter


def test_film_terms_match_the_adapter_forward():
    saved, adapter = synthetic_saved()
    x = torch.randn(5, 8)
    for row in (1, 2):
        terms = diag.film_terms(saved["adapter"])[row]
        expected = adapter(x, torch.full((5,), row)).double()
        torch.testing.assert_close(x.double() * (1 + terms["gamma"]) + terms["beta"], expected, rtol=1e-6, atol=1e-6)


def test_zero_initialized_adapter_reports_no_change():
    saved, _ = synthetic_saved(step=0, zero_film=True)
    summary = diag.adapter_summary(saved, PLAYERS)
    assert summary["unknown_row_is_zero"]
    assert set(summary["identities"]) == {"donk", "broky"}
    for row in summary["identities"].values():
        assert row["gamma"]["norm"] == 0 and row["beta"]["norm"] == 0
        assert row["beta"]["dims_above"]["0.1"] == 0
    assert summary["pair"]["half_difference_norm"] == {"gamma": 0.0, "beta": 0.0}


def test_identical_identities_have_no_identity_specific_part():
    saved, _ = synthetic_saved()
    E = saved["adapter"]["embedding.weight"]
    E[2] = E[1]
    summary = diag.adapter_summary(saved, PLAYERS, lr=1e-3)
    assert summary["pair"]["embedding_cosine"] == pytest.approx(1)
    assert summary["pair"]["half_difference_norm"]["beta"] == pytest.approx(0, abs=1e-12)
    assert summary["pair"]["shared_norm"]["beta"] > 0
    bound = summary["adam_step_bound"]
    assert bound["max_move_per_parameter"] == pytest.approx(.4)
    W = saved["adapter"]["film.to_scale_shift.weight"]
    assert bound["film_weight_max_over_bound"] == pytest.approx(float(W.abs().max()) / .4)


def test_embedding_compared_with_its_initial_value():
    saved, _ = synthetic_saved()
    init = saved["adapter"]["embedding.weight"].clone()
    saved["adapter"]["embedding.weight"][1:] += .01
    summary = diag.adapter_summary(saved, PLAYERS, lr=1e-3, initial_embedding=init)
    row = summary["embedding_vs_init"]["donk"]
    assert row["moved_max_abs"] == pytest.approx(.01, rel=1e-4)
    assert row["cosine_to_init"] > .99
    with pytest.raises(ValueError):
        diag.adapter_summary(saved, PLAYERS, initial_embedding=init[:2])


def test_drift_between_identical_checkpoints_is_zero():
    saved, _ = synthetic_saved()
    drift = diag.drift_summary(saved, saved, PLAYERS)
    assert all(t["max_abs_change"] == 0 for t in drift["tensors"].values())
    assert drift["identities"]["donk"]["beta"]["cosine"] == pytest.approx(1)


def test_implied_condition_scale_recovers_a_known_scale():
    gamma, beta = torch.full((10,), .1, dtype=torch.float64), torch.full((10,), .5, dtype=torch.float64)
    terms = {1: dict(gamma=gamma, beta=beta), 2: dict(gamma=gamma, beta=beta)}
    regularizer = .1 ** 2 * 8 ** 2 + .5 ** 2  # x RMS 8
    assert diag.implied_condition_rms(regularizer, terms) == pytest.approx(8)
    assert diag.implied_condition_rms(.1, terms) is None


def test_training_summary_reports_regularizer_weight_and_dev_gain():
    history = [dict(step=s, loss=.6, regularizer=r) for s, r in ((1, 0.), (10, .1), (20, .2), *[(30 + 10*i, .3 + .01*i) for i in range(25)])]
    training = dict(history=history, best_step=200, holdout_used_for_selection=False,
        baseline={"donk": dict(own_teacher_forced_loss=.66, base_teacher_forced_loss=.66, windows=24)},
        latest_dev={"donk": dict(own_teacher_forced_loss=.65, base_teacher_forced_loss=.66, windows=24)})
    summary = diag.training_summary(training)
    assert summary["development"]["donk"]["latest_improvement"] == pytest.approx(.01)
    assert summary["regularizer"]["weighted_last"] == pytest.approx(.001 * history[-1]["regularizer"])
    assert summary["regularizer"]["still_rising"]
    assert summary["holdout_used_for_selection"] is False


def review_case(match="2393237", own_shift=0.):
    path = [[.25 * (i + 1), float(i), 0., 0.] for i in range(4)]
    moved = [[t, x + own_shift, y, z] for t, x, y, z in path]
    trace = lambda p: dict(path=p, yaw_degrees=[0.] * 4)
    return dict(player="donk", match_id=match, round_id=1, side="CT", context_tick=15, start_position=[0, 0, 0],
        actual=trace(path), predictions=dict(own=trace(moved), other=trace(path), base=trace(path)))


def test_review_summary_counts_exact_equal_paths_and_refuses_held_out():
    summary = diag.review_summary(dict(split="dev", cases=[review_case(), review_case(own_shift=4.)]))
    assert summary["exact_equal_paths"] == {"own==base": 1, "own==other": 1, "other==base": 2, "all_three_equal": 1}
    assert summary["per_case"][1]["max_xyz_diff_own_base"] == 4
    with pytest.raises(ValueError):
        diag.review_summary(dict(split="dev", cases=[review_case(match="2393242")]))
    with pytest.raises(ValueError):
        diag.review_summary(dict(split="test", cases=[]))


def test_logit_comparison():
    reference = torch.tensor([[[3., 0., 0.], [0., 1., .9]]])
    mask = torch.tensor([[True, True]])
    same = diag.compare_logits(reference, reference.clone(), mask)
    assert same["argmax_agreement"] == 1 and same["mean_kl_reference_to_other"] == pytest.approx(0, abs=1e-7)
    assert same["share_positions_flippable"] == 0
    other = reference.clone()
    other[0, 1, 2] += .2  # closes a 0.1 gap: flips the second position only
    changed = diag.compare_logits(reference, other, mask)
    assert changed["argmax_agreement"] == .5 and changed["share_positions_flippable"] == .5
    assert changed["max_abs_logit_change"] == pytest.approx(.2)


def test_paired_difference_clusters_windows_by_round():
    result = diag.paired_difference([-1., -1., -1., 3.], ["a", "a", "a", "b"])
    assert result["mean"] == 0 and result["round_mean"] == 1 and result["rounds"] == 2
    assert result["share_windows_lower"] == .75 and result["share_rounds_lower"] == .5
    assert result["sem_rounds"] == pytest.approx(2)


def test_decoder_measurement_refuses_held_out_rounds():
    dev = dict(match_id="2393237", split="dev")
    diag.check_development_manifest(dict(rounds=[dev, dict(match_id="2393024", split="test")]))
    with pytest.raises(ValueError):
        diag.check_development_manifest(dict(rounds=[dev, dict(match_id="2393024", split="dev")]))
    with pytest.raises(ValueError):
        diag.check_development_manifest(dict(rounds=[dict(match_id="2393237", split="train")]))


def test_adapter_cli_writes_a_report(tmp_path):
    early, _ = synthetic_saved(step=400, seed=1)
    late, _ = synthetic_saved(step=600, seed=2)
    torch.save(early, tmp_path / "best.pt")
    torch.save(late, tmp_path / "last.pt")
    (tmp_path / "manifest.json").write_text(json.dumps(dict(players=PLAYERS)))
    history = [dict(step=s, loss=.6, regularizer=.5) for s in (1, *range(10, 610, 10))]
    (tmp_path / "training.json").write_text(json.dumps(dict(history=history, best_step=400,
        baseline={"donk": dict(own_teacher_forced_loss=.66, base_teacher_forced_loss=.66, windows=24)},
        latest_dev={"donk": dict(own_teacher_forced_loss=.65, base_teacher_forced_loss=.66, windows=24)})))
    (tmp_path / "review.json").write_text(json.dumps(dict(split="dev", cases=[review_case()])))
    out = tmp_path / "report.json"
    diag.main(["adapter", "--best", str(tmp_path / "best.pt"), "--last", str(tmp_path / "last.pt"),
        "--training", str(tmp_path / "training.json"), "--review", str(tmp_path / "review.json"),
        "--manifest", str(tmp_path / "manifest.json"), "--lr", "3e-4", "--out", str(out)])
    report = json.loads(out.read_text())
    assert report["best"]["step"] == 400 and report["drift_best_to_last"]["to_step"] == 600
    assert report["review"]["exact_equal_paths"]["all_three_equal"] == 1
    assert "implied_condition_rms" in report["best"]
    assert math.isclose(report["training"]["regularizer"]["weighted_last"], .0005)


@pytest.fixture
def upstream():
    value = os.environ.get("CSNET_ROOT")
    if not value:
        pytest.fail("Set CSNET_ROOT to the pinned CS-NET checkout; these tests must not silently skip integration")
    return configure(value)


def test_decoder_inputs_reproduce_the_training_loss(upstream):
    from pretrain_model import CS2PretrainModel, PretrainConfig
    from model import LearnedClone
    from test_learned import synthetic_batch
    torch.manual_seed(0)
    cfg = PretrainConfig(d_model=32, n_spatial_layers=1, n_temporal_layers=1, n_decoder_layers=1,
        n_depth_ray_layers=1, n_heads=4, d_ff=64, n_ticks=16, move_grid_size=4., angle_grid_size=5.)
    model = LearnedClone(CS2PretrainModel(cfg), REGISTRY).eval()
    with torch.no_grad():
        model.adapter.film.to_scale_shift.weight.normal_(0, .1)
    batch = synthetic_batch()
    expected = model(batch)[0]
    inputs = diag.decoder_inputs(model, batch)
    logits, targets = diag.decode(model, inputs, model.adapter(inputs["conditions"], batch["identity"].long()))
    torch.testing.assert_close(model.backbone._compute_loss(logits, targets)[0], expected)
    base_logits, _ = diag.decode(model, inputs, inputs["conditions"])
    torch.testing.assert_close(model.backbone._compute_loss(base_logits, targets)[0], model(batch, identity_override=0)[0])
