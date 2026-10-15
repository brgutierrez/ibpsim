#!/usr/bin/env python3
"""
replication_analysis.py
=======================
Reproduces the analyses of the number of replicates reported in the
"Statistical Methodology" section of the article:

  (A) Resampling analysis. For each subset size n in {10, 15, 20, 25}, draw
      random subsets of the 30 replicates (without replacement), repeat the
      whole post-hoc procedure on each subset (paired Wilcoxon signed-rank
      tests + Holm-Bonferroni correction over the same family of 25 tests)
      and report how often each comparison that is significant with the full
      set of 30 replicates is still significant.

  (B) Robustness checks.
        (i)  post-hoc analysis excluding replicate 1 (its reference window
             contained fewer than 20 cases, so the sample was completed with
             repetitions);
        (ii) post-hoc analysis on subsets of 10 replicates whose reference
             windows do not overlap (replicates r, r+3, r+6, ...).

Input : raw_distances.csv produced by the experiment (columns: run_id,
        variant, metric, distance). Variant names in the file:
        'oro' = Planner-only Log, 'dinamico' = Planner + intervention Log,
        'estatico' = Baseline Log.
Output: printed summary (and, optionally, a CSV with the resampling results).

Usage:
    python replication_analysis.py
    python replication_analysis.py --raw path/to/raw_distances.csv \
        --subsets 300 --seed 1 --out resampling_results.csv

Requirements: numpy, pandas, scipy.
Note: the resampling subsets are drawn from the same 30 replicates, so (A) is
an indicative analysis, not a formal power analysis.
"""

import argparse
import numpy as np
import pandas as pd
from scipy import stats

DEFAULT_RAW = "results/raw_distances.csv"
UNINFORMATIVE = ["bigram", "trigram"]           # zero variance: not tested
PAIRS = [("estatico", "dinamico"),              # Baseline vs Planner+intervention
         ("oro", "dinamico"),                   # Planner-only vs Planner+intervention
         ("oro", "estatico")]                   # Planner-only vs Baseline
SIZES = (10, 15, 20, 25)
NAMES = {"estatico": "Baseline", "oro": "Planner-only", "dinamico": "Planner+intervention"}


def load_differences(path):
    """Return the list of tests and an array D[test, replicate] of paired differences."""
    d = pd.read_csv(path)
    d = d[~d.metric.isin(UNINFORMATIVE)]
    piv = d.pivot_table(index=["metric", "run_id"], columns="variant", values="distance")
    run_ids = sorted(d.run_id.unique())
    metrics = sorted(d.metric.unique())
    tests = [(m, a, b) for m in metrics for a, b in PAIRS
             # case-arrival values are identical by construction for these two variants
             if not (m.startswith("case_arrival") and (a, b) == ("oro", "dinamico"))]
    D = np.array([(piv.loc[m].loc[run_ids, a] - piv.loc[m].loc[run_ids, b]).values
                  for m, a, b in tests])
    return tests, D, run_ids


def holm(pvals):
    """Holm-Bonferroni adjusted p-values (step-down, monotone)."""
    pvals = np.asarray(pvals, dtype=float)
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return adj


def significant_set(D, idx, alpha=0.05):
    """Indices of tests significant after Holm over the whole family, using replicates idx."""
    p = np.array([stats.wilcoxon(D[t][idx]).pvalue for t in range(D.shape[0])])
    return set(np.where(holm(p) < alpha)[0])


def label(test):
    m, a, b = test
    return f"{m}: {NAMES[a]} vs {NAMES[b]}"


def is_vs_baseline(test):
    return "estatico" in (test[1], test[2])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default=DEFAULT_RAW, help="path to raw_distances.csv")
    ap.add_argument("--subsets", type=int, default=300, help="random subsets per size (default 300)")
    ap.add_argument("--seed", type=int, default=1, help="random seed (default 1)")
    ap.add_argument("--out", default=None, help="optional CSV with the resampling results")
    args = ap.parse_args()

    tests, D, run_ids = load_differences(args.raw)
    n_rep = D.shape[1]
    if n_rep <= max(SIZES):
        raise SystemExit(f"This analysis needs more than {max(SIZES)} replicates (found {n_rep}); "
                         f"it is meant for the full 30-replicate experiment.")
    all_idx = np.arange(n_rep)
    full = significant_set(D, all_idx)
    vs_base = [i for i in full if is_vs_baseline(tests[i])]
    fine = [i for i in full if not is_vs_baseline(tests[i])]
    print(f"Replicates: {n_rep} | family of tests: {len(tests)}")
    print(f"Significant with all replicates (Holm, alpha=0.05): {len(full)} "
          f"({len(vs_base)} against the baseline, {len(fine)} between the proposed variants)")
    for i in fine:
        print("  proposed-vs-proposed:", label(tests[i]))

    # ---- (A) resampling analysis -------------------------------------------------
    print(f"\n(A) Resampling analysis: {args.subsets} random subsets per size, seed={args.seed}")
    rng = np.random.default_rng(args.seed)
    rows = []
    for n in SIZES:
        counts = np.zeros(len(tests))
        for _ in range(args.subsets):
            idx = rng.choice(n_rep, n, replace=False)
            for i in significant_set(D, idx):
                counts[i] += 1
        share = counts / args.subsets
        min_base = min(share[i] for i in vs_base) if vs_base else float("nan")
        print(f"  n={n:2d}: each baseline comparison significant in at least {100*min_base:.0f}% of subsets "
              f"(minimum over the {len(vs_base)} comparisons); "
              + "; ".join(f"{label(tests[i])} in {100*share[i]:.0f}%" for i in fine))
        for i in sorted(full):
            rows.append({"n": n, "test": label(tests[i]), "share_significant": share[i]})
    if args.out:
        pd.DataFrame(rows).to_csv(args.out, index=False)
        print(f"  results written to {args.out}")

    # ---- (B) robustness checks ---------------------------------------------------
    def report(name, idx):
        s = significant_set(D, np.array(idx))
        rec_base = len([i for i in s if is_vs_baseline(tests[i])])
        lost = [label(tests[i]) for i in sorted(full - s)]
        print(f"  {name} (n={len(idx)}): {rec_base}/{len(vs_base)} comparisons against the baseline significant; "
              f"lost vs full set: {lost if lost else 'none'}")

    print("\n(B) Robustness checks")
    report("excluding replicate 1", list(range(1, n_rep)))
    for off in range(3):
        report(f"non-overlapping windows, replicates {off+1},{off+4},{off+7},...",
               list(range(off, n_rep, 3)))


if __name__ == "__main__":
    main()