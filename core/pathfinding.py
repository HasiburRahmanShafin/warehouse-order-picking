"""
Shortest paths on the one-way warehouse grid.

Every move costs 1 (one cell). Because aisles are one-way, the distance
from A to B is often NOT the same as from B to A.
"""
import heapq
from collections import deque

from core.warehouse import Warehouse, Cell


def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(wh: Warehouse, start: Cell, goal: Cell, avoid: set[Cell] | None = None) -> list[Cell] | None:
    """
    Shortest legal path from start to goal, including both ends.
    avoid: extra cells to treat as blocked (e.g. cells occupied by other robots).
    Returns None if no path exists.
    """
    avoid = avoid or set()
    if start == goal:
        return [start]
    # heap items: (f = g + h, tie-breaker, g, cell)
    counter = 0
    open_heap = [(manhattan(start, goal), counter, 0, start)]
    came_from: dict[Cell, Cell] = {}
    best_g = {start: 0}

    while open_heap:
        _, _, g, cell = heapq.heappop(open_heap)
        if cell == goal:
            path = [cell]
            while cell != start:
                cell = came_from[cell]
                path.append(cell)
            return path[::-1]
        if g > best_g[cell]:
            continue                      # stale heap entry, skip
        for nxt in wh.neighbors(cell):
            if nxt in avoid and nxt != goal:
                continue
            new_g = g + 1
            if new_g < best_g.get(nxt, float("inf")):
                best_g[nxt] = new_g
                came_from[nxt] = cell
                counter += 1
                heapq.heappush(open_heap, (new_g + manhattan(nxt, goal), counter, new_g, nxt))
    return None


def distances_from(wh: Warehouse, start: Cell) -> dict[Cell, int]:
    """Distance from start to EVERY reachable cell (breadth-first search)."""
    dist = {start: 0}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for nxt in wh.neighbors(cell):
            if nxt not in dist:
                dist[nxt] = dist[cell] + 1
                queue.append(nxt)
    return dist


def distance_matrix(wh: Warehouse, points: list[Cell]) -> list[list[int]]:
    """
    D[i][j] = shortest distance from points[i] to points[j].
    Not symmetric when aisles are one-way. One search per point (fast).
    """
    matrix = []
    for p in points:
        d = distances_from(wh, p)
        matrix.append([d[q] for q in points])
    return matrix


def render_path(wh: Warehouse, path: list[Cell]) -> str:
    """Warehouse picture with the path drawn as '*'."""
    rows = [list(line) for line in wh.render().split("\n")]
    for (x, y) in path[1:-1]:
        rows[wh.height - 1 - y][x] = "*"
    sx, sy = path[0]
    gx, gy = path[-1]
    rows[wh.height - 1 - sy][sx] = "S"
    rows[wh.height - 1 - gy][gx] = "G"
    return "\n".join("".join(r) for r in rows)


if __name__ == "__main__":
    from core.warehouse import build_warehouse

    wh = build_warehouse(n_aisles=4, aisle_width=1, aisle_length=6)
    a, b = (4, 3), (1, 5)   # a is in a DOWN aisle, b is in an UP aisle

    p_ab = astar(wh, a, b)
    p_ba = astar(wh, b, a)
    print(f"A -> B: {len(p_ab) - 1} steps")
    print(render_path(wh, p_ab))
    print(f"\nB -> A: {len(p_ba) - 1} steps   (different! one-way aisles)")
    print(render_path(wh, p_ba))