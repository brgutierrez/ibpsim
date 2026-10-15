"""
compute_distances.py
====================
Step 3 of the pipeline. For every replicate r = 1..30 and every simulated
variant, compute the 11 distance metrics between the simulated log and the
adapted real-world log of the same replicate, and write them to
``raw_distances.csv`` (one row per replicate x variant x metric).

Directory layout (see README.md); names are kept from the original experiment:

    <data-dir>/logOro/<r>/merged_log.xes        Planner-only log       (variant id "oro")
    <data-dir>/logDinamico/<r>/merged_log.xes   Planner + intervention (variant id "dinamico")
    <data-dir>/logEstatico/<r>.csv|.xes         Baseline (Apromore)    (variant id "estatico")
    <data-dir>/logRealAdaptado/<r>/merged_log.xes   adapted real-world log (reference)

Usage:
    python compute_distances.py --data-dir data --output-dir results
    python compute_distances.py --run-ids 1 2 3      # subset of replicates

Requirements: numpy, pandas, scipy, pulp (LP solver for the EMD), jellyfish.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from distance_metrics import (
    DistanceMetric,
    absolute_event_distribution_distance,
    case_arrival_distribution_distance,
    circadian_event_distribution_distance,
    control_flow_log_distance,
    cycle_time_distribution_distance,
    n_gram_distribution_distance,
    relative_event_distribution_distance,
)

HERE = Path(__file__).resolve().parent
STANDARD_COLUMNS = ["case_id", "activity", "start_time", "end_time", "resource"]
VARIANTS = ["oro", "estatico", "dinamico"]
# Variant ids used in the CSV files  ->  names used in the article
VARIANT_NAMES = {"estatico": "Baseline", "oro": "Planner-only", "dinamico": "Planner + intervention"}


def _local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_xes_datetime(value: str | None) -> pd.Timestamp:
    if value is None:
        return pd.Timestamp("NaT")
    return pd.to_datetime(value, utc=True, errors="coerce")


def _normalize_event_log(df: pd.DataFrame) -> pd.DataFrame:
    missing = {"case_id", "activity", "start_time", "end_time"} - set(df.columns)
    if missing:
        raise ValueError(f"Missing mandatory columns in the log: {sorted(missing)}")

    data = df.copy()
    for col in ["start_time", "end_time"]:
        data[col] = pd.to_datetime(data[col], utc=True, errors="coerce")
    if "resource" not in data.columns:
        data["resource"] = pd.NA

    data = data[STANDARD_COLUMNS]
    data = data.dropna(subset=["case_id", "activity", "start_time", "end_time"])
    data["case_id"] = data["case_id"].astype(str)
    data["activity"] = data["activity"].astype(str)
    return data.sort_values(["case_id", "start_time", "end_time", "activity"]).reset_index(drop=True)


def load_xes_event_log(path: Path) -> pd.DataFrame:
    tree = ET.parse(path)
    root = tree.getroot()

    rows: list[dict[str, object]] = []
    for trace in (node for node in root.iter() if _local_name(node.tag) == "trace"):
        case_id = None
        for child in trace:
            if _local_name(child.tag) != "string":
                continue
            if child.attrib.get("key") in {"concept:name", "case:concept:name"}:
                case_id = child.attrib.get("value")
                break
        if case_id is None:
            case_id = str(len(rows))

        for event in (node for node in trace if _local_name(node.tag) == "event"):
            row: dict[str, object] = {
                "case_id": case_id,
                "activity": None,
                "start_time": None,
                "end_time": None,
                "resource": None,
            }
            for attr in event:
                tag = _local_name(attr.tag)
                key = attr.attrib.get("key")
                value = attr.attrib.get("value")
                if tag == "string" and key in {"concept:name", "activity", "event"} and row["activity"] is None:
                    row["activity"] = value
                elif tag == "string" and key in {"resource", "org:resource", "Resource"}:
                    row["resource"] = value
                elif tag == "date" and key in {"start_timestamp", "start_time"}:
                    row["start_time"] = _parse_xes_datetime(value)
                elif tag == "date" and key in {"time:timestamp", "end_time"}:
                    row["end_time"] = _parse_xes_datetime(value)

            if row["start_time"] is None and row["end_time"] is not None:
                row["start_time"] = row["end_time"]
            if row["end_time"] is None and row["start_time"] is not None:
                row["end_time"] = row["start_time"]
            rows.append(row)

    return _normalize_event_log(pd.DataFrame(rows, columns=STANDARD_COLUMNS))


def load_csv_event_log(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    rename_map = {}
    if "case:concept:name" in df.columns:
        rename_map["case:concept:name"] = "case_id"
    if "concept:name" in df.columns:
        rename_map["concept:name"] = "activity"
    if "Start_Time" in df.columns:
        rename_map["Start_Time"] = "start_time"
    if "End_Time" in df.columns:
        rename_map["End_Time"] = "end_time"
    if "start_timestamp" in df.columns:
        rename_map["start_timestamp"] = "start_time"
    if "time:timestamp" in df.columns:
        rename_map["time:timestamp"] = "end_time"
    if "Resource" in df.columns:
        rename_map["Resource"] = "resource"
    df = df.rename(columns=rename_map)
    return _normalize_event_log(df)


def load_event_log(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".xes":
        return load_xes_event_log(path)
    if suffix == ".csv":
        return load_csv_event_log(path)
    raise ValueError(f"Unsupported log format: {path}")


def discover_run_ids(base_dir: Path, adapted_dir: Path) -> list[int]:
    oro_ids = {int(path.name) for path in (base_dir / "logOro").iterdir() if path.is_dir() and path.name.isdigit()}
    dyn_ids = {int(path.name) for path in (base_dir / "logDinamico").iterdir() if path.is_dir() and path.name.isdigit()}
    adapted_ids = {int(path.name) for path in adapted_dir.iterdir() if path.is_dir() and path.name.isdigit()}

    est_ids_csv = {
        int(path.stem)
        for path in (base_dir / "logEstatico").glob("*.csv")
        if path.stem.isdigit()
    }
    est_ids_xes = {
        int(path.stem)
        for path in (base_dir / "logEstatico").glob("*.xes")
        if path.stem.isdigit()
    }
    est_ids = est_ids_csv | est_ids_xes
    return sorted(oro_ids & dyn_ids & est_ids & adapted_ids)


def variant_log_path(base_dir: Path, run_id: int, variant: str) -> Path:
    if variant == "oro":
        return base_dir / "logOro" / str(run_id) / "merged_log.xes"
    if variant == "dinamico":
        return base_dir / "logDinamico" / str(run_id) / "merged_log.xes"
    if variant == "estatico":
        csv_path = base_dir / "logEstatico" / f"{run_id}.csv"
        return csv_path if csv_path.exists() else (base_dir / "logEstatico" / f"{run_id}.xes")
    raise ValueError(f"Unsupported variant: {variant}")


def adapted_log_path(adapted_dir: Path, run_id: int) -> Path:
    return adapted_dir / str(run_id) / "merged_log.xes"


def compute_metrics_for_pair(
    gold: pd.DataFrame,
    other: pd.DataFrame,
    include_cfld: bool,
    include_workforce: bool = False,
) -> list[dict]:
    metrics = []

    def timed(name: str, func):
        start = time.perf_counter()
        value = func()
        runtime = time.perf_counter() - start
        metrics.append({"metric": name, "distance": float(value), "runtime_sec": runtime})

    timed("bigram", lambda: n_gram_distribution_distance(gold, other, n=2))
    timed("trigram", lambda: n_gram_distribution_distance(gold, other, n=3))
    if include_cfld:
        timed("cfld", lambda: control_flow_log_distance(gold, other))
    timed("absolute_emd", lambda: absolute_event_distribution_distance(gold, other, DistanceMetric.EMD))
    timed("absolute_wass", lambda: absolute_event_distribution_distance(gold, other, DistanceMetric.WASSERSTEIN))
    timed("case_arrival_emd", lambda: case_arrival_distribution_distance(gold, other, DistanceMetric.EMD))
    timed("case_arrival_wass", lambda: case_arrival_distribution_distance(gold, other, DistanceMetric.WASSERSTEIN))
    timed("circadian_emd", lambda: circadian_event_distribution_distance(gold, other, DistanceMetric.EMD))
    timed("circadian_wass", lambda: circadian_event_distribution_distance(gold, other, DistanceMetric.WASSERSTEIN))
    timed("relative_emd", lambda: relative_event_distribution_distance(gold, other, DistanceMetric.EMD))
    timed("relative_wass", lambda: relative_event_distribution_distance(gold, other, DistanceMetric.WASSERSTEIN))

    if include_workforce and gold["resource"].notna().any() and other["resource"].notna().any():
        from distance_metrics import circadian_workforce_distribution_distance

        timed("workforce_emd", lambda: circadian_workforce_distribution_distance(gold, other, DistanceMetric.EMD))
        timed("workforce_wass", lambda: circadian_workforce_distribution_distance(gold, other, DistanceMetric.WASSERSTEIN))

    bin_size = max(
        [events["end_time"].max() - events["start_time"].min() for _, events in gold.groupby("case_id")]
    ) / 1000
    timed("cycle_time_wass", lambda: cycle_time_distribution_distance(gold, other, bin_size, DistanceMetric.WASSERSTEIN))

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute the distance metrics between each simulated variant and the adapted real-world log."
    )
    parser.add_argument("--data-dir", type=Path, default=HERE / "data",
                        help="Directory with logOro/, logDinamico/, logEstatico/ and logRealAdaptado/.")
    parser.add_argument("--adapted-dir", type=Path, default=None,
                        help="Adapted real-world logs (default: <data-dir>/logRealAdaptado).")
    parser.add_argument("--output-dir", type=Path, default=HERE / "results", help="Output directory.")
    parser.add_argument("--run-ids", type=int, nargs="*", default=None, help="Replicates to process (default: all).")
    parser.add_argument("--include-cfld", action="store_true", help="Also compute CFLD (slower; not used in the article).")
    parser.add_argument("--include-workforce", action="store_true",
                        help="Also compute workforce metrics (needs a resource column in both logs; not used in the article).")
    args = parser.parse_args()

    base_dir = args.data_dir.resolve()
    adapted_dir = (args.adapted_dir or (base_dir / "logRealAdaptado")).resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    run_ids = args.run_ids or discover_run_ids(base_dir, adapted_dir)
    if not run_ids:
        raise RuntimeError("No replicate found in common between the three variants and the adapted real-world log.")

    rows: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for run_id in run_ids:
        ref_path = adapted_log_path(adapted_dir, run_id)
        if not ref_path.exists():
            skipped.append({"run_id": run_id, "variant": "real_adaptado", "reason": "merged_log.xes is missing"})
            continue

        reference = load_event_log(ref_path)
        if reference.empty:
            skipped.append({"run_id": run_id, "variant": "real_adaptado", "reason": "empty log after normalisation"})
            continue

        for variant in VARIANTS:
            other_path = variant_log_path(base_dir, run_id, variant)
            if not other_path.exists():
                skipped.append({"run_id": run_id, "variant": variant, "reason": f"path does not exist: {other_path.name}"})
                continue

            other = load_event_log(other_path)
            if other.empty:
                skipped.append({"run_id": run_id, "variant": variant, "reason": "empty log after normalisation"})
                continue

            for item in compute_metrics_for_pair(
                reference, other, include_cfld=args.include_cfld, include_workforce=args.include_workforce
            ):
                rows.append(
                    {
                        "run_id": run_id,
                        "comparison": f"real_adaptado_vs_{variant}",
                        "variant": variant,
                        "metric": item["metric"],
                        "distance": item["distance"],
                        "similarity_1_over_1_plus_d": 1.0 / (1.0 + item["distance"]),
                        "runtime_sec": item["runtime_sec"],
                    }
                )
        print(f"replicate {run_id}: done", flush=True)

    raw_df = pd.DataFrame(rows)
    if raw_df.empty:
        raise RuntimeError("No results were produced. Check the paths and the log formats.")

    raw_df.to_csv(output_dir / "raw_distances.csv", index=False)
    pd.DataFrame(skipped, columns=["run_id", "variant", "reason"]).to_csv(output_dir / "skipped_runs.csv", index=False)
    print(f"Results written to: {output_dir}")
    print(f"Replicates processed: {raw_df['run_id'].nunique()} / {len(run_ids)}")
    print(f"Metrics: {', '.join(sorted(raw_df['metric'].unique().tolist()))}")
    if skipped:
        print(f"Skipped records: {len(skipped)} (see skipped_runs.csv)")


if __name__ == "__main__":
    main()
