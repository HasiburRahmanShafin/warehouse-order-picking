"""
Ant Colony Optimization (ACO) for order sequencing.

Each iteration, every ant builds a tour step by step. From node i it picks the next
node j with probability proportional to
    pheromone[i][j]^alpha * (1 / distance[i][j])^beta
Short tours then deposit more pheromone, so good edges get chosen more often.
Pheromone is directional (i->j differs from j->i), which fits one-way aisles.
"""
import random

from algorithms.tour import tour_cost


def aco(D: list[list[int]], seed: int = 0, n_ants: int = 20, iterations: int = 100,
        alpha: float = 1.0, beta: float = 3.0, evaporation: float = 0.1) -> list[int]:
    rng = random.Random(seed)
    n = len(D)
    if n <= 2:
        return [0] + list(range(1, n)) + [0]

    eta = [[0.0 if i == j else 1.0 / max(D[i][j], 0.5) for j in range(n)] for i in range(n)]
    tau = [[1.0] * n for _ in range(n)]
    best_tour, best_cost = None, float("inf")

    for _ in range(iterations):
        iter_best, iter_cost = None, float("inf")
        for _ in range(n_ants):
            tour, current = [0], 0
            unvisited = list(range(1, n))
            while unvisited:
                weights = [(tau[current][j] ** alpha) * (eta[current][j] ** beta) for j in unvisited]
                nxt = rng.choices(unvisited, weights=weights)[0]
                tour.append(nxt)
                unvisited.remove(nxt)
                current = nxt
            tour.append(0)
            c = tour_cost(tour, D)
            if c < iter_cost:
                iter_best, iter_cost = tour, c

        if iter_cost < best_cost:
            best_tour, best_cost = iter_best, iter_cost

        # evaporate everywhere, then reinforce the iteration-best and best-so-far tours
        for i in range(n):
            for j in range(n):
                tau[i][j] *= (1 - evaporation)
        for t, c in ((iter_best, iter_cost), (best_tour, best_cost)):
            for k in range(len(t) - 1):
                tau[t[k]][t[k + 1]] += 1.0 / c
    return best_tour