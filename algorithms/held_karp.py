"""
Held-Karp: exact dynamic programming. Always finds the optimal tour.
Cost grows like n^2 * 2^n, so only usable for small orders (about 12 picks or fewer).
Works for asymmetric distances (one-way aisles).
"""
from algorithms.tour import tour_cost

MAX_PICKS = 13


def held_karp(D: list[list[int]], seed=None) -> list[int]:
    n = len(D)
    m = n - 1                      # number of picks (nodes 1..n-1)
    if m == 0:
        return [0, 0]
    if m > MAX_PICKS:
        raise ValueError(f"Held-Karp limited to {MAX_PICKS} picks (got {m}); it would take too long.")

    INF = float("inf")
    full = 1 << m
    # dp[mask][j]: cheapest way to leave the depot, visit exactly the picks in mask, and stand on pick j
    dp = [[INF] * m for _ in range(full)]
    parent = [[-1] * m for _ in range(full)]
    for j in range(m):
        dp[1 << j][j] = D[0][j + 1]

    for mask in range(1, full):
        for j in range(m):
            cost_here = dp[mask][j]
            if cost_here == INF or not (mask >> j) & 1:
                continue
            for k in range(m):
                if (mask >> k) & 1:
                    continue
                new_mask = mask | (1 << k)
                new_cost = cost_here + D[j + 1][k + 1]
                if new_cost < dp[new_mask][k]:
                    dp[new_mask][k] = new_cost
                    parent[new_mask][k] = j

    # close the tour: return to depot
    last = min(range(m), key=lambda j: dp[full - 1][j] + D[j + 1][0])

    # walk back through parents to rebuild the order
    order, mask, j = [], full - 1, last
    while j != -1:
        order.append(j + 1)
        prev = parent[mask][j]
        mask ^= 1 << j
        j = prev
    tour = [0] + order[::-1] + [0]
    assert tour_cost(tour, D) == min(dp[full - 1][j] + D[j + 1][0] for j in range(m))
    return tour