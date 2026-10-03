"""
Multi-robot order-picking simulator (SimPy, discrete-event).

Rules
-----
* Every free cell is a SimPy Resource with capacity 1: at most one robot per cell.
* A robot always holds the cell it stands on. To move, it requests the next cell,
  holds BOTH cells while moving (1 time unit), then releases the old one.
  -> two robots can never occupy the same cell (physical collision is impossible).
* If the next cell is taken, that is a CONFLICT. The robot waits up to `patience`
  time units. If still blocked, it reacts according to the routing policy:
    - "wait"   : keep waiting on the same path
    - "replan" : compute a new path that avoids cells occupied right now
* DEADLOCK: robots waiting on each other in a cycle (A waits for B, B waits for A).
  It is detected with a wait-for graph and resolved by the robot side-stepping
  into a random free neighbouring cell.
* Each robot starts at its own home cell on the bottom cross-aisle, completes its
  orders (home -> picks -> home), then leaves the floor (e.g. to charge).
"""
import random
import time
from dataclasses import dataclass, field

import simpy

from core.warehouse import build_warehouse, Warehouse, Cell
from core.pathfinding import astar, distance_matrix
from algorithms.held_karp import held_karp
from algorithms.heuristics import nearest_neighbor, nn_2opt
from algorithms.genetic import genetic
from algorithms.aco import aco
from algorithms.alo import alo
from algorithms.hybrid import hybrid

SEQUENCERS = {"HeldKarp": held_karp, "NN": nearest_neighbor, "NN2opt": nn_2opt,
"GA": genetic, "ACO": aco, "ALO": alo, "Hybrid": hybrid}


@dataclass
class SimConfig:
    # layout
    n_aisles: int = 6
    aisle_width: int = 1          # 1 = narrow, 2 = wide
    aisle_length: int = 10
    n_blocks: int = 1
    one_way: bool = True
    # workload
    n_robots: int = 5
    orders_per_robot: int = 3
    picks_per_order: int = 8
    # behaviour
    sequencer: str = "NN2opt"
    policy: str = "wait"          # "wait" or "replan"
    patience: float = 3.0         # time units blocked before reacting
    pick_time: float = 2.0        # time units spent at each pick
    max_time: float = 5000.0      # safety limit: run counts as failed if not finished
    seed: int = 0


@dataclass
class SimResult:
    success: bool                 # all orders finished before max_time
    makespan: float               # time when the last robot finished
    distance: int                 # total cells moved by all robots
    planned_distance: int         # total length of planned tours (no traffic)
    wait_time: float              # total time robots spent blocked
    conflicts: int                # times a robot found its next cell taken
    replans: int
    deadlocks: int
    sidesteps: int
    planning_ms: float            # total wall-clock time spent sequencing orders
    trajectories: dict = field(default_factory=dict, repr=False)   # robot -> [(time, cell)]

    # --- Properties aligning with Thesis Report terminology (Chapter 4 & 5, Tables 4.1, 5.1, 5.4) ---
    @property
    def collisions(self) -> int:
        """Alias for conflicts, matching Thesis Report Table 5.4 ('Collision Count') and Figure 5.8."""
        return self.conflicts

    @property
    def replan_count(self) -> int:
        """Alias for replans, matching Thesis Report Table 4.1 & Table 5.1 ('Replan Count')."""
        return self.replans

    @property
    def congestion_delay(self) -> float:
        """Alias for wait_time, matching Thesis Report Table 5.1 ('Congestion delay')."""
        return self.wait_time



class Simulation:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        self.wh: Warehouse = build_warehouse(cfg.n_aisles, cfg.aisle_width, cfg.aisle_length,
                                             cfg.n_blocks, cfg.one_way)
        self.env = simpy.Environment()
        self.cells = {c: simpy.Resource(self.env, capacity=1) for c in self.wh.free_cells()}
        self.occupant: dict[Cell, int] = {}          # cell -> robot id standing there
        self.waiting_on: dict[int, Cell] = {}        # robot id -> cell it is waiting for
        self.sequence = SEQUENCERS[cfg.sequencer]
        self.stats = dict(distance=0, planned=0, wait=0.0, conflicts=0, replans=0,
                          deadlocks=0, sidesteps=0, planning_ms=0.0)
        self.finish_times: list[float] = []
        self.trajectories: dict[int, list] = {}

        # homes spread along the bottom cross-aisle (avoid the dead-end corners)
        row = [(x, 0) for x in range(1, self.wh.width - 1)]
        if cfg.n_robots > len(row):
            raise ValueError(f"At most {len(row)} robots fit on this layout.")
        self.homes = [row[i * len(row) // cfg.n_robots] for i in range(cfg.n_robots)]

        # all orders are drawn up front from the seed -> identical workload for every algorithm
        picks = self.wh.pick_cells()
        self.orders = [[self.rng.sample(picks, cfg.picks_per_order) for _ in range(cfg.orders_per_robot)]
                       for _ in range(cfg.n_robots)]

    # ---------- occupancy bookkeeping ----------
    def _occupy(self, cell, rid):
        assert cell not in self.occupant, f"two robots in {cell}!"   # must never happen
        self.occupant[cell] = rid

    def _leave(self, cell, rid):
        assert self.occupant.get(cell) == rid
        del self.occupant[cell]

    def _in_deadlock(self, rid) -> bool:
        """
        Follow 'waits for' links from rid: rid waits for B, B waits for C, ...
        If the chain loops (back to rid, or into any cycle further ahead), nobody in it
        can ever move by waiting alone, so rid is stuck in a deadlock.
        """
        seen, current = {rid}, rid
        while current in self.waiting_on:
            blocker = self.occupant.get(self.waiting_on[current])
            if blocker is None:
                return False          # the cell is free (or about to be): not a deadlock
            if blocker in seen:
                return True
            seen.add(blocker)
            current = blocker
        return False                  # chain ends at a robot that is moving/picking: just wait

    # ---------- robot behaviour ----------
    def robot(self, rid):
        cfg, env = self.cfg, self.env
        home = self.homes[rid]
        cur = home
        hold = self.cells[cur].request()
        yield hold
        self._occupy(cur, rid)
        traj = self.trajectories[rid] = [(env.now, cur)]

        for order in self.orders[rid]:
            # plan the visiting order (wall-clock time is measured, sim time is not affected)
            nodes = [home] + order
            D = distance_matrix(self.wh, nodes)
            t0 = time.perf_counter()
            tour = self.sequence(D, seed=cfg.seed)
            self.stats["planning_ms"] += (time.perf_counter() - t0) * 1000
            self.stats["planned"] += sum(D[tour[k]][tour[k + 1]] for k in range(len(tour) - 1))
            targets = [nodes[i] for i in tour[1:]]       # picks in order, then home

            for target in targets:
                path = astar(self.wh, cur, target)[1:]
                blocked = False                          # already counted a conflict for this step?
                while cur != target:
                    nxt = path[0]
                    req = self.cells[nxt].request()
                    if not req.triggered and not blocked:
                        self.stats["conflicts"] += 1
                    t_start = env.now
                    self.waiting_on[rid] = nxt
                    yield req | env.timeout(cfg.patience)
                    self.stats["wait"] += env.now - t_start

                    if req.triggered:                    # got the cell (even if at the same instant as the timeout): move
                        del self.waiting_on[rid]
                        self._occupy(nxt, rid)
                        yield env.timeout(1)
                        self.cells[cur].release(hold)
                        self._leave(cur, rid)
                        hold, cur = req, nxt
                        path.pop(0)
                        blocked = False
                        self.stats["distance"] += 1
                        traj.append((env.now, cur))
                        continue

                    # still blocked after `patience`: withdraw the request
                    req.cancel()
                    blocked = True
                    deadlock = self._in_deadlock(rid)    # check BEFORE we stop "waiting"
                    del self.waiting_on[rid]
                    if deadlock:
                        self.stats["deadlocks"] += 1
                    if cfg.policy == "replan" or deadlock:
                        new_path = astar(self.wh, cur, target, avoid=set(self.occupant))
                        if new_path and len(new_path) > 1 and new_path[1] not in self.occupant:
                            path = new_path[1:]
                            self.stats["replans"] += 1
                            continue
                    if deadlock:                         # no way around: step aside
                        free = [n for n in self.wh.neighbors(cur) if n not in self.occupant]
                        if free:
                            step = self.rng.choice(free)
                            path = [step] + astar(self.wh, step, target)[1:]
                            self.stats["sidesteps"] += 1
                        else:
                            yield env.timeout(self.rng.uniform(0.5, 2.0))   # random back-off

                if target != home:
                    yield env.timeout(cfg.pick_time)     # picking the item

        # all orders done: leave the floor
        self.cells[cur].release(hold)
        self._leave(cur, rid)
        self.finish_times.append(env.now)

    def run(self) -> SimResult:
        for rid in range(self.cfg.n_robots):
            self.env.process(self.robot(rid))
        self.env.run(until=self.cfg.max_time)
        s = self.stats
        success = len(self.finish_times) == self.cfg.n_robots
        return SimResult(success=success,
                         makespan=max(self.finish_times) if success else float("inf"),
                         distance=s["distance"], planned_distance=s["planned"],
                         wait_time=round(s["wait"], 2), conflicts=s["conflicts"],
                         replans=s["replans"], deadlocks=s["deadlocks"], sidesteps=s["sidesteps"],
                         planning_ms=round(s["planning_ms"], 2), trajectories=self.trajectories)


def run_simulation(cfg: SimConfig) -> SimResult:
    return Simulation(cfg).run()


if __name__ == "__main__":
    print(f"{'aisles':<8}{'robots':>7}{'policy':>8}{'ok':>5}{'makespan':>10}{'wait':>8}"
          f"{'conflicts':>11}{'deadlocks':>11}{'replans':>9}")
    for width, label in ((1, "narrow"), (2, "wide")):
        for n in (3, 5, 10):
            for policy in ("wait", "replan"):
                r = run_simulation(SimConfig(aisle_width=width, n_robots=n, policy=policy, seed=1))
                print(f"{label:<8}{n:>7}{policy:>8}{'yes' if r.success else 'NO':>5}{r.makespan:>10.0f}"
                      f"{r.wait_time:>8.0f}{r.conflicts:>11}{r.deadlocks:>11}{r.replans:>9}")