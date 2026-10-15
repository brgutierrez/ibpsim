# Reproducing the evaluation of I-BPSim

This folder contains the scripts used for the evaluation reported in Section 5 of the
article *"I-BPSim: Enabling Interventions in Business Process Simulation"*: the
construction of the adapted real-world log, the distance metrics, the statistical
analysis, Table 1, Supplementary Table S1, Figure 2 and the analysis of the number of
replicates.

**About the data.** The event logs of the Port of Seville case study are confidential
(confidentiality agreement with the Port) and **cannot be shared**. For this reason the
repository provides (i) all the scripts, (ii) the per-replicate distance values
(`results/raw_distances.csv`), from which every number of the statistical analysis can be
reproduced, and (iii) a synthetic example to exercise the whole pipeline.

## What can be reproduced

| Level | What | Needs | Available to reviewers |
|---|---|---|---|
| 1 | Statistics, Table 1, Table S1, Figure 2, analysis of the number of replicates | `results/raw_distances.csv` | **Yes** |
| 2 | Distance metrics (`raw_distances.csv`) from the logs | the 120 logs (3 variants × 30 replicates + 30 reference logs) | No (confidential) |
| 3 | Adapted real-world log and simulated logs | real-world log; simulator input data | No (confidential) |
| – | Smoke test of the whole pipeline | `example/` (synthetic) | **Yes** |

## Pipeline

| Step | Script | Input | Output | Article |
|---|---|---|---|---|
| 1 | `merge_logs.py` | per-day CSV logs of a variant | `<r>/merged_log.xes` | – |
| 2 | `generate_adapted_real_log.py` | real log + Planner-only logs | `logRealAdaptado/`, `generation_report.csv` | Sect. 5.1.2 |
| 3 | `compute_distances.py` | simulated logs + adapted real log | `raw_distances.csv` | Sect. 5.2 |
| 4 | `compute_statistics.py` | `raw_distances.csv` | `summary_statistics.csv`, `global_tests.csv`, `paired_tests.csv` | Sect. 5.3 |
| 5 | `build_tables.py` | outputs of step 4 | `table1_mean_sd.*`, `tableS1_pairwise_tests.*` | Table 1, Table S1 |
| 6 | `make_figure.py` | `raw_distances.csv` | `experimental_results_plots.pdf` | Figure 2 |
| 7 | `replication_analysis.py` | `raw_distances.csv` | printed summary, `resampling_results.csv` | Sect. 5.3 (number of replicates) |
| – | `check_activity_vocabulary.py` | logs | printed diagnostic | Sect. 5.4–5.5 (bigram/trigram) |

Supporting modules: `distance_metrics.py` (the distance measures) and `stats_utils.py`
(Holm–Bonferroni, rank-biserial correlation, paired statistics).

## Installation

```bash
cd evaluation
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Quick start

### Level 1 – reproduce the statistics from the distances (no confidential data)

```bash
python compute_statistics.py --raw-csv results/raw_distances.csv --output-dir out
python build_tables.py       --stats-dir out
python make_figure.py        results/raw_distances.csv out/experimental_results_plots.pdf
python replication_analysis.py --raw results/raw_distances.csv --subsets 300 --seed 1
```

The files in `results/` are the outputs obtained with these commands; `out/` should match
them (up to floating-point noise in the last digits).

### Smoke test with synthetic data

```bash
python example/make_synthetic_example.py
python compute_distances.py  --data-dir example/data --output-dir example/results
python compute_statistics.py --raw-csv example/results/raw_distances.csv --output-dir example/results
python build_tables.py       --stats-dir example/results
```

The synthetic data have nothing to do with the case study (5 replicates of random logs);
the output only shows that the pipeline runs end to end.

### Level 2 / 3 – with the actual logs (authors / data owners)

```bash
python merge_logs.py data/logOro
python merge_logs.py data/logDinamico
python generate_adapted_real_log.py --real-log data/logReal.xes \
       --planner-only-dir data/logOro --output-dir data/logRealAdaptado   # window_systematic, seed 2021
python compute_distances.py --data-dir data --output-dir results
python compute_statistics.py --raw-csv results/raw_distances.csv --output-dir results
python build_tables.py --stats-dir results
python make_figure.py results/raw_distances.csv results/experimental_results_plots.pdf
python replication_analysis.py --raw results/raw_distances.csv --out results/resampling_results.csv
```

See `data/README.md` for the expected layout and file formats.

## How the logs were generated

* **Planner-only** and **Planner + intervention** logs are produced by the simulator in
  `business_process_simulator_interventions/` (the first 20 vessel calls, 30 independent
  runs). The Planner + intervention runs use the intervention configuration in
  `business_process_simulator_interventions/config/` (`run_batch_simulations.py`); the
  Planner-only runs use the same procedure without interventions.
* The **Baseline** logs were generated with [Apromore](https://apromore.com) from the same
  discovered process model and resource/duration distributions.
* The simulator is **not seeded** (`random.seed(time.time())`): a new execution produces
  logs that are statistically equivalent, but not identical, to those analysed in the
  article. The construction of the adapted real-world log **is** seeded
  (`--seed 2021`), so the same inputs give exactly the same reference logs.

## Notes on the experimental design (see Sections 5.1 and 5.3 of the article)

* The reference window of replicate *r* starts at the *r*-th of 30 equally spaced points
  (about 13 days apart) and is as long as the simulated log of that replicate
  (18–35 days); consecutive windows therefore partially overlap
  (`results/generation_report.csv`).
* The window of replicate 1 contains only 6 cases, so its sample of 20 is completed with
  repeated cases. `replication_analysis.py` includes a robustness check without that replicate.
* `bigram` and `trigram` are constant (1.0) for the three variants, because the activity
  vocabularies of the simulated and the real logs are almost disjoint
  (`check_activity_vocabulary.py`); they are reported but excluded from the post-hoc tests.
* For the case-arrival metrics the Planner-only and Planner + intervention values are
  identical by construction, so that comparison is not tested; the Holm–Bonferroni
  correction is applied to the remaining 25 post-hoc tests.

## Reference

The distance measures implement the framework of D. Chapela-Campa, I. Benchekroun,
O. Baron, M. Dumas, D. Krass and A. Senderovich, *A framework for measuring the quality of
business process simulation models*, Information Systems 127 (2025) 102447,
<https://doi.org/10.1016/j.is.2024.102447>.
