"""CPU tests for self-training on imagined play (imagine.py). A tiny random CS-NET and a stub engine stand in."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_learned import upstream  # noqa: F401  (fixture)
from test_donk import tiny_base
import donk
import imagine


def line(n, step, yaw=0.0):
    return [[step * (i + 1), 0.0, 0.0] for i in range(n)], [yaw] * n, [0.0] * n


def test_judge_keeps_the_closest_future_that_stays_human():
    gt_pts, gt_yaw, gt_pitch = line(16, 20)
    near_bad, y1, p1 = line(16, 20)
    y1 = [0.0] * 8 + [170.0] + [170.0] * 7                       # a 170 degree turn in one step
    near_ok, y2, p2 = line(16, 22)
    far, y3, p3 = line(16, 40)
    result = {"start_pos": [0, 0, 0], "gt": {"gt_points": gt_pts, "gt_yaw": gt_yaw, "gt_pitch": gt_pitch},
              "samples": [{"pred_points": far, "pred_yaw": y3, "pred_pitch": p3},
                          {"pred_points": near_bad, "pred_yaw": y1, "pred_pitch": p1},
                          {"pred_points": near_ok, "pred_yaw": y2, "pred_pitch": p2}]}
    best, ade = imagine.judge_samples(result)
    assert best == 2 and ade > 0
    result["gt"]["gt_points"], _, _ = line(16, 90)                # the real future itself is impossible
    assert imagine.judge_samples(result) == (None, None)


def test_test_rounds_are_cut_by_round_number():
    data = SimpleNamespace(by_player={"donk": [0, 1, 2]},
                           index=[({"match_id": "1", "round_id": 3}, 0), ({"match_id": "1", "round_id": 4}, 0),
                                  ({"match_id": "2", "round_id": 10}, 16)])
    pool, test = imagine.split_training(data)
    assert pool == [1, 2] and test == [0]


def test_recorder_returns_the_decoder_inputs_and_they_train(upstream):  # noqa: F811
    base = tiny_base()
    n, d, k = base.cfg.n_ticks, base.cfg.d_model, 3

    class Engine:
        model, model_cfg = base, base.cfg

        def _compute_depth_emb(self, *a, **kw):
            return torch.randn(k, d)

        def _compute_xyz_emb(self, *a, **kw):
            return torch.randn(k, d)

        def _compute_angle_emb(self, *a, **kw):
            return None                                          # all dead at that step: recorded as zeros

        def predict_at_tick_player_sampled(self, sample, tick, player_idx, num_samples, temperature, top_p):
            self.model.get_player_embeddings(None)
            for t in range(n):
                self._compute_depth_emb(); self._compute_xyz_emb(); self._compute_angle_emb()
                self.model.decoder.generate_group(None, t)
            return {"samples": [{}] * num_samples}

    base.get_player_embeddings = lambda batch: torch.randn(1, 4, 10, d)
    base.decoder.generate_group = lambda x, t, **kw: (torch.randint(0, 50, (k, 7)), x)
    rec = imagine.Recorder(Engine())
    _, inputs = rec.sample(None, 0, 2, k)
    assert inputs["tokens"].shape == (k, 7 * n)
    assert inputs["depth"].shape == inputs["xyz"].shape == inputs["angle"].shape == (k, n, d)
    assert float(inputs["angle"].abs().sum()) == 0
    assert inputs["start"].shape == (k, d)
    kept = [{key: v[i] for key, v in inputs.items()} for i in range(k)]
    loras = donk.add_lora(base.decoder, r=4)
    for lora in loras:
        lora.A.requires_grad_(True); lora.B.requires_grad_(True)
    nll, kl = donk.losses(base, loras, imagine.imagined_batch(kept, 2, "cpu"))
    assert torch.isfinite(nll) and abs(float(kl)) < 1e-6
    nll.backward()
    assert all(lora.B.grad is not None for lora in loras)
