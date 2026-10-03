import random
from itertools import permutations

from core.warehouse import build_warehouse
from core.pathfinding import distance_matrix
from algorithms.tour import tour_cost, is_valid_tour
from algorithms.held_karp import held_karp
from algorithms.heuristics import nearest_neighbor, two_opt, nn_2opt
from algorithms.genetic import genetic
from algorithms.aco import aco
from algorithms.alo import alo

ALL = [held_karp, nearest_neighbor, nn_2opt, genetic, aco, alo]


def random_asymmetric(n, seed):
    rng = random.Random(seed)
    return [[0 if i == j else rng.randint(1, 50) for j in range(n)] for i in range(n)]


def brute_force(D):
    n = len(D)
    return min(tour_cost([0, *p, 0], D) for p in permutations(range(1, n)))


def warehouse_instance(k, seed):
    wh = build_warehouse()
    picks = random.Random(seed).sample(wh.pick_cells(), k)
    return distance_matrix(wh, [wh.depot] + picks)


def test_held_karp_is_optimal_on_asymmetric():
    for seed in range(20):
        for n in (2, 3, 5, 8):
            D = random_asymmetric(n, seed)
            assert tour_cost(held_karp(D), D) == brute_force(D)


def test_held_karp_is_optimal_on_warehouse():
    for seed in range(10):
        D = warehouse_instance(7, seed)
        assert tour_cost(held_karp(D), D) == brute_force(D)


def test_every_algorithm_returns_valid_tour():
    for seed in range(5):
        for n in (2, 3, 4, 9):
            D = random_asymmetric(n, seed)
            for algo in ALL:
                assert is_valid_tour(algo(D, seed=seed), n), algo.__name__


def test_heuristics_never_beat_optimal():
    for seed in range(10):
        D = warehouse_instance(9, seed)
        best = tour_cost(held_karp(D), D)
        for algo in ALL:
            assert tour_cost(algo(D, seed=seed), D) >= best


def test_two_opt_never_makes_tour_worse():
    for seed in range(10):
        D = random_asymmetric(12, seed)
        nn = nearest_neighbor(D)
        assert tour_cost(two_opt(nn, D), D) <= tour_cost(nn, D)


def test_ga_is_reproducible():
    D = warehouse_instance(12, 3)
    assert genetic(D, seed=5) == genetic(D, seed=5)


def test_metaheuristics_are_reproducible():
    D = warehouse_instance(10, 4)
    for algo in (aco, alo):
        assert algo(D, seed=1) == algo(D, seed=1)


def test_ga_and_aco_solve_small_orders_optimally():
    for seed in range(5):
        D = warehouse_instance(5, seed)
        best = tour_cost(held_karp(D), D)
        for algo in (genetic, aco):
            assert tour_cost(algo(D, seed=seed), D) == best, algo.__name__