# Warehouse Order Picking with One-Way Aisles and Multi-Robot Congestion

Simulation and benchmarking code for comparing order-sequencing algorithms (Held-Karp, NN, NN+2-opt, GA, ACO, ALO, and a direction-aware Hybrid) in grid warehouses with one-way aisles and multiple robots.

All results except timing and memory are **deterministic**: the same seeds give identical numbers on any machine with the same library versions.

---

## 1. Requirements

- Python **3.10 or newer** (use the same minor version on every machine you compare results across)
- About 200 MB of disk space

---

## 2. Setup (one time per machine)

Open a terminal in the project folder.

**Windows (PowerShell)**
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If activation fails with "running scripts is disabled", run this once, then activate again:
```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Mac / Linux**
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Your terminal prompt should now start with `(.venv)`. Activate the environment every time you open a new terminal.

---

## 3. Check everything works

```
python -m pytest -q
```
Expected: `36 passed` (about 20 seconds).

---

## 4. Project structure & Thesis Algorithm Mapping

This codebase implements and validates the methodology presented in the thesis report:
`T2510622_main_report_without_sign_.pdf`: *"An Algorithmic Method for Warehouse Order Picking with Congestion and One-Way Aisle Constraints"* (Brac University).

| Thesis Report Reference | Implementation File | Description |
|---|---|---|
| **Algorithm 1 (Held-Karp)** | `algorithms/held_karp.py` | Exact Dynamic Programming solver for Asymmetric TSP ($O(2^n \cdot n^2)$), optimal baseline up to 12 picks. |
| **Algorithm 2 (Genetic Algorithm)** | `algorithms/genetic.py` | Order Crossover (OX), swap/inversion mutation, elitism. |
| **Algorithm 3 (Ant Colony Optimization)** | `algorithms/aco.py` | Pheromone trail reinforcement and heuristic desirability on directed warehouse graph. |
| **Algorithm 4 (Ant Lion Optimizer)** | `algorithms/alo.py` | Random-key continuous encoding mapping antlion random walks to valid order permutations. |
| **Algorithm 5 (Nearest Neighbor + 2-Opt)** | `algorithms/heuristics.py` | Greedy nearest-neighbor route construction with 2-opt local edge exchange refinement. |
| **Algorithm 6 (Hybrid NN2Opt Collision-Aware)** | `algorithms/hybrid.py` | Direction-aware hybrid combining NN + Or-opt chain relocations (length 1–3) + 2-opt + collision/occupancy weighting. |
| **Simulation Framework (Sec. 4.2.2 & 4.3)** | `simulation/simulator.py` | Discrete-event SimPy engine with unit cell capacity, conflict logging, wait-for deadlock resolution, and replanning. |
| **Tables 4.1, 5.2, 5.4 & Figures 5.1–5.8** | `experiments/analyze_report.py` | Automated report generator reproducing all thesis summary tables and publication figures. |

```
core/
  warehouse.py        grid layout, racks, one-way aisles, cross-aisles
  pathfinding.py      A*, BFS distances, asymmetric distance matrix
algorithms/
  tour.py             tour cost and validity helpers
  held_karp.py        Algorithm 1: exact optimum (up to 13 picks)
  heuristics.py       Algorithm 5: Nearest Neighbor, 2-opt, NN+2-opt
  genetic.py          Algorithm 2: Genetic Algorithm
  aco.py              Algorithm 3: Ant Colony Optimization
  alo.py              Algorithm 4: Ant Lion Optimizer (random-key encoding)
  hybrid.py           Algorithm 6: Hybrid NN2Opt (direction & collision-aware)
  compare.py          quick side-by-side demo with Table 4.1 metrics
simulation/
  simulator.py        multi-robot SimPy simulator (cell reservation, conflicts, deadlock handling)
  animate.py          renders a simulation run as a GIF
experiments/
  run.py              full experiment runner (parallel, resumable)
  analyze_report.py   reproduces Thesis Tables 4.1, 5.2, 5.4 and Figures 5.1-5.8
  check_same.py       verifies two result files match across machines
tests/                correctness tests for every module
requirements.txt      clean UTF-8 library versions
```

---

## 5. Quick demos & Thesis Reproduction

| Command | What it shows | Time |
|---|---|---|
| `python -m core.warehouse` | Text picture of narrow and wide layouts | instant |
| `python -m core.pathfinding` | A→B and B→A routes differ because of one-way aisles | instant |
| `python -m algorithms.compare` | All 7 algorithms on one order: tour length, gap, time, memory | ~1 s |
| `python -m algorithms.compare --table` | **Reproduces Thesis Table 4.1** for a sample order | ~1 s |
| `python -m experiments.analyze_report` | **Reproduces Thesis Tables 4.1, 5.2, and 5.4** from experiment data | instant |
| `python -m experiments.analyze_report --plots` | **Generates all Thesis Figures 5.1 to 5.8** in `figures/` | ~3 s |
| `python -m simulation.simulator` | Multi-robot traffic table (narrow/wide, 3/5/10 robots, wait/replan) | ~10 s |
| `python -m simulation.animate` | Saves `figures/simulation.gif` | ~40 s |

> **Note on Terminology ("Collisions" vs. "Conflicts"):** In Chapter 5 (Table 5.4, Fig 5.8), the thesis refers to "Collision Count". In the physical SimPy discrete-event model, each cell has `capacity=1`, so physical overlap is prevented. The reported "collision count" corresponds to **traffic conflicts / contention events** where a robot attempts to enter an occupied cell and is forced to wait or replan. `SimResult.collisions` is provided as an explicit alias.


Animation options:
```
python -m simulation.animate --robots 10 --width 2 --policy replan --seconds 200 --out figures/wide10.gif
```
- `--width 1` = narrow aisles, `--width 2` = wide aisles
- `--policy wait` or `--policy replan`
- `--sequencer` any of: `HeldKarp, NN, NN2opt, GA, ACO, ALO, Hybrid`

---

## 6. Running the experiments

| Experiment | Flag | What it measures |
|---|---|---|
| A. Sequencing | `--exp seq` | Route quality vs. the exact optimum, planning time, peak memory. 3 layouts × one-way/two-way × 5–30 picks × 30 seeds |
| B. Simulation | `--exp sim` | Makespan, wait time, conflicts, deadlocks with real robot traffic. Narrow/wide × 1–15 robots × 7 algorithms × wait/replan × 20 seeds |
| C. One-way effect | `--exp oneway` | One-way vs. two-way aisles. NN2opt vs. Hybrid × 5/10/15 robots × 20 seeds |

**Step 1: small test run (1–3 minutes)**
```
python -m experiments.run --quick
```
This writes to `results/quick/`.

**Step 2: full run (roughly 15–45 minutes on a 4–8 core laptop)**
```
python -m experiments.run
```
To run one experiment only:
```
python -m experiments.run --exp seq
python -m experiments.run --exp sim
python -m experiments.run --exp oneway
```
To control the number of CPU cores used:
```
python -m experiments.run --workers 4
```

Results go to `results/seq.csv`, `results/sim.csv`, and `results/oneway.csv`.

**Stopping and resuming.** Each result is saved as soon as it finishes. If the run stops (Ctrl+C, sleep, crash), run the same command again and finished jobs are skipped.

---

## 7. Running on another machine and getting identical results

1. Copy the project folder **without** `.venv`, `results`, `figures`, and `__pycache__`.
2. On the new machine, use the same Python minor version, then do the setup in section 2 and the test in section 3.
3. Run `python -m experiments.run --quick` on **both** machines.
4. Copy one machine's quick CSV next to the other's and compare:
   ```
   python -m experiments.check_same results/quick/sim.csv sim_other.csv
   python -m experiments.check_same results/quick/seq.csv seq_other.csv
   ```
   Both should print `IDENTICAL`. The comparison ignores `planning_ms` and `peak_kb`, which depend on hardware.
5. Run the full experiment(s) you want. Each experiment writes its own CSV, so you can split them across machines and copy the files into `results/` afterwards.

If `check_same` prints `DIFFERENT`, compare `pip freeze` and `python --version` on both machines. ALO is the most sensitive, since it depends on numpy's random number generator.

---

## 8. Result columns

**`seq.csv`** (one row per algorithm per order)

| Column | Meaning |
|---|---|
| `blocks`, `one_way`, `k`, `seed` | Layout blocks, aisle direction rule, picks in the order, instance seed |
| `algo` | Algorithm name |
| `cost` | Tour length in cells (depot → picks → depot) |
| `optimal` | Exact optimum from Held-Karp (empty when `k` > 12) |
| `planning_ms` | Wall-clock time to compute the tour |
| `peak_kb` | Peak memory during planning |

**`sim.csv` and `oneway.csv`** (one row per simulation run)

| Column | Meaning |
|---|---|
| `width`, `one_way`, `robots`, `algo`, `policy`, `seed` | Configuration |
| `success` | All orders finished before the time limit |
| `makespan` | Time when the last robot finished (`inf` if not successful) |
| `distance` / `planned_distance` | Cells actually driven / cells in the planned tours |
| `wait_time` | Total time robots spent blocked |
| `conflicts` | Times a robot found its next cell occupied |
| `replans`, `deadlocks`, `sidesteps` | Rerouting events, detected wait-cycles, side-steps used to break them |
| `planning_ms` | Total sequencing time for all orders in the run |

---

## 9. Model summary

- **Warehouse:** grid of cells. Vertical aisles between racks alternate up/down. Cross-aisles at the top, bottom, and between blocks are two-way. Narrow aisles are 1 lane and wide aisles are 2 lanes.
- **Movement:** each move to a neighbouring cell takes 1 time unit, and each pick takes 2.
- **Traffic:** each cell holds at most one robot (SimPy resource, capacity 1). A robot keeps its current cell until it has entered the next, so physical collisions cannot occur. A **conflict** is counted when the next cell is occupied.
- **Policies:** after waiting 3 time units, `wait` keeps waiting and `replan` routes around occupied cells.
- **Deadlocks:** detected as cycles in the wait-for graph and resolved by side-stepping into a free neighbouring cell.
- **Workload:** each robot completes its orders from its own home cell on the bottom cross-aisle, then leaves the floor. All algorithms receive identical orders for the same seed.

---

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| `No module named 'core'` (or `algorithms`, ...) | Run commands from the project root folder, using `python -m ...` |
| `No module named simpy` | The virtual environment isn't active; activate it (section 2) |
| The full run seems stuck | GA and ALO runs with 15 robots take ~10 s each; check the progress lines |
| Tests fail after editing code | Run `python -m pytest -q` to see which module broke |