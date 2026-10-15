#!/usr/bin/env python3
"""Regenerates experimental_results_plots.pdf (Figure 2) from raw_distances.csv
with the naming used in the article: Baseline / Planner-only / Planner + intervention.
Usage: python make_figure.py [raw_distances.csv] [out.pdf]
"""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

raw = sys.argv[1] if len(sys.argv) > 1 else "results/raw_distances.csv"
out = sys.argv[2] if len(sys.argv) > 2 else "results/experimental_results_plots.pdf"

VARIANTS = [("estatico", "Baseline", "#808080"),
            ("oro", "Planner-only", "#2ca02c"),
            ("dinamico", "Planner + intervention", "#3274a1")]
FAMILIES = [("Absolute Time", ["absolute_emd", "absolute_wass"]),
            ("Case Arrival", ["case_arrival_emd", "case_arrival_wass"]),
            ("Circadian", ["circadian_emd", "circadian_wass"]),
            ("Relative Time", ["relative_emd", "relative_wass"]),
            ("Macro KPI", ["cycle_time_wass"])]

d = pd.read_csv(raw)
mean = d.groupby(["metric", "variant"]).distance.mean().unstack()

fig, axes = plt.subplots(2, 3, figsize=(13.85, 8.19))
axes = axes.ravel()
w = 0.27
for ax, (fam, metrics) in zip(axes, FAMILIES):
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#cccccc", lw=0.8)
    for j, (v, _, c) in enumerate(VARIANTS):
        xs = [i + (j - 1) * w for i in range(len(metrics))]
        ax.bar(xs, [mean.loc[m, v] for m in metrics], width=w, color=c, edgecolor="white", lw=0.6)
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(metrics, rotation=15, ha="right", fontsize=9)
    ax.set_xlim(-0.6, len(metrics) - 0.4)
    ax.set_title(f"Family: {fam}", fontsize=10, fontweight="bold")
    ax.set_ylabel("Distance (Lower is Better)", fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    for s in ax.spines.values():
        s.set_color("#cccccc")
axes[5].axis("off")
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in VARIANTS]
fig.legend(handles, [n for _, n, _ in VARIANTS], loc="upper center", ncol=3, fontsize=10, frameon=True)
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(out)
print("written", out)