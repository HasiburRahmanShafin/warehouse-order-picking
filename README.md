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

## 4. Project structure

```
core/
  warehouse.py        grid layout, racks, one-way aisles, cross-aisles
  pathfinding.py      A*, BFS distances, asymmetric distance matrix
algorithms/
  tour.py             tour cost and validity helpers
  held_karp.py        exact optimum (up to 13 picks)
  heuristics.py       Nearest Neighbor, 2-opt, NN+2-opt
  genetic.py          Genetic Algorithm
  aco.py              Ant Colony Optimization
  alo.py              Ant Lion Optimizer (random-key encoding)
  hybrid.py           NN + Or-opt + 2-opt (direction-aware local search)
  compare.py          quick side-by-side demo
simulation/
  simulator.py        multi-robot SimPy simulator (cell reservation, conflicts, deadlock handling)
  animate.py          renders a simulation run as a GIF
experiments/
  run.py              full experiment runner (parallel, resumable)
  check_same.py       verifies two result files match across machines
tests/                correctness tests for every module
requirements.txt      exact library versions
```

---

## 5. Quick demos

| Command | What it shows | Time |
|---|---|---|
| `python -m core.warehouse` | Text picture of narrow and wide layouts | instant |
| `python -m core.pathfinding` | A→B and B→A routes differ because of one-way aisles | instant |
| `python -m algorithms.compare` | All 7 algorithms on one order: tour length, gap to optimal, time | ~1 s |
| `python -m simulation.simulator` | Multi-robot traffic table (narrow/wide, 3/5/10 robots, wait/replan) | ~10 s |
| `python -m simulation.animate` | Saves `figures/simulation.gif` | ~40 s |

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