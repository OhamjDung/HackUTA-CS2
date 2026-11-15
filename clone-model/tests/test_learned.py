from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import HOLDOUTS, PLAYERS, REGISTRY, configure, round_split
from identity import PlayerAdapter
from validate import path_metrics


def test_unknown_identity_is_the_base_even_after_bias_training():
    adapter = PlayerAdapter(REGISTRY, 8)
    x = torch.randn(3, 8)
    assert torch.equal(adapter(x, torch.tensor([0, 1, 2])), x)
    with torch.no_grad():
        adapter.film.to_scale_shift.weight.fill_(.1)
        adapter.film.to_scale_shift.bias.fill_(.3)
    assert torch.equal(adapter(x, torch.zeros(3, dtype=torch.long)), x)
    assert not torch.equal(adapter(x, torch.ones(3, dtype=torch.long)), x)


def test_identity_indices_are_stable_dense_and_do_not_use_nicknames():
    assert REGISTRY[PLAYERS["donk"]] != REGISTRY[PLAYERS["broky"]]
    with pytest.raises(ValueError):
        PlayerAdapter({"steam-id": 0}, 8)
    with pytest.raises(ValueError):
        PlayerAdapter({"steam-id": 3}, 8)


def test_holdouts_never_enter_training_or_tuning():
    for match in HOLDOUTS:
        assert {round_split(match, r) for r in range(1, 40)} == {"test"}
    for match in ("2393226", "2392601"):
        splits = [round_split(match, r) for r in range(1, 25)]
        assert set(splits) == {"train", "dev"}
        assert splits == [round_split(match, r) for r in range(1, 25)]


def test_early_stopping_does_not_hide_the_rest_of_the_path_error():
    scores = path_metrics([[1, 0, 0]], [[1, 0, 0], [2, 0, 0], [3, 0, 0]], [0, 0, 0])
    assert scores["ade"] == 1
    assert scores["fde"] == 2
    with pytest.raises(ValueError):
        path_metrics([[float("nan"), 0, 0]], [[1, 0, 0]], [0, 0, 0])


@pytest.fixture
def upstream():
    value = os.environ.get("CSNET_ROOT")
    if not value:
        pytest.fail("Set CSNET_ROOT to the pinned CS-NET checkout; these tests must not silently skip integration")
    return configure(value)


def test_player_shuffle_preserves_the_target_and_its_labels(upstream):
    from data import shuffle_aligned
    features = np.zeros((16, 10, 3), dtype=np.float32)
    features[:, :, 0] = np.arange(10)
    labels = np.zeros((31, 10, 10), dtype=np.float32)
    labels[:, :, 0] = np.arange(10)
    permutation = np.array([9, 7, 2, 0, 6, 4, 1, 3, 8, 5])
    identities = np.zeros(10, dtype=np.int64)
    identities[7] = 2
    window, ids, target = shuffle_aligned(dict(player_pos=features, label_camera=labels), identities, 7, permutation)
    assert target == 1 and ids[target] == 2
    assert np.all(window["player_pos"][:, target, 0] == 7)
    assert np.all(window["label_camera"][:, target, 0] == 7)


def synthetic_batch():
    B, T, P, L = 2, 16, 10, 31
    return dict(
        player_pos=torch.randn(B,T,P,3), player_state=torch.randn(B,T,P,14),
        player_inv=torch.zeros(B,T,P,9,dtype=torch.long), player_inv_mask=torch.ones(B,T,P,9,dtype=torch.bool),
        player_rel_f=torch.randn(B,T,P,9,14), player_rel_i=torch.zeros(B,T,P,9,dtype=torch.long),
        player_rel_mask=torch.ones(B,T,P,9,dtype=torch.bool), player_sound=torch.zeros(B,T,P,2),
        player_alive_mask=torch.ones(B,T,P,dtype=torch.bool), player_depth=torch.randn(B,T,P,64,5),
        bomb_pos=torch.randn(B,T,3), bomb_state=torch.randn(B,T,4), map_idx=torch.zeros(B,T,dtype=torch.long),
        proj_pos=torch.randn(B,T,16,3), proj_type=torch.zeros(B,T,16,dtype=torch.long),
        proj_dur=torch.zeros(B,T,16), proj_mask=torch.zeros(B,T,16,dtype=torch.bool), proj_is_active=torch.zeros(B,T,16),
        tick_times_input=torch.arange(T).float().expand(B,-1)*.25,
        player_depth_labels=torch.randn(B,L,P,64,5), player_pos_labels=torch.randn(B,L,P,3),
        player_angle_labels=torch.randn(B,L,P,4), label_camera=torch.zeros(B,L,P,10),
        target_index=torch.tensor([3,7]), identity=torch.tensor([1,2]))


def test_real_backbone_wiring_has_zero_initial_change_and_only_adapter_gradients(upstream):
    from pretrain_model import CS2PretrainModel, PretrainConfig
    from model import LearnedClone
    torch.set_num_threads(2)
    torch.manual_seed(42)
    cfg = PretrainConfig(d_model=32, n_spatial_layers=1, n_temporal_layers=1,
        n_decoder_layers=1, n_depth_ray_layers=1, n_heads=4, d_ff=64, n_ticks=16,
        move_grid_size=4., angle_grid_size=5.)
    model = LearnedClone(CS2PretrainModel(cfg), REGISTRY)
    batch = synthetic_batch()
    own = model(batch)[0]
    baseline = model(batch, identity_override=0)[0]
    torch.testing.assert_close(own, baseline, rtol=0, atol=0)
    own.backward()
    assert all(p.grad is None and not p.requires_grad for p in model.backbone.parameters())
    assert model.adapter.film.to_scale_shift.weight.grad.abs().sum() > 0


def test_temporal_hook_leaves_all_unknown_slots_unchanged():
    adapter = PlayerAdapter(REGISTRY, 8)
    with torch.no_grad():
        adapter.film.to_scale_shift.bias.fill_(.2)
    x = torch.randn(1,16,10,8)
    ids = torch.zeros(1,10,dtype=torch.long)
    ids[0,4] = 1
    result = adapter.temporal_hook(ids)(None, None, x)
    assert torch.equal(result[:,:,:4], x[:,:,:4])
    assert torch.equal(result[:,:,5:], x[:,:,5:])
    assert not torch.equal(result[:,:,4], x[:,:,4])


def test_spectator_roster_filter_requires_five_real_players_per_side():
    import pandas as pd
    from parse_compat import active_roster
    frame = pd.DataFrame({"steamid": [str(i) for i in range(11)], "team_num": [2]*5 + [3]*5 + [float("nan")]})
    result = active_roster(frame)
    assert result["steamid"].tolist() == [str(i) for i in range(10)]
    frame.loc[10,"team_num"] = 2
    with pytest.raises(ValueError):
        active_roster(frame)


def test_checked_roster_is_kept_through_later_tick_passes():
    import pandas as pd
    from parse_compat import RosterParser
    class FakeParser:
        def __init__(self):
            self.calls = []
        def parse_ticks(self, *args, **kwargs):
            self.calls.append(kwargs)
            return pd.DataFrame({"steamid": list(range(100,111))*2, "tick": [1]*11+[2]*11,
                "team_num": ([2]*5+[3]*5+[float("nan")])*2})
    original = FakeParser()
    parser = RosterParser(original)
    assert len(parser.parse_ticks(wanted_props=["team_num"])) == 20
    assert len(parser.parse_ticks(wanted_props=["team_num"], ticks=[1,2])) == 20
    assert original.calls[1]["players"] == list(range(100,110))
