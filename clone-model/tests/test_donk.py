"""CPU tests for the donk-only model (donk.py). A tiny random CS-NET stands in for the real one."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_learned import synthetic_batch, upstream  # noqa: F401  (upstream is a fixture)
import donk


def tiny_base():
    from pretrain_model import CS2PretrainModel, PretrainConfig
    torch.set_num_threads(2)
    torch.manual_seed(42)
    cfg = PretrainConfig(d_model=32, n_spatial_layers=1, n_temporal_layers=1, n_decoder_layers=2,
                         n_depth_ray_layers=1, n_heads=4, d_ff=64, n_ticks=16, move_grid_size=4., angle_grid_size=5.)
    return CS2PretrainModel(cfg).eval().requires_grad_(False)


def decoder_logits(base, enc):
    return base.decoder(enc[0], enc[4], depth_ctx=enc[1], xyz_ctx=enc[2], angle_ctx=enc[3])[0]


def test_lora_starts_at_the_base_and_only_lora_learns(upstream):  # noqa: F811
    base = tiny_base()
    batch = synthetic_batch()
    b, p = torch.arange(2), batch["target_index"]
    enc = donk.encode(base, batch, b, p)
    before = decoder_logits(base, enc)
    loras = donk.add_lora(base.decoder, r=4)
    assert len(loras) == 2 * 4                                    # 2 blocks x (in_proj, out_proj, 2 feed-forward)
    torch.testing.assert_close(decoder_logits(base, enc), before, rtol=0, atol=1e-6)
    nll, kl = donk.losses(base, loras, enc)
    assert abs(float(kl)) < 1e-6                                  # identical to the base at the start
    for lora in loras:
        lora.A.requires_grad_(True); lora.B.requires_grad_(True)
    nll.backward()
    assert all(lora.B.grad is not None and lora.B.grad.abs().sum() > 0 for lora in loras)
    frozen = [prm for name, prm in base.named_parameters() if "parametrizations" not in name]
    assert all(prm.grad is None for prm in frozen)


def test_switching_lora_off_gives_the_base_and_merging_keeps_the_trained_model(upstream):  # noqa: F811
    base = tiny_base()
    batch = synthetic_batch()
    enc = donk.encode(base, batch, torch.arange(2), batch["target_index"])
    original = decoder_logits(base, enc)
    loras = donk.add_lora(base.decoder, r=4)
    with torch.no_grad():
        for lora in loras:
            lora.B.normal_(0, 0.05)
    trained = decoder_logits(base, enc)
    assert not torch.allclose(trained, original)
    donk.set_lora(loras, False)
    torch.testing.assert_close(decoder_logits(base, enc), original, rtol=0, atol=1e-6)
    _, kl = donk.losses(base, loras, enc)
    assert float(kl) > 0                                          # trained model now differs from the base
    donk.merge_lora(base.decoder)
    assert not any(torch.nn.utils.parametrize.is_parametrized(m) for m in base.decoder.modules())
    torch.testing.assert_close(decoder_logits(base, enc), trained, rtol=1e-5, atol=1e-5)
    assert all("parametrizations" not in k for k in base.state_dict())   # an ordinary checkpoint


def test_windows_whose_real_future_breaks_a_human_limit_are_flagged():
    labels = torch.zeros(3, 16, 10)
    labels[..., 3] = 1; labels[..., 5] = 1; labels[..., 7] = 1   # no turn, alive
    labels[:, :, 0] = 30.0                                        # 30 units per step: fine
    labels[1, 5, 0] = 90.0                                        # 90 units in 0.25 s: impossible on foot
    angle = np.radians(170)
    labels[2, 3, 5], labels[2, 3, 6] = float(np.cos(angle)), float(np.sin(angle))  # 170 deg turn in one step
    assert donk.step_violations(labels).tolist() == [False, True, True]
    labels[1, 5, 7] = 0                                           # dead at that step: not a move
    assert donk.step_violations(labels).tolist() == [False, False, True]


def test_path_steps_detect_backwards_walking_and_turns():
    start = [0, 0, 0]
    points = [[-20, 0, 0], [-40, 0, 0], [-40, 20, 0]]             # 20 units per step towards -X, then +Y
    yaws = [0, 0, 90]                                             # looking towards +X, then +Y
    move, turn, pitch, back = donk.path_steps(start, points, yaws, [0, 0, 0], start_yaw=0)
    assert np.allclose(move, [20, 20, 20])
    assert back.tolist() == [True, True, False]
    assert np.allclose(turn, [0, 0, 90])


def test_pass_rule():
    rng = np.random.default_rng(0)
    real = {"move": rng.normal(30, 10, 500), "turn": rng.exponential(10, 500), "pitch": np.zeros(500),
            "back": rng.random(500) < 0.09}
    good = {"mean_ade": list(rng.normal(80, 5, 60)), "move": rng.normal(30, 10, 500), "turn": rng.exponential(10, 500),
            "pitch": np.zeros(500), "back": rng.random(500) < 0.09}
    base = {"mean_ade": list(np.asarray(good["mean_ade"]) + 10), "move": rng.normal(40, 10, 500),
            "turn": rng.exponential(20, 500), "pitch": np.zeros(500), "back": rng.random(500) < 0.2}
    result = donk.judge({"donk": good, "base": base}, real)
    assert result["P1_mean_ade"]["pass"] and result["P2_behaviour"]["pass"] and result["pass"]
    worse = donk.judge({"donk": base, "base": good}, real)
    assert not worse["pass"]
    assert donk.w1([1, 2, 3], [1, 2, 3]) == 0
