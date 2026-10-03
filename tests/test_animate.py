from simulation.animate import position_at

TRAJ = [(0, (1, 0)), (1, (2, 0)), (5, (3, 0))]   # moves at t 0->1, waits 1->4, moves 4->5


def test_robot_slides_between_cells():
    assert position_at(TRAJ, 0.5) == (1.5, 0, True)
    assert position_at(TRAJ, 4.5) == (2.5, 0, True)


def test_robot_standing_still_is_not_moving():
    assert position_at(TRAJ, 2.0) == (2, 0, False)


def test_robot_disappears_after_finishing():
    assert position_at(TRAJ, 10) is None