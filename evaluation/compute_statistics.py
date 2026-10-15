"""
compute_statistics.py
=====================
Step 4 of the pipeline. From ``raw_distances.csv`` (written by
compute_distances.py) compute:

  * summary_statistics.csv : mean, median, SD and 95% CI per metric and variant;
  * global_tests.csv       : Friedman test across the three variants, per metric;
  * paired_tests.csv       : paired post-hoc comparisons (Wilcoxon signed-rank,
                             matched-pairs rank-biserial correlation r_rb, wins),
                             with the Holm-Bonferroni correction applied globally
                             over the whole family of post-hoc tests ("posthoc_eligible"
                             metrics, i.e. those where the Friedman test rejects H0;
                             tests that cannot be computed, such as identical
                             case-arrival values for two variants, are not part of the family).

No distance is recomputed here, so it runs in seconds and needs neither the logs
nor the PuLP solver.

Usage:
    python compute_statistics.py --raw-csv results/raw_distances.csv --output-dir results
"""

from __future__ import annotations

import argparse
import warnings
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare

from stats_utils import holm_adjust, paired_stats, summarize_vector

# For the case-arrival metrics the Planner-only and Planner + intervention values are
# identical by construction (both use the same scheduler-driven arrivals), so the
# Friedman/Wilcoxon statistics are undefined (division by zero) and become NaN.
# Those tests are not part of the post-hoc family; the SciPy warnings are expected.
warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"scipy\.stats")

FRIEDMAN_ALPHA = 0.05
VARIANTS = ["oro", "estatico", "dinamico"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-csv", type=Path, required=True, help="raw_distances.csv")
    parser.add_argument("--output-dir", type=Path, required=True, help="Where to write the CSV files.")
    args = parser.parse_args()

    raw_df = pd.read_csv(args.raw_csv)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- 1. Summary statistics ---------------------------------------------------
    summary_rows = []
    for metric_name, metric_group in raw_df.groupby("metric"):
        for variant, variant_group in metric_group.groupby("variant"):
            dist_summary = summarize_vector(variant_group["distance"].tolist())
            sim_summary = summarize_vector(variant_group["similarity_1_over_1_plus_d"].tolist())
            summary_rows.append({
                "metric": metric_name,
                "comparison": f"real_adaptado_vs_{variant}",
                "variant": variant,
                "distance_n": dist_summary["n"],
                "distance_mean": dist_summary["mean"],
                "distance_median": dist_summary["median"],
                "distance_std": dist_summary["std"],
                "distance_ci95": dist_summary["ci"],
                "similarity_mean": sim_summary["mean"],
                "similarity_median": sim_summary["median"],
                "similarity_std": sim_summary["std"],
                "similarity_ci95": sim_summary["ci"],
                "mean_runtime_sec": float(variant_group["runtime_sec"].mean()),
            })
    summary_df = pd.DataFrame(summary_rows).sort_values(["metric", "variant"]).reset_index(drop=True)
    summary_df.to_csv(output_dir / "summary_statistics.csv", index=False)

    # --- 2. Friedman global test per metric --------------------------------------
    global_rows = []
    friedman_p_by_metric: dict[str, float] = {}
    for metric_name, metric_group in raw_df.groupby("metric"):
        pivot = metric_group.pivot_table(index="run_id", columns="variant", values="distance", aggfunc="mean")
        present_variants = [v for v in VARIANTS if v in pivot.columns]
        pivot = pivot[present_variants].dropna()

        if len(present_variants) >= 3 and len(pivot) >= 3:
            stat, pvalue = friedmanchisquare(*[pivot[v].to_numpy() for v in present_variants])
            global_rows.append({"metric": metric_name, "test": "friedman",
                                "n_pairs": int(len(pivot)), "statistic": float(stat), "p_value": float(pvalue)})
            friedman_p_by_metric[metric_name] = float(pvalue)
        else:
            global_rows.append({"metric": metric_name, "test": "friedman",
                                "n_pairs": int(len(pivot)), "statistic": np.nan, "p_value": np.nan})
            friedman_p_by_metric[metric_name] = np.nan

    global_df = pd.DataFrame(global_rows).sort_values("metric").reset_index(drop=True)
    global_df.to_csv(output_dir / "global_tests.csv", index=False)

    # --- 3. Paired post-hoc comparisons (Wilcoxon + rank-biserial r) ---------------
    paired_rows = []
    for metric_name, metric_group in raw_df.groupby("metric"):
        pivot = metric_group.pivot_table(index="run_id", columns="variant", values="distance", aggfunc="mean")
        present_variants = [v for v in VARIANTS if v in pivot.columns]
        pivot = pivot[present_variants].dropna()

        friedman_p = friedman_p_by_metric.get(metric_name, np.nan)
        posthoc_eligible = (not np.isnan(friedman_p)) and (friedman_p < FRIEDMAN_ALPHA)

        current_metric_rows = []
        for va, vb in combinations(present_variants, 2):
            pair = pivot[[va, vb]].dropna()
            stats = paired_stats(pair[va].tolist(), pair[vb].tolist())
            row = {
                "metric": metric_name,
                "comparison_a": va,
                "comparison_b": vb,
                "friedman_p": friedman_p,
                "posthoc_eligible": posthoc_eligible,
                **stats,
            }
            paired_rows.append(row)
            current_metric_rows.append(row)

        # Holm correction within the 3 comparisons of one metric. Kept only for
        # comparison; the article reports the global correction below.
        pvals_within = [r["wilcoxon_p"] for r in current_metric_rows]
        adjusted_within = (
            holm_adjust(pvals_within) if pvals_within and any(not np.isnan(v) for v in pvals_within)
            else [np.nan] * len(current_metric_rows)
        )
        for row, adj in zip(current_metric_rows, adjusted_within):
            row["wilcoxon_p_holm_within_metric"] = adj

    paired_df = pd.DataFrame(paired_rows).sort_values(["metric", "comparison_a", "comparison_b"]).reset_index(drop=True)

    # Global Holm-Bonferroni: family = every computable post-hoc comparison of the
    # metrics for which the Friedman test rejects H0 (bigram/trigram are excluded:
    # their distance is constant).
    paired_df["wilcoxon_p_holm_global"] = np.nan
    n_family = 0
    if not paired_df.empty:
        eligible_mask = paired_df["posthoc_eligible"] & paired_df["wilcoxon_p"].notna()
        eligible_pvals = paired_df.loc[eligible_mask, "wilcoxon_p"].tolist()
        n_family = len(eligible_pvals)
        if eligible_pvals:
            paired_df.loc[eligible_mask, "wilcoxon_p_holm_global"] = holm_adjust(eligible_pvals)

    paired_df.to_csv(output_dir / "paired_tests.csv", index=False)

    n_metrics_eligible = sum(1 for v in friedman_p_by_metric.values() if not np.isnan(v) and v < FRIEDMAN_ALPHA)
    print(f"Statistics written to: {output_dir}")
    print(f"Metrics: {len(friedman_p_by_metric)} | with a significant Friedman test: {n_metrics_eligible}")
    print(f"Post-hoc tests in the global Holm family: {n_family}")


if __name__ == "__main__":
    main()
