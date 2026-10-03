import random
from core.warehouse import build_warehouse
from core.pathfinding import astar, distances_from, distance_matrix


def is_legal(wh, path):
    return all(path[i + 1] in wh.neighbors(path[i]) for i in range(len(path) - 1))


def test_astar_is_legal_and_shortest():
    rng = random.Random(0)
    for width in (1, 2):
        wh = build_warehouse(aisle_width=width)
        cells = wh.free_cells()
        for _ in range(200):
            a, b = rng.choice(cells), rng.choice(cells)
            path = astar(wh, a, b)
            assert path[0] == a and path[-1] == b
            assert is_legal(wh, path)                                  # obeys one-way rules
            assert len(path) - 1 == distances_from(wh, a)[b]           # truly shortest


def test_one_way_makes_distances_asymmetric():
    wh = build_warehouse()
    D = distance_matrix(wh, wh.pick_cells()[:30])
    assert any(D[i][j] != D[j][i] for i in range(30) for j in range(30))


def test_two_way_distances_are_symmetric():
    wh = build_warehouse(one_way=False)
    pts = wh.pick_cells()[:30]
    D = distance_matrix(wh, pts)
    assert all(D[i][j] == D[j][i] for i in range(30) for j in range(30))


def test_avoid_cells_forces_detour_or_none():
    wh = build_warehouse(n_aisles=4, aisle_width=1, aisle_length=6)
    a, b = (1, 1), (1, 5)                       # same UP aisle, straight line
    direct = astar(wh, a, b)
    assert len(direct) - 1 == 4
    assert astar(wh, a, b, avoid={(1, 3)}) is None   # single-lane aisle blocked: no way through


def test_path_to_self():
    wh = build_warehouse()
    assert astar(wh, wh.depot, wh.depot) == [wh.depot]