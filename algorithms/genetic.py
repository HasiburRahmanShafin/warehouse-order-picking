"""
Genetic Algorithm (GA) for order sequencing.

Each individual is an ordering of the picks (depot excluded). Each generation:
keep the best few (elitism) -> pick parents by tournament -> order crossover (OX)
-> mutation (swap or segment inversion).
"""
import random

from algorithms.tour import tour_cost


def _cost(order, D):
    return tour_cost([0] + order + [0], D)


def _order_crossover(p1, p2, rng):
    n = len(p1)
    a, b = sorted(rng.sample(range(n), 2))
    child = [None] * n
    child[a:b + 1] = p1[a:b + 1]
    taken = set(child[a:b + 1])
    fill = iter(g for g in p2 if g not in taken)
    return [g if g is not None else next(fill) for g in child]


def _mutate(order, rng):
    a, b = sorted(rng.sample(range(len(order)), 2))
    if rng.random() < 0.5:
        order[a], order[b] = order[b], order[a]            # swap two picks
    else:
        order[a:b + 1] = order[a:b + 1][::-1]               # reverse a segment


def genetic(D: list[list[int]], seed: int = 0, pop_size: int = 60, generations: int = 200,
            crossover_rate: float = 0.9, mutation_rate: float = 0.2, elite: int = 2,
            tournament: int = 3) -> list[int]:
    rng = random.Random(seed)              # own random generator -> reproducible
    picks = list(range(1, len(D)))
    if len(picks) < 3:                     # too small for GA operators: try all orders
        from itertools import permutations
        best = min(permutations(picks), key=lambda o: _cost(list(o), D))
        return [0] + list(best) + [0]

    population = []
    for _ in range(pop_size):
        ind = picks[:]
        rng.shuffle(ind)
        population.append(ind)

    for _ in range(generations):
        population.sort(key=lambda o: _cost(o, D))
        next_gen = [ind[:] for ind in population[:elite]]          # elitism: copies, never lose the best
        while len(next_gen) < pop_size:
            p1 = min(rng.sample(population, tournament), key=lambda o: _cost(o, D))
            p2 = min(rng.sample(population, tournament), key=lambda o: _cost(o, D))
            child = _order_crossover(p1, p2, rng) if rng.random() < crossover_rate else p1[:]
            if rng.random() < mutation_rate:
                _mutate(child, rng)
            next_gen.append(child)
        population = next_gen

    best = min(population, key=lambda o: _cost(o, D))
    return [0] + best + [0]