"""
Ant Lion Optimizer (ALO, Mirjalili 2015) adapted to order sequencing.

ALO is designed for continuous numbers, not orderings. We use the standard
"random keys" trick: a solution is a list of numbers in [0, 1], one per pick,
and the visiting order is the picks sorted by their number.

Each iteration:
  - every ant random-walks around (a) an antlion chosen by roulette wheel and
    (b) the elite (best) antlion; its new position is the average of the two walks
  - the walk range shrinks over time (exploration early, exploitation late)
  - antlions are replaced by ants that found better tours
"""
import numpy as np

from algorithms.tour import tour_cost


def _keys_to_tour(keys):
    return [0] + [int(i) + 1 for i in np.argsort(keys, kind="stable")] + [0]


def _random_walk(rng, center, lo_off, hi_off, t, T):
    """Position at step t of a normalised random walk around `center` (one value per dimension)."""
    dims = len(center)
    steps = np.where(rng.random((dims, T)) > 0.5, 1.0, -1.0)
    walk = np.concatenate([np.zeros((dims, 1)), np.cumsum(steps, axis=1)], axis=1)
    a, b = walk.min(axis=1), walk.max(axis=1)
    lo, hi = center + lo_off, center + hi_off
    value = walk[:, t]
    return (value - a) * (hi - lo) / np.maximum(b - a, 1e-12) + lo


def alo(D: list[list[int]], seed: int = 0, n_agents: int = 20, iterations: int = 100) -> list[int]:
    rng = np.random.default_rng(seed)
    n = len(D)
    dims = n - 1
    if dims <= 1:
        return [0] + list(range(1, n)) + [0]

    cost = lambda keys: tour_cost(_keys_to_tour(keys), D)
    antlions = rng.random((n_agents, dims))
    antlion_cost = np.array([cost(a) for a in antlions])
    elite = antlions[antlion_cost.argmin()].copy()
    elite_cost = antlion_cost.min()

    for t in range(1, iterations + 1):
        # shrinking ratio from the original paper
        ratio = 1.0
        for frac, w in ((0.95, 6), (0.9, 5), (0.75, 4), (0.5, 3), (0.1, 2)):
            if t > frac * iterations:
                ratio = 10 ** w * t / iterations
                break
        c, d = 0.0 / ratio, 1.0 / ratio            # search space is [0, 1], shrunk by the ratio

        fitness = 1.0 / (antlion_cost + 1e-9)
        probs = fitness / fitness.sum()
        ants = np.empty_like(antlions)
        for i in range(n_agents):
            chosen = antlions[rng.choice(n_agents, p=probs)]
            walks = []
            for center in (chosen, elite):
                lo = c if rng.random() < 0.5 else -c
                hi = d if rng.random() < 0.5 else -d
                walks.append(_random_walk(rng, center, min(lo, hi), max(lo, hi), t, iterations))
            ants[i] = np.clip((walks[0] + walks[1]) / 2, 0.0, 1.0)

        ant_cost = np.array([cost(a) for a in ants])
        everyone = np.vstack([antlions, ants])
        everyone_cost = np.concatenate([antlion_cost, ant_cost])
        keep = np.argsort(everyone_cost, kind="stable")[:n_agents]
        antlions, antlion_cost = everyone[keep], everyone_cost[keep]
        if antlion_cost[0] < elite_cost:
            elite, elite_cost = antlions[0].copy(), antlion_cost[0]

    return _keys_to_tour(elite)