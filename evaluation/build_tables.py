"""
build_tables.py
===============
Step 5 of the pipeline. From summary_statistics.csv and paired_tests.csv
(written by compute_statistics.py) build:

  * table1_mean_sd.csv / .tex : Table 1 of the article, "mean (SD)" of each
    distance metric for the three variants over the same replicates, plus the
    variant with the lowest mean ("Winning Variant"; it denotes the lowest mean
    only, not a statistically significant difference);
  * tableS1_pairwise_tests.csv / .tex : Supplementary Table S1, the post-hoc
    comparisons of the metrics for which the Friedman test rejects H0 that could
    be computed (the family of 25 tests), with the raw Wilcoxon p-value, the
    globally Holm-adjusted p-value and the rank-biserial effect size r_rb.

Usage:
    python build_tables.py --stats-dir results
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# Order of the metrics in Table 1 (bigram/trigram are excluded: their distance is
# constant, 1.0, for the three variants).
METRIC_ORDER = [
    "absolute_emd", "absolute_wass",
    "case_arrival_emd", "case_arrival_wass",
    "circadian_emd", "circadian_wass",
    "relative_emd", "relative_wass",
    "cycle_time_wass",
]
# Variant ids used in the data files -> names used in the article
VARIANT_LABELS = {"estatico": "Baseline", "oro": "Planner-only", "dinamico": "Planner + intervention"}


def fmt(mean: float, std: float, decimals: int = 2) -> str:
    if pd.isna(mean):
        return "--"
    std_str = f"{std:.{decimals}f}" if not pd.isna(std) else "n/a"
    return f"{mean:.{decimals}f} ({std_str})"


def build_table1(summary_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in METRIC_ORDER:
        sub = summary_df[summary_df["metric"] == metric]
        if sub.empty:
            continue
        row = {"Metric": metric}
        best_variant, best_mean = None, None
        for variant in ["estatico", "oro", "dinamico"]:
            m = sub[sub["variant"] == variant]
            if m.empty:
                row[VARIANT_LABELS[variant]] = "--"
                continue
            mean_v = float(m["distance_mean"].iloc[0])
            std_v = float(m["distance_std"].iloc[0])
            row[VARIANT_LABELS[variant]] = fmt(mean_v, std_v)
            if best_mean is None or mean_v < best_mean:
                best_mean, best_variant = mean_v, variant
        row["Winning Variant"] = f"{VARIANT_LABELS[best_variant]} Log" if best_variant else "--"
        rows.append(row)
    return pd.DataFrame(rows)


def build_table_s1(paired_df: pd.DataFrame) -> pd.DataFrame:
    if "posthoc_eligible" not in paired_df.columns:
        raise ValueError("paired_tests.csv has no 'posthoc_eligible' column; regenerate it with compute_statistics.py.")
    eligible = paired_df[paired_df["posthoc_eligible"] & paired_df["wilcoxon_p"].notna()].copy()
    eligible = eligible.sort_values(["metric", "comparison_a", "comparison_b"])
    eligible["comparison"] = (
        eligible["comparison_a"].map(VARIANT_LABELS) + " vs " + eligible["comparison_b"].map(VARIANT_LABELS)
    )
    cols = ["metric", "comparison", "n_pairs", "wilcoxon_p", "wilcoxon_p_holm_global", "rank_biserial_r",
            "wins_a", "wins_b"]
    missing = [c for c in cols if c not in eligible.columns]
    if missing:
        raise ValueError(f"Columns missing in paired_tests.csv: {missing}")

    out = eligible[cols].rename(columns={
        "metric": "Metric",
        "comparison": "Comparison",
        "n_pairs": "N",
        "wilcoxon_p": "Wilcoxon p (raw)",
        "wilcoxon_p_holm_global": "p (Holm, global)",
        "rank_biserial_r": "r_rb",
        "wins_a": "Wins A",
        "wins_b": "Wins B",
    })
    return out.reset_index(drop=True)


def write_latex(df: pd.DataFrame, path: Path, caption: str, label: str) -> None:
    try:
        latex = df.to_latex(index=False, caption=caption, label=label, float_format="%.3f")
    except TypeError:  # old pandas without caption/label support
        latex = df.to_latex(index=False, float_format="%.3f")
        latex = f"% caption: {caption}\n% label: {label}\n" + latex
    path.write_text(latex)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stats-dir", type=Path, required=True,
                        help="Directory with summary_statistics.csv and paired_tests.csv (also used for the output).")
    args = parser.parse_args()

    stats_dir = args.stats_dir.resolve()
    summary_df = pd.read_csv(stats_dir / "summary_statistics.csv")
    paired_df = pd.read_csv(stats_dir / "paired_tests.csv")

    table1 = build_table1(summary_df)
    table1.to_csv(stats_dir / "table1_mean_sd.csv", index=False)
    write_latex(
        table1, stats_dir / "table1_mean_sd.tex",
        "Summary of mean (SD) distance metrics across 30 replicates against the adapted real-world log (lower is better).",
        "tab:results",
    )

    table_s1 = build_table_s1(paired_df)
    table_s1.to_csv(stats_dir / "tableS1_pairwise_tests.csv", index=False)
    write_latex(
        table_s1, stats_dir / "tableS1_pairwise_tests.tex",
        "Post-hoc pairwise Wilcoxon tests (Holm-Bonferroni corrected across the global family) "
        "with matched-pairs rank-biserial effect sizes (r_rb).",
        "tab:posthoc",
    )

    print(f"Table 1  -> {stats_dir / 'table1_mean_sd.csv'}  (and .tex)")
    print(f"Table S1 -> {stats_dir / 'tableS1_pairwise_tests.csv'}  (and .tex, {len(table_s1)} rows)")


if __name__ == "__main__":
    main()
