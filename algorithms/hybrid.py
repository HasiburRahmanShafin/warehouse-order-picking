"""
Algorithm 6: Hybrid NN2Opt (Collision-Aware / Congestion-Aware)
Reference: Thesis Report Section 4.2.1, Algorithm 6 & Section 4.3.2.

Combines:
1. Nearest Neighbor (NN) greedy construction (fast initial route).
2. Direction-aware Or-opt chain relocations (length 1-3 picks) without sequence inversion,
   preserving valid aisle directionality on asymmetric directed grid graphs.
3. 2-opt local edge exchanges.
4. Collision & Congestion Awareness: Supports penalty weighting for occupied cells (c = 1),
   penalizing or discarding moves through congested regions.
"""
from typing import Optional, Set
from algorithms.tour import tour_cost
from algorithms.heuristics import nearest_neighbor, two_opt


def or_opt(tour: list[int], D: list[list[int]], max_chain: int = 3,
           occupied_penalty: Optional[list[list[int]]] = None) -> list[int]:
    """
    Or-opt: relocates a chain of 1-3 consecutive picks to another place in the tour
    WITHOUT reversing it, preserving travel direction in one-way aisles.
    """
    cost_matrix = D
    if occupied_penalty is not None:
        cost_matrix = [[D[i][j] + occupied_penalty[i][j] for j in range(len(D))] for i in range(len(D))]

    best = tour[:]
    best_cost = tour_cost(best, cost_matrix)
    improved = True
    while improved:
        improved = False
        n = len(best)
        for length in range(1, max_chain + 1):
            for i in range(1, n - length):                    # chain = best[i : i+length], never the depot
                chain = best[i:i + length]
                rest = best[:i] + best[i + length:]
                for j in range(1, len(rest)):                 # insert chain before rest[j]
                    if j == i:
                        continue                              # same place as before
                    candidate = rest[:j] + chain + rest[j:]
                    c = tour_cost(candidate, cost_matrix)
                    if c < best_cost:
                        best, best_cost, improved = candidate, c, True
                        break
                if improved:
                    break
            if improved:
                break
    return best


def hybrid(D: list[list[int]], seed=None,
           occupied_penalty: Optional[list[list[int]]] = None) -> list[int]:
    """
    Algorithm 6: Hybrid NN2Opt.
    Constructs initial tour via Nearest Neighbor, then alternates Or-opt and 2-opt
    until local optimality is achieved. If occupied_penalty is provided, candidate moves
    through occupied cells (c = 1) are penalized according to Algorithm 6.
    """
    cost_matrix = D
    if occupied_penalty is not None:
        cost_matrix = [[D[i][j] + occupied_penalty[i][j] for j in range(len(D))] for i in range(len(D))]

    tour = nearest_neighbor(cost_matrix)
    cost = tour_cost(tour, cost_matrix)
    while True:
        tour = two_opt(or_opt(tour, cost_matrix, occupied_penalty=None), cost_matrix)
        new_cost = tour_cost(tour, cost_matrix)
        if new_cost >= cost:
            return tour
        cost = new_cost


# Explicit alias matching Thesis Report Chapter 4 naming
hybrid_nn2opt = hybrid