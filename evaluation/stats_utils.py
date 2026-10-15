"""
stats_utils.py
==============
Small statistical helpers shared by the evaluation scripts. They do not depend
on the distance-metric code (no PuLP / jellyfish needed), so the statistical
stage of the pipeline can be run from ``raw_distances.csv`` alone.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
from scipy.stats import binomtest, rankdata, t, ttest_rel, wilcoxon


def summarize_vector(values: Iterable[float], confidence: float = 0.95) -> dict:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    if n == 0:
        return {"n": 0, "mean": np.nan, "median": np.nan, "std": np.nan, "ci": np.nan}
    if n == 1:
        return {"n": 1, "mean": float(arr[0]), "median": float(arr[0]), "std": np.nan, "ci": np.nan}
    sample_mean = float(np.mean(arr))
    sample_std = float(np.std(arr, ddof=1))
    t_value = float(t.ppf(1 - (1 - confidence) / 2, n - 1))
    ci = t_value * sample_std / np.sqrt(n)
    return {
        "n": n,
        "mean": sample_mean,
        "median": float(np.median(arr)),
        "std": sample_std,
        "ci": float(ci),
    }


def holm_adjust(pvalues: list[float]) -> list[float]:
    indexed = sorted(enumerate(pvalues), key=lambda item: (np.nan_to_num(item[1], nan=1.0), item[0]))
    adjusted = [np.nan] * len(pvalues)
    m = len(pvalues)
    prev = 0.0
    for rank, (idx, pvalue) in enumerate(indexed, start=1):
        if np.isnan(pvalue):
            adjusted[idx] = np.nan
            continue
        adj = min(1.0, (m - rank + 1) * pvalue)
        prev = max(prev, adj)
        adjusted[idx] = prev
    return adjusted


def rank_biserial_from_diff(diff: np.ndarray) -> tuple[float, int]:
    """
    Matched-pairs rank-biserial correlation associated with the Wilcoxon
    signed-rank test: r_rb = (W+ - W-) / (W+ + W-).

    It is computed directly from the signed differences (ranked by absolute
    value) instead of relying on the statistic returned by
    scipy.stats.wilcoxon, whose sign convention can change between SciPy
    versions. Zero differences (ties) are discarded, as SciPy does with
    zero_method="wilcox".

    Returns (r_rb, number_of_non_zero_differences). r_rb lies in [-1, 1];
    +/-1 means that all the differences have the same sign.
    """
    diff = np.asarray(diff, dtype=float)
    diff = diff[diff != 0]
    n = len(diff)
    if n == 0:
        return float("nan"), 0

    abs_diff = np.abs(diff)
    ranks = rankdata(abs_diff)
    w_pos = float(ranks[diff > 0].sum())
    w_neg = float(ranks[diff < 0].sum())
    total = w_pos + w_neg
    if total == 0:
        return float("nan"), n
    return (w_pos - w_neg) / total, n


def paired_stats(a_values: list[float], b_values: list[float]) -> dict:
    """
    Compare two variants (a, b) replicate by replicate. Sign convention:
    diff = b - a. A positive rank_biserial_r means that b tends to have higher
    values than a (for distances: b is worse than a more often than not).
    """
    a = np.asarray(a_values, dtype=float)
    b = np.asarray(b_values, dtype=float)
    mask = ~np.isnan(a) & ~np.isnan(b)
    a = a[mask]
    b = b[mask]
    diff = b - a

    out = {
        "n_pairs": int(len(diff)),
        "mean_diff_b_minus_a": float(np.mean(diff)) if len(diff) else np.nan,
        "median_diff_b_minus_a": float(np.median(diff)) if len(diff) else np.nan,
        "cohen_dz": np.nan,  # kept for traceability only; the article reports rank_biserial_r
        "rank_biserial_r": np.nan,
        "n_nonzero_diff": 0,
        "wins_a": int(np.sum(a < b)),
        "wins_b": int(np.sum(b < a)),
        "ties": int(np.sum(a == b)),
        "sign_test_p": np.nan,
        "paired_t_p": np.nan,
        "wilcoxon_p": np.nan,
    }

    if len(diff) >= 2:
        std_diff = float(np.std(diff, ddof=1))
        if std_diff > 0:
            out["cohen_dz"] = float(np.mean(diff) / std_diff)

        r_rb, n_nz = rank_biserial_from_diff(diff)
        out["rank_biserial_r"] = r_rb
        out["n_nonzero_diff"] = n_nz

        out["paired_t_p"] = float(ttest_rel(b, a, nan_policy="omit").pvalue)
        try:
            out["wilcoxon_p"] = float(
                wilcoxon(b, a, zero_method="wilcox", alternative="two-sided", method="auto").pvalue
            )
        except ValueError:
            out["wilcoxon_p"] = np.nan
        success = int(np.sum(diff > 0))
        failures = int(np.sum(diff < 0))
        if success + failures > 0:
            out["sign_test_p"] = float(
                binomtest(success, n=success + failures, p=0.5, alternative="two-sided").pvalue
            )

    return out
