"""Quick comparison on one random order. Run: python -m algorithms.compare"""
import random
import sys
import time

from core.warehouse import build_warehouse
from core.pathfinding import distance_matrix
from algorithms.tour import tour_cost
from algorithms.held_karp import held_karp
from algorithms.heuristics import nearest_neighbor, nn_2opt
from algorithms.genetic import genetic
from algorithms.aco import aco
from algorithms.alo import alo
from algorithms.hybrid import hybrid  

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
wh = build_warehouse(n_aisles=8, aisle_width=1, aisle_length=8, n_blocks=2)
rng = random.Random(SEED)
picks = rng.sample(wh.pick_cells(), 10)
D = distance_matrix(wh, [wh.depot] + picks)

optimal = None
print(f"{'algorithm':<10}{'tour length':>12}{'gap to optimal':>16}{'time (ms)':>11}")
for name, fn in [("HeldKarp", held_karp), ("NN", nearest_neighbor), ("NN2opt", nn_2opt), ("GA", genetic),
                 ("ACO", aco), ("ALO", alo), ("Hybrid", hybrid)]:
    t0 = time.perf_counter()
    tour = fn(D, seed=0)
    ms = (time.perf_counter() - t0) * 1000
    cost = tour_cost(tour, D)
    optimal = optimal or cost
    print(f"{name:<10}{cost:>12}{100 * (cost - optimal) / optimal:>15.1f}%{ms:>11.1f}")