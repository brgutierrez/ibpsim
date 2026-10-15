"""
make_synthetic_example.py
=========================
Creates a small SYNTHETIC data set with the same directory layout and file
formats as the real experiment, so that the whole pipeline can be exercised
without the (confidential) data of the case study:

    example/data/logOro/<r>/merged_log.xes
    example/data/logDinamico/<r>/merged_log.xes
    example/data/logEstatico/<r>.csv
    example/data/logRealAdaptado/<r>/merged_log.xes

Everything is random (fixed seed) and has nothing to do with the Port of Seville:
the activities are called A..F and the numbers are meaningless. The statistics
computed on it only demonstrate that the scripts run end to end.

Usage:  python example/make_synthetic_example.py            (from the evaluation/ directory)
"""
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "data"
N_REPLICATES = 5
N_CASES = 12
ACTIVITIES = ["A", "B", "C", "D", "E", "F"]
START = pd.Timestamp("2021-01-02 05:00:00")


def make_log(rng: np.random.Generator, arrival_scale: float, duration_scale: float) -> pd.DataFrame:
    rows = []
    t_arrival = START
    for case in range(N_CASES):
        t_arrival = t_arrival + pd.Timedelta(hours=float(rng.exponential(arrival_scale)))
        t = t_arrival
        for act in ACTIVITIES:
            dur = pd.Timedelta(hours=float(rng.exponential(duration_scale)) + 0.5)
            rows.append({"case_id": str(case), "activity": act, "start_time": t, "end_time": t + dur})
            t = t + dur
    return pd.DataFrame(rows)


def write_xes(df: pd.DataFrame, path: Path) -> None:
    root = ET.Element("log", {"xes.version": "1.0", "xmlns": "http://www.xes-standard.org/"})
    for case_id, events in df.groupby("case_id", sort=False):
        trace = ET.SubElement(root, "trace")
        ET.SubElement(trace, "string", {"key": "concept:name", "value": str(case_id)})
        for _, ev in events.iterrows():
            e = ET.SubElement(trace, "event")
            ET.SubElement(e, "string", {"key": "concept:name", "value": ev["activity"]})
            ET.SubElement(e, "date", {"key": "start_timestamp", "value": ev["start_time"].strftime("%Y-%m-%dT%H:%M:%S")})
            ET.SubElement(e, "date", {"key": "time:timestamp", "value": ev["end_time"].strftime("%Y-%m-%dT%H:%M:%S")})
    path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="unicode", xml_declaration=True)


def main() -> None:
    rng = np.random.default_rng(2021)
    for r in range(1, N_REPLICATES + 1):
        write_xes(make_log(rng, arrival_scale=30.0, duration_scale=10.0), OUT / "logRealAdaptado" / str(r) / "merged_log.xes")
        write_xes(make_log(rng, arrival_scale=30.0, duration_scale=10.0), OUT / "logOro" / str(r) / "merged_log.xes")
        write_xes(make_log(rng, arrival_scale=30.0, duration_scale=11.0), OUT / "logDinamico" / str(r) / "merged_log.xes")
        base = make_log(rng, arrival_scale=18.0, duration_scale=22.0)
        (OUT / "logEstatico").mkdir(parents=True, exist_ok=True)
        base.rename(columns={"start_time": "Start_Time", "end_time": "End_Time"}).to_csv(OUT / "logEstatico" / f"{r}.csv", index=False)
    print(f"Synthetic data written to {OUT}")


if __name__ == "__main__":
    main()
