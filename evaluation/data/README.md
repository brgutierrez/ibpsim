# `data/` (not distributed)

The event logs of the case study are **not** included in this repository: they are
covered by a confidentiality agreement with the Port of Seville. This folder is the
place where the scripts of `evaluation/` expect them. Everything in it except this
file is ignored by git (see `../.gitignore`).

Expected layout (names are kept from the original experiment):

```
data/
├── logReal.xes                      real-world log (only for generate_adapted_real_log.py)
├── logOro/<r>/*.csv                 Planner-only logs, one CSV per simulated day, r = 1..30
├── logOro/<r>/merged_log.xes        … merged by merge_logs.py
├── logDinamico/<r>/*.csv            Planner + intervention logs
├── logDinamico/<r>/merged_log.xes
├── logEstatico/<r>.csv              Baseline logs generated with Apromore (or <r>.xes)
└── logRealAdaptado/<r>/merged_log.xes   adapted real-world log (generate_adapted_real_log.py)
```

| Folder | Variant in the article | Variant id in the CSV files |
|---|---|---|
| `logEstatico` | Baseline | `estatico` |
| `logOro` | Planner-only | `oro` |
| `logDinamico` | Planner + intervention | `dinamico` |
| `logRealAdaptado` | adapted real-world log (reference) | – |

## File formats

* **Per-day simulator logs** (`logOro`, `logDinamico`): CSV with the columns
  `case_id, activity, time:timestamp:start, time:timestamp:end`.
* **`merged_log.xes`**: XES with one `trace` per case (`concept:name`), and events with
  `concept:name`, `start_timestamp` and `time:timestamp`.
* **Baseline** (`logEstatico/<r>.csv`): CSV exported from Apromore with at least
  `case_id, activity, Start_Time, End_Time` (`resource` is optional).

To run the pipeline on your own logs, arrange them in this layout (30 replicates are
needed for `replication_analysis.py`; the other steps work with at least 3).
