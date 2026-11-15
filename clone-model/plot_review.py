"""Draw the offline review artifact with Matplotlib; no map/collision approval implied."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("review", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.review.read_text())
    if data.get("format") != "cs2.clone.review.v1" or data.get("split") != "dev":
        raise ValueError("Expected a development review artifact")
    cases = data["cases"]
    if not cases:
        raise ValueError("No cases to plot")
    rows = (len(cases)+1)//2
    fig, axes = plt.subplots(rows, 2, figsize=(12, 3.5*rows), squeeze=False, layout="constrained")
    styles = [("actual", "Real player", "#111827", "-"),
        ("own", "Own identity", "#2563eb", "-"),
        ("other", "Other identity", "#ea580c", "--"),
        ("base", "Generic base", "#6b7280", ":")]
    for ax, case in zip(axes.flat, cases):
        start = np.asarray(case["start_position"], dtype=float)
        for key, label, color, linestyle in styles:
            trace = case["actual"] if key == "actual" else case["predictions"][key]
            xy = np.asarray([start[:2].tolist()] + [p[1:3] for p in trace["path"]])
            ax.plot(xy[:, 0], xy[:, 1], color=color, linestyle=linestyle, linewidth=2,
                alpha=.85, label=label)
            ax.scatter(*xy[-1], color=color, s=16)
        ax.scatter(*start[:2], marker="x", s=45, color="#111827", zorder=10)
        ax.set_title(f"{case['player']} | {case['match_id']} r{case['round_id']} (zero-based), {case['side']}\n"
            f"context at {case['seconds_into_round']:.2f} s", fontsize=10)
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_xlabel("X (Source units)"); ax.set_ylabel("Y (Source units)")
        ax.grid(alpha=.15)
    for ax in list(axes.flat)[len(cases):]:
        ax.set_visible(False)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4, frameon=False)
    fig.suptitle(f"Development paths for review | selected checkpoint {data['selected_step']}\n"
        "Diagnostic examples, not held-out accuracy; no map geometry or collision approval", fontsize=12)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=170)
    plt.close(fig)
    print(f"PLOTTED {len(cases)} cases: {args.out}")


if __name__ == "__main__":
    main()
