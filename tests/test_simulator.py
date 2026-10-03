import pytest
from simulation.simulator import SimConfig, Simulation, run_simulation


def test_single_robot_has_no_traffic():
    cfg = SimConfig(n_robots=1, orders_per_robot=2, picks_per_order=6, seed=3)
    r = run_simulation(cfg)
    assert r.success
    assert r.conflicts == 0 and r.wait_time == 0 and r.deadlocks == 0
    assert r.distance == r.planned_distance                     # drove exactly the planned tours
    assert r.makespan == r.distance + cfg.pick_time * 2 * 6     # 1 time unit per cell + picking


@pytest.mark.parametrize("width", [1, 2])
@pytest.mark.parametrize("policy", ["wait", "replan"])
def test_multi_robot_runs_finish_and_obey_rules(width, policy):
    for seed in range(4):
        sim = Simulation(SimConfig(aisle_width=width, n_robots=6, policy=policy, seed=seed,
                                   orders_per_robot=2, picks_per_order=6))
        r = sim.run()            # an internal check raises an error if two robots ever share a cell
        assert r.success
        assert r.distance >= r.planned_distance                 # traffic can only add distance
        for traj in r.trajectories.values():
            for (_, a), (_, b) in zip(traj, traj[1:]):
                assert b in sim.wh.neighbors(a)                 # every move is legal (one-way rules)


def test_same_seed_same_result():
    cfg = SimConfig(n_robots=8, policy="replan", seed=11)
    a, b = run_simulation(cfg), run_simulation(cfg)
    assert (a.makespan, a.distance, a.conflicts, a.wait_time) == (b.makespan, b.distance, b.conflicts, b.wait_time)


def test_every_algorithm_gets_the_same_orders():
    s1 = Simulation(SimConfig(sequencer="NN2opt", seed=5))
    s2 = Simulation(SimConfig(sequencer="GA", seed=5))
    assert s1.orders == s2.orders