"""
check_activity_vocabulary.py
============================
Diagnostic (optional) that supports the discussion in Sections 5.4 and 5.5 of the
article: why the bigram and trigram distances are constant (= 1.0, the maximum)
for the three variants.

It reads the logs (it does not recompute any distance) and:
  1. extracts the activity vocabulary of each simulated variant and of the adapted
     real-world log;
  2. computes the exact overlap (Jaccard index = intersection / union);
  3. computes the overlap after a superficial normalisation (lower case, trimmed
     spaces, removal of life-cycle suffixes such as '+complete' or '_start');
  4. prints an automatic interpretation: a high normalised but low exact overlap
     points to a labelling/format problem; both low means that the activity
     granularity of the process model differs from that of the real log.

Usage:
    python check_activity_vocabulary.py --data-dir data
    python check_activity_vocabulary.py --data-dir data --run-ids 1 2 3
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from compute_distances import (
    HERE,
    adapted_log_path,
    discover_run_ids,
    load_event_log,
    variant_log_path,
)

VARIANTS = ["oro", "estatico", "dinamico"]
LIFECYCLE_SUFFIX_RE = re.compile(r"[+_\-\s](start|complete|end|schedule|suspend|resume)$", re.IGNORECASE)


def normalize(name: str) -> str:
    n = name.strip().lower()
    n = LIFECYCLE_SUFFIX_RE.sub("", n).strip()
    n = re.sub(r"\s+", " ", n)
    return n


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=HERE / "data")
    parser.add_argument("--adapted-dir", type=Path, default=None, help="default: <data-dir>/logRealAdaptado")
    parser.add_argument("--run-ids", type=int, nargs="*", default=None,
                        help="Subset of replicates to inspect (default: all the replicates in common).")
    args = parser.parse_args()

    base_dir = args.data_dir.resolve()
    adapted_dir = (args.adapted_dir or (base_dir / "logRealAdaptado")).resolve()
    run_ids = args.run_ids or discover_run_ids(base_dir, adapted_dir)
    if not run_ids:
        raise RuntimeError("No replicate in common between the variants and the adapted real-world log.")

    print(f"Analysing {len(run_ids)} replicate(s): {run_ids}\n")

    all_real_activities: set[str] = set()
    all_variant_activities: dict[str, set[str]] = {v: set() for v in VARIANTS}

    for run_id in run_ids:
        ref_path = adapted_log_path(adapted_dir, run_id)
        if not ref_path.exists():
            print(f"  [WARN] Replicate {run_id}: {ref_path.name} is missing in the adapted log, skipped.")
            continue
        real_df = load_event_log(ref_path)
        all_real_activities |= set(real_df["activity"].unique())

        for variant in VARIANTS:
            other_path = variant_log_path(base_dir, run_id, variant)
            if not other_path.exists():
                print(f"  [WARN] Replicate {run_id}, variant {variant}: {other_path.name} does not exist, skipped.")
                continue
            other_df = load_event_log(other_path)
            all_variant_activities[variant] |= set(other_df["activity"].unique())

    print("=" * 78)
    print(f"Vocabulary of the adapted real-world log: {len(all_real_activities)} unique activities")
    print(f"  Sample: {sorted(all_real_activities)[:20]}")
    print("=" * 78)

    real_norm = {normalize(a) for a in all_real_activities}
    summary = []

    for variant in VARIANTS:
        var_activities = all_variant_activities[variant]
        var_norm = {normalize(a) for a in var_activities}

        exact_overlap = jaccard(all_real_activities, var_activities)
        norm_overlap = jaccard(real_norm, var_norm)
        summary.append((variant, exact_overlap, norm_overlap))

        only_in_real = sorted(all_real_activities - var_activities)[:10]
        only_in_variant = sorted(var_activities - all_real_activities)[:10]

        print(f"\n--- Variant: {variant} ---")
        print(f"  Unique activities: {len(var_activities)}")
        print(f"  Sample: {sorted(var_activities)[:15]}")
        print(f"  EXACT Jaccard      vs adapted real log: {exact_overlap:.3f}")
        print(f"  NORMALISED Jaccard vs adapted real log: {norm_overlap:.3f}")
        print(f"  Only in the adapted real log (sample, up to 10): {only_in_real}")
        print(f"  Only in {variant} (sample, up to 10):     {only_in_variant}")

    print("\n" + "=" * 78)
    print("AUTOMATIC INTERPRETATION")
    print("=" * 78)
    for variant, exact_overlap, norm_overlap in summary:
        if norm_overlap >= 0.7 and exact_overlap < 0.3:
            print(f"[{variant}] -> Looks like a LABELLING/FORMAT problem "
                  f"(normalised {norm_overlap:.2f} vs exact {exact_overlap:.2f}): harmonising the activity "
                  f"names before computing bigram/trigram should reduce the distance.")
        elif norm_overlap < 0.3 and exact_overlap < 0.3:
            print(f"[{variant}] -> Looks like a REAL granularity difference "
                  f"(both Jaccard indices low: exact {exact_overlap:.2f}, normalised {norm_overlap:.2f}): "
                  f"the process model used for the simulation does not reproduce the atomic activities of "
                  f"the real log.")
        else:
            print(f"[{variant}] -> Intermediate result (exact {exact_overlap:.2f}, "
                  f"normalised {norm_overlap:.2f}); inspect the 'only in ...' samples above.")
    print("=" * 78)


if __name__ == "__main__":
    main()
