import random

from core.warehouse import build_warehouse
from core.pathfinding import distance_matrix
from algorithms.tour import tour_cost, is_valid_tour
from algorithms.held_karp import held_karp
from algorithms.heuristics import nearest_neighbor, nn_2opt
from algorithms.hybrid import hybrid, or_opt
from simulation.simulator import SimConfig, run_simulation


def one_way_instance(seed, k=10):
    wh = build_warehouse(n_aisles=8, aisle_length=8, n_blocks=2)
    picks = random.Random(seed).sample(wh.pick_cells(), k)
    return distance_matrix(wh, [wh.depot] + picks)


def test_or_opt_keeps_tour_valid_and_never_worse():
    for seed in range(10):
        D = one_way_instance(seed)
        nn = nearest_neighbor(D)
        improved = or_opt(nn, D)
        assert is_valid_tour(improved, len(D))
        assert tour_cost(improved, D) <= tour_cost(nn, D)


def test_hybrid_valid_and_between_optimal_and_nn():
    for seed in range(10):
        D = one_way_instance(seed)
        t = hybrid(D)
        assert is_valid_tour(t, len(D))
        assert tour_cost(held_karp(D), D) <= tour_cost(t, D) <= tour_cost(nearest_neighbor(D), D)


def test_hybrid_beats_nn2opt_on_one_way_layouts_on_average():
    gap = lambda algo, D: tour_cost(algo(D), D) / tour_cost(held_karp(D), D) - 1
    seeds = range(15)
    hybrid_gap = sum(gap(hybrid, one_way_instance(s)) for s in seeds) / len(seeds)
    nn2opt_gap = sum(gap(nn_2opt, one_way_instance(s)) for s in seeds) / len(seeds)
    assert hybrid_gap < nn2opt_gap


def test_hybrid_runs_in_simulator():
    r = run_simulation(SimConfig(sequencer="Hybrid", n_robots=4, orders_per_robot=2, seed=2))
    assert r.success