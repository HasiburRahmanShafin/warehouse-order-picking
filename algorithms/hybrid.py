"""
Hybrid sequencer: Nearest Neighbor + direction-aware local search.

Why: with one-way aisles the distance matrix is asymmetric. 2-opt improves a tour
by REVERSING a segment, and driving a segment backwards through one-way aisles is
usually much longer, so 2-opt gets stuck early (we measured this in Step 5).

Or-opt fixes this: it MOVES a short chain of 1-3 consecutive picks to another place
in the tour WITHOUT reversing it, so the direction of travel inside the chain is kept.
We alternate Or-opt and 2-opt until neither can improve the tour.
"""
from algorithms.tour import tour_cost
from algorithms.heuristics import nearest_neighbor, two_opt


def or_opt(tour: list[int], D: list[list[int]], max_chain: int = 3) -> list[int]:
    best = tour[:]
    best_cost = tour_cost(best, D)
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
                    c = tour_cost(candidate, D)
                    if c < best_cost:
                        best, best_cost, improved = candidate, c, True
                        break
                if improved:
                    break
            if improved:
                break
    return best


def hybrid(D: list[list[int]], seed=None) -> list[int]:
    tour = nearest_neighbor(D)
    cost = tour_cost(tour, D)
    while True:
        tour = two_opt(or_opt(tour, D), D)
        new_cost = tour_cost(tour, D)
        if new_cost >= cost:
            return tour
        cost = new_cost