"""CPU tests for the second learned-identity experiment (v2.py). A tiny random base stands in for CS-NET."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_learned import synthetic_batch, upstream  # noqa: F401  (upstream is a fixture)
import v2

REGISTRY = {"ids": {"11": 1, "12": 2, "13": 3, "21": 4, "22": 5},
            "groups": {"11": ["11", "12", "13"], "12": ["11", "12", "13"], "13": ["11", "12", "13"],
                       "21": ["21", "22"], "22": ["21", "22"]}}


def tiny_model():
    from pretrain_model import CS2PretrainModel, PretrainConfig
    torch.set_num_threads(2)
    torch.manual_seed(42)
    cfg = PretrainConfig(d_model=32, n_spatial_layers=1, n_temporal_layers=1, n_decoder_layers=1,
                         n_depth_ray_layers=1, n_heads=4, d_ff=64, n_ticks=16, move_grid_size=4., angle_grid_size=5.)
    return v2.LearnedCloneV2(CS2PretrainModel(cfg), len(REGISTRY["ids"]))


def batch_with_slots():
    batch = synthetic_batch()
    slots = torch.zeros(2, 10, dtype=torch.long)
    slots[0, 3], slots[0, 5], slots[1, 7] = 1, 2, 4
    batch["slot_ids"] = slots
    return batch


def test_targets_are_every_registered_player_in_the_batch():
    bi, pi, ids = v2.targets_of(batch_with_slots())
    assert bi.tolist() == [0, 0, 1] and pi.tolist() == [3, 5, 7] and ids.tolist() == [1, 2, 4]


def test_new_model_starts_as_the_exact_base_and_trains_only_the_adapter(upstream):  # noqa: F811
    model = tiny_model()
    batch = batch_with_slots()
    bi, pi, ids = v2.targets_of(batch)
    encoded = model.encode(batch, bi, pi)
    own, base = model.nll(encoded, ids), model.nll(encoded, torch.zeros_like(ids))
    torch.testing.assert_close(own, base, rtol=0, atol=0)          # zero effect before training
    assert own.shape == (3,)
    own.mean().backward()
    assert all(p.grad is None and not p.requires_grad for p in model.backbone.parameters())
    assert model.adapter.start.weight.grad.abs().sum() > 0
    assert all(layer.weight.grad.abs().sum() > 0 for layer in model.adapter.steps)   # identity reaches every step input


def test_unknown_player_stays_the_base_after_training_and_identities_differ(upstream):  # noqa: F811
    model = tiny_model()
    with torch.no_grad():
        for layer in (model.adapter.start, *model.adapter.steps):
            layer.weight.normal_(0, .5)
    batch = batch_with_slots()
    bi, pi, ids = v2.targets_of(batch)
    encoded = model.encode(batch, bi, pi)
    start, depth, xyz, angle, _ = encoded
    unchanged = model.adapter(start, depth, xyz, angle, torch.zeros_like(ids))
    for before, after in zip((start, depth, xyz, angle), unchanged):
        assert torch.equal(before, after)
    assert not torch.allclose(model.nll(encoded, ids), model.nll(encoded, torch.zeros_like(ids)))
    assert not torch.allclose(model.nll(encoded, ids), model.nll(encoded, torch.tensor([2, 1, 5])))


def test_wrong_teammate_is_always_a_different_member_of_the_same_team():
    ids = torch.tensor([1, 2, 3, 4, 5] * 20)
    wrong = v2.wrong_teammates(ids, REGISTRY, random.Random(0))
    assert (wrong != ids).all()
    for own, other in zip(ids.tolist(), wrong.tolist()):
        assert (own <= 3) == (other <= 3)


def test_rank_and_pass_rule():
    assert v2.rank_identities({1: 0.50, 2: 0.60, 3: 0.55}, 1) == 1
    assert v2.rank_identities({1: 0.50, 2: 0.60, 3: 0.55}, 2) == 3
    five = {"a": 5, "b": 5, "c": 5, "d": 5, "e": 5}
    good = v2.summarise({"a": 1, "b": 2, "c": 2, "d": 4, "e": 5}, five)
    assert good["top_1"] == 1 and good["top_k"] == 3 and good["pass"]          # 60% in the top 2
    bad = v2.summarise({"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}, five)
    assert not bad["pass"] and bad["chance_share_in_top_k"] == 0.4
    assert not v2.summarise({}, {})["pass"]                                     # an empty test cannot pass


def test_guidance_scale_one_is_the_plain_model_and_larger_scales_amplify():
    base, own = torch.tensor([0., 1.]), torch.tensor([0., 2.])
    assert torch.equal(v2.guided_logits(base, own, 1.0), own)
    assert torch.equal(v2.guided_logits(base, own, 0.0), base)
    assert torch.equal(v2.guided_logits(base, own, 3.0), torch.tensor([0., 4.]))


def test_pass_rule_constants_are_the_declared_ones():
    assert (v2.TOP_K, v2.PASS_SHARE, v2.MIN_MATCHES) == (2, 0.6, 2)
    with pytest.raises(ValueError):
        v2.rank_identities({1: 0.5}, 9)
