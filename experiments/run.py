"""
Experiment runner. Results are appended to CSV files in results/ as jobs finish,
so you can stop (Ctrl+C) and re-run the same command later: finished jobs are skipped.

  python -m experiments.run --exp seq            # A: sequencing quality (no robots moving)
  python -m experiments.run --exp sim            # B: multi-robot simulation
  python -m experiments.run --exp oneway         # C: one-way vs two-way aisles
  python -m experiments.run --exp all
  add --quick for a small test run (written to results/quick/)
"""
import argparse
import csv
import itertools
import os
import random
import time
import tracemalloc
from multiprocessing import Pool

from core.warehouse import build_warehouse
from core.pathfinding import distance_matrix
from algorithms.tour import tour_cost
from simulation.simulator import SEQUENCERS, SimConfig, run_simulation

ALGOS = ["HeldKarp", "NN", "NN2opt", "GA", "ACO", "ALO", "Hybrid"]
HELD_KARP_MAX = 12          # exact solver only up to this many picks


# ---------------------------------------------------------------- job lists
def seq_jobs(quick):
    seeds = range(3) if quick else range(30)
    sizes = [5, 10] if quick else [5, 8, 10, 12, 20, 30]
    for blocks, one_way, k, seed in itertools.product([1, 2, 3], [True, False], sizes, seeds):
        yield dict(exp="seq", blocks=blocks, one_way=one_way, k=k, seed=seed)


def sim_jobs(quick):
    seeds = range(2) if quick else range(20)
    robots = [1, 5] if quick else [1, 3, 5, 10, 15]
    for width, n, algo, policy, seed in itertools.product([1, 2], robots, ALGOS, ["wait", "replan"], seeds):
        yield dict(exp="sim", width=width, robots=n, algo=algo, policy=policy, seed=seed, one_way=True)


def oneway_jobs(quick):
    seeds = range(2) if quick else range(20)
    robots = [5] if quick else [5, 10, 15]
    for one_way, n, algo, seed in itertools.product([True, False], robots, ["NN2opt", "Hybrid"], seeds):
        yield dict(exp="oneway", width=1, robots=n, algo=algo, policy="wait", seed=seed, one_way=one_way)


def job_id(job):
    return "|".join(f"{k}={job[k]}" for k in sorted(job))


# ---------------------------------------------------------------- workers
def run_seq_job(job):
    """One random order on one layout; every algorithm solves the SAME order."""
    wh = build_warehouse(n_aisles=8, aisle_width=1, aisle_length=8, n_blocks=job["blocks"], one_way=job["one_way"])
    picks = random.Random(f"{job['blocks']}-{job['k']}-{job['seed']}").sample(wh.pick_cells(), job["k"])
    D = distance_matrix(wh, [wh.depot] + picks)
    rows = []
    optimal = None
    for algo in ALGOS:
        if algo == "HeldKarp" and job["k"] > HELD_KARP_MAX:
            continue
        fn = SEQUENCERS[algo]
        t0 = time.perf_counter()
        tour = fn(D, seed=job["seed"])
        ms = (time.perf_counter() - t0) * 1000
        tracemalloc.start()                       # separate run for memory (tracing slows code down)
        fn(D, seed=job["seed"])
        peak_kb = tracemalloc.get_traced_memory()[1] / 1024
        tracemalloc.stop()
        cost = tour_cost(tour, D)
        if algo == "HeldKarp":
            optimal = cost
        rows.append(dict(job=job_id(job), blocks=job["blocks"], one_way=job["one_way"], k=job["k"],
                         seed=job["seed"], algo=algo, cost=cost, optimal=optimal if optimal else "",
                         planning_ms=round(ms, 3), peak_kb=round(peak_kb, 1)))
    return rows


def run_sim_job(job):
    cfg = SimConfig(n_aisles=8, aisle_length=10, aisle_width=job["width"], one_way=job["one_way"],
                    n_robots=job["robots"], orders_per_robot=3, picks_per_order=8,
                    sequencer=job["algo"], policy=job["policy"], seed=job["seed"])
    r = run_simulation(cfg)
    return [dict(job=job_id(job), width=job["width"], one_way=job["one_way"], robots=job["robots"],
                 algo=job["algo"], policy=job["policy"], seed=job["seed"], success=r.success,
                 makespan=r.makespan, distance=r.distance, planned_distance=r.planned_distance,
                 wait_time=r.wait_time, conflicts=r.conflicts, replans=r.replans,
                 deadlocks=r.deadlocks, sidesteps=r.sidesteps, planning_ms=r.planning_ms)]


def run_job(job):
    return run_seq_job(job) if job["exp"] == "seq" else run_sim_job(job)


# ---------------------------------------------------------------- driver
def run_experiment(name, jobs, out_dir, workers):
    path = os.path.join(out_dir, f"{name}.csv")
    done = set()
    if os.path.exists(path):
        with open(path, newline="") as f:
            done = {row["job"] for row in csv.DictReader(f)}
    todo = [j for j in jobs if job_id(j) not in done]
    print(f"[{name}] {len(done)} jobs already done, {len(todo)} to run -> {path}")
    if not todo:
        return

    start = time.time()
    with Pool(workers) as pool, open(path, "a", newline="") as f:
        writer = None
        for i, rows in enumerate(pool.imap_unordered(run_job, todo), 1):
            if writer is None:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                if f.tell() == 0:
                    writer.writeheader()
            writer.writerows(rows)
            f.flush()                                    # saved immediately: safe to stop any time
            if i % 20 == 0 or i == len(todo):
                elapsed = time.time() - start
                eta = elapsed / i * (len(todo) - i)
                print(f"  {i}/{len(todo)} jobs   elapsed {elapsed / 60:5.1f} min   remaining ~{eta / 60:5.1f} min")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", choices=["seq", "sim", "oneway", "all"], default="all")
    ap.add_argument("--quick", action="store_true", help="tiny version to check everything works")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()

    out_dir = os.path.join("results", "quick" if args.quick else "")
    os.makedirs(out_dir, exist_ok=True)
    print(f"Using {args.workers} CPU workers")
    plan = {"seq": seq_jobs, "sim": sim_jobs, "oneway": oneway_jobs}
    for name in (plan if args.exp == "all" else [args.exp]):
        run_experiment(name, list(plan[name](args.quick)), out_dir, args.workers)
    print("All done.")


if __name__ == "__main__":
    main()