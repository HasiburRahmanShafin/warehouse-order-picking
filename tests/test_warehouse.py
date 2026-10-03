from collections import deque
from core.warehouse import build_warehouse, UP


def reachable(wh, start, reverse=False):
    """All cells reachable from start (or that can reach start, if reverse=True)."""
    if reverse:
        incoming = {c: [] for c in wh.free_cells()}
        for c in wh.free_cells():
            for n in wh.neighbors(c):
                incoming[n].append(c)
        step = lambda c: incoming[c]
    else:
        step = wh.neighbors
    seen, queue = {start}, deque([start])
    while queue:
        for n in step(queue.popleft()):
            if n not in seen:
                seen.add(n)
                queue.append(n)
    return seen


def test_every_cell_reachable_both_ways():
    # robot must be able to go from depot to any cell AND come back
    for width in (1, 2):
        for blocks in (1, 2):
            for n_aisles in (2, 3, 6):
                wh = build_warehouse(n_aisles=n_aisles, aisle_width=width, n_blocks=blocks)
                free = set(wh.free_cells())
                assert reachable(wh, wh.depot) == free
                assert reachable(wh, wh.depot, reverse=True) == free


def test_one_way_rule_is_enforced():
    wh = build_warehouse(n_aisles=4, aisle_width=1, aisle_length=6)
    x = next(col for col, d in wh.aisle_dir.items() if d == UP)
    middle = (x, 3)
    assert (x, 4) in wh.neighbors(middle)        # going up: allowed
    assert (x, 2) not in wh.neighbors(middle)    # going down: forbidden


def test_two_way_option():
    wh = build_warehouse(n_aisles=4, one_way=False)
    assert wh.aisle_dir == {}
    assert (1, 2) in wh.neighbors((1, 3)) and (1, 4) in wh.neighbors((1, 3))


def test_robots_never_enter_racks():
    wh = build_warehouse()
    for c in wh.free_cells():
        for n in wh.neighbors(c):
            assert n not in wh.blocked


def test_pick_cells_are_next_to_racks():
    wh = build_warehouse(aisle_width=2)
    for (x, y) in wh.pick_cells():
        assert (x - 1, y) in wh.blocked or (x + 1, y) in wh.blocked