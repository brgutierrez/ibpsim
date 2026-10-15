# I-BPSim: Enabling Interventions in Business Process Simulation

I-BPSim is a business process simulator that allows **interventions** (changes to resource
capacities, activity durations and gateway branching probabilities, plus an external
planning agent) to be applied *while a simulation is running*, so that "what-if" scenarios can
be studied on top of a process model discovered from an event log. It is built on
[SimPy](https://simpy.readthedocs.io) and [PM4Py](https://pm4py.fit.fraunhofer.de), and was
evaluated on a real-world case study: the vessel arrival/departure process of the
**Port of Seville**.

This repository accompanies the article:

> **"I-BPSim: Enabling Interventions in Business Process Simulation"** (under review).

## Contents

```
.
├── business_process_simulator_interventions/   # the simulator (Python package)
│   ├── main.py                    # interactive entry point (GUI to define interventions)
│   ├── run_batch_simulations.py   # headless batch runs, interventions read from CSV files
│   ├── config/                    # intervention definitions used in the case study (CSV)
│   ├── data/                      # model/log readers (process model, durations, resources, gateways)
│   ├── interventions/             # intervention types + external planning agent
│   ├── simulation/                # SimPy-based simulation engine
│   └── gui/                       # PyQt6 dialog to configure interventions
├── evaluation/                    # scripts to reproduce the evaluation (Section 5 of the article)
├── requirements.txt
└── .env.example                   # template of the input-data configuration
```

## Data availability (please read)

The case study uses event logs, process models and operational data of the Port of Seville.
They are **confidential** (non-disclosure agreement with the Port) and are **not included**
in this repository. Consequently:

| What | Needs the confidential data? | Where |
|---|---|---|
| Run the simulator on your own process | No (bring your own model/data, see [Input data](#input-data)) | this README |
| Reproduce the statistics, tables and figure of the evaluation | **No** (uses the per-replicate distance values we release) | [`evaluation/`](evaluation/README.md) |
| Run the evaluation pipeline end to end on a toy example | **No** (synthetic data) | [`evaluation/example/`](evaluation/README.md) |
| Regenerate the simulated logs / distances of the case study | Yes | — |

The reviewer-oriented instructions are in [`evaluation/README.md`](evaluation/README.md).

## Requirements

* Python **3.10 – 3.12** (developed and tested with 3.11).
* The dependencies in `requirements.txt` (SimPy, PM4Py, pandas, NumPy, SciPy, `mip`, PyQt6, …).
* A desktop environment for the interactive GUI (`main.py`). The batch runner does not need it.
* `mip` (CBC solver) is used by the external planning agent.

## Installation

```bash
git clone https://github.com/brgutierrez/ibpsim.git
cd ibpsim

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Input data

The simulator reads its inputs from the paths defined in a `.env` file. Create it from the
template and point each variable to your files:

```bash
cp .env.example .env
```

| Variable | Meaning |
|---|---|
| `VESSELS_DATA` | CSV with the vessel calls (arrivals/departures) to simulate |
| `PROCESS_MODEL`, `PROCESS_MODEL_DEPARTURES` | BPMN models for arrivals / departures |
| `ACTIVITIES_DURATION`, `ACTIVITIES_DURATION_DEPARTURES` | CSV with the duration distribution of each activity |
| `ACTIVITIES_RESOURCES`, `ACTIVITIES_RESOURCES_DEPARTURES` | CSV with the resource required by each activity (`RESOURCE` column) and its capacity |
| `ACTIVITIES_GATEWAYS_PERCENTAGES`, `ACTIVITIES_GATEWAYS_PERCENTAGES_DEPARTURE` | CSV with the branching probabilities of each gateway |
| `WAITING_ACTIVITY`, `WAITING_ACTIVITY_DEPARTURE` | Name of the activity at which a case waits for the planner's slot (`ACTA` / `ACTB` in the case study) |

The default paths in `.env.example` are relative to the package folder
(`business_process_simulator_interventions/`), so a `data/` folder placed at the repository
root is picked up automatically. `data/` and `.env` are git-ignored.

> The process models, duration/resource/gateway tables and the vessel data are exactly the
> files that cannot be released for the Port of Seville. To use I-BPSim on another process,
> provide the same set of files built from your own event log (e.g. discovered with
> Apromore, PM4Py or any other tool that exports BPMN).
>
> The external planning agent additionally loads a precomputed bathymetry/depth array
> (`.npy`, see `interventions/external_agent/planner.py`). This file is derived from the
> Port's data, so it is not distributed either; it is excluded from the repository (`*.npy` is
> git-ignored).

## Usage

All commands are run from the simulator folder, so that the relative paths of `.env` resolve:

```bash
cd business_process_simulator_interventions
export PYTHONPATH=..               # Windows (PowerShell): $env:PYTHONPATH=".."
```

### 1. Interactive mode (GUI)

```bash
python main.py
```

A dialog opens in which you define the interventions and the date from which each one takes
effect:

* **Resources** – change the capacity of a resource type (e.g. pilots from 8 to 4).
* **Activities** – change the duration of an activity.
* **Gateways** – change the probability of the branches of an exclusive gateway.

After confirming, the simulation runs and the event logs are written to `./results/`
(one CSV per simulated day). The planner is invoked at each planning date to schedule the
vessels.

### 2. Batch mode (no GUI, interventions from CSV files)

`run_batch_simulations.py` runs `NUM_SIMULATIONS` (30 by default) independent replicates with
the same intervention scenario, which is read from three CSV files in `config/`:

| File | Columns |
|---|---|
| `config/resources_interventions.csv` | `resource_name, initial, modified, change_time` |
| `config/activities_interventions.csv` | `activity_name, new_duration, change_time` |
| `config/percentages_interventions.csv` | `gateway_id, branch_name, percentage, change_time` |

Empty `modified` / `new_duration` / `percentage` cells mean "no intervention"; `change_time`
is the simulation time (in minutes) at which the change takes effect. The activation dates are
set at the bottom of the script (`*_INTERVENTION_DATE`). The files in `config/` are the ones
used for the *Planner + intervention* variant of the case study (pilots reduced from 8 to 4
and a change of the branching probabilities of one gateway).

```bash
python run_batch_simulations.py
```

Each replicate is written to `./caseStudy/logDinamico/<replicate number>/`.

> **Note.** The simulator is stochastic and is seeded from the system clock
> (`random.seed(time.time())`), so independent runs produce different logs. The evaluation
> in the article is therefore reproduced from the released *distance values*, not by
> re-simulating (see [`evaluation/`](evaluation/README.md)).

## The three variants evaluated in the article

| Variant | Description | How it is obtained |
|---|---|---|
| **Baseline** | Process model simulated without a planner and without interventions | Apromore simulation of the discovered model |
| **Planner-only** | I-BPSim with the external planning agent, no interventions | I-BPSim, empty intervention files |
| **Planner + intervention** | I-BPSim with the planner and the interventions of `config/` | `run_batch_simulations.py` |

Their distance to a window of the real-world log is measured with the framework of
Chapela-Campa *et al.* (*Information Systems* 127, 2025), and compared statistically. All of
this is in [`evaluation/`](evaluation/README.md).

## Reproducing the evaluation

```bash
cd evaluation
pip install -r requirements.txt
python compute_statistics.py --raw-csv results/raw_distances.csv --output-dir out
python build_tables.py --stats-dir out
python make_figure.py results/raw_distances.csv out/experimental_results_plots.pdf
python replication_analysis.py --raw results/raw_distances.csv --subsets 300 --seed 1
```

This regenerates Table 1, Supplementary Table S1, Figure 2 and the analysis of the number of
replicates of the article, from the released `results/raw_distances.csv`. Details,
including what can and cannot be reproduced without the confidential logs, are in
[`evaluation/README.md`](evaluation/README.md).

## Tests

A smoke test for the intervention configuration loader (reads the CSV files in `config/`) is provided:

```bash
cd business_process_simulator_interventions
PYTHONPATH=.. python test_interventions_config.py
```

## Citation

If you use I-BPSim in your work, please credit the authors and cite the article above. The
full reference will be added here once the article is published.

## License

I-BPSim is released under the [Apache License 2.0](LICENSE). You are free to use, modify and
redistribute it, provided that you keep the copyright and license notices (see `NOTICE`) and
state any changes you make. If you use I-BPSim in your work, please also credit the authors
and cite the article above.

This license covers the code only. The data of the Port of Seville are confidential and are
not part of this repository.

## Funding

This work has been supported by the grants **KOSMOS-US** (PID2024-155363OB-C42), funded by
MICIU/AEI/10.13039/501100011033 and by the "European Union NextGenerationEU/PRTR", and
**LUNA** (DGP_PIDI_2024_01728), funded by "Junta de Andalucía: Consejería de Universidad,
Investigación e Innovación".

## Contact

Belén Ramos-Gutiérrez — Universidad de Sevilla, Departamento de Lenguajes y Sistemas
Informáticos — <brgutierrez@us.es>
