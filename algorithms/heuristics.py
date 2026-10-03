"""
Fast heuristics: Nearest Neighbor (NN) and 2-opt improvement.

Note on one-way aisles: a 2-opt move REVERSES a segment of the tour, which changes
the direction of travel on every edge inside it. With asymmetric distances we must
therefore re-cost the whole candidate tour, not just the two swapped edges.
"""
from algorithms.tour import tour_cost


def nearest_neighbor(D: list[list[int]], seed=None) -> list[int]:
    n = len(D)
    unvisited = set(range(1, n))
    tour, current = [0], 0
    while unvisited:
        nxt = min(unvisited, key=lambda j: (D[current][j], j))   # (distance, index) = deterministic ties
        tour.append(nxt)
        unvisited.remove(nxt)
        current = nxt
    return tour + [0]


def two_opt(tour: list[int], D: list[list[int]]) -> list[int]:
    """Keep reversing segments while it shortens the tour (best-improvement)."""
    best = tour[:]
    best_cost = tour_cost(best, D)
    n = len(best)
    while True:
        best_move = None
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                c = tour_cost(candidate, D)
                if c < best_cost:
                    best_cost, best_move = c, candidate
        if best_move is None:
            return best
        best = best_move


def nn_2opt(D: list[list[int]], seed=None) -> list[int]:
    return two_opt(nearest_neighbor(D), D)