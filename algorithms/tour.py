"""
Shared helpers for order sequencing.

A "tour" is a list of node indices that starts AND ends at the depot (node 0):
    [0, 3, 1, 2, 0]  -> depot -> pick 3 -> pick 1 -> pick 2 -> depot
D[i][j] is the travel distance from node i to node j (may differ from D[j][i]).
"""


def tour_cost(tour: list[int], D: list[list[int]]) -> int:
    return sum(D[tour[k]][tour[k + 1]] for k in range(len(tour) - 1))


def is_valid_tour(tour: list[int], n: int) -> bool:
    """Starts and ends at 0 and visits every other node exactly once."""
    return tour[0] == 0 and tour[-1] == 0 and sorted(tour[1:-1]) == list(range(1, n))