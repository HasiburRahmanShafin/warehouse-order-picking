"""
Animate a simulation run and save it as a GIF.

Run:  python -m simulation.animate
      python -m simulation.animate --robots 10 --width 2 --policy replan --seconds 200
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")                     # draw to files, no window needed
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np

from simulation.simulator import SimConfig, Simulation

COLORS = ["#378ADD", "#D85A30", "#1D9E75", "#7F77DD", "#D4537E", "#BA7517",
          "#639922", "#185FA5", "#993556", "#0F6E56", "#854F0B", "#534AB7",
          "#993C1D", "#3B6D11", "#72243E"]


def position_at(traj, t):
    """
    Where a robot is at time t, from its trajectory [(arrival_time, cell), ...].
    Each move takes 1 time unit and ends at the arrival time, so we slide smoothly
    between cells. Returns (x, y, moving) or None if the robot has left the floor.
    """
    if t > traj[-1][0] + 0.5:
        return None
    for k in range(1, len(traj)):
        arrive, cell = traj[k]
        if t < arrive:
            prev = traj[k - 1][1]
            frac = t - (arrive - 1)                         # the move started at arrive - 1
            if frac < 0:                                    # move hasn't started: standing still
                return prev[0], prev[1], False
            return prev[0] + (cell[0] - prev[0]) * frac, prev[1] + (cell[1] - prev[1]) * frac, True
    last = traj[-1][1]
    return last[0], last[1], False


def animate(sim: Simulation, out_path: str, t_end: float, dt: float = 0.5, fps: int = 20):
    wh = sim.wh
    trajs = sim.trajectories
    picks_of = {rid: {c for order in sim.orders[rid] for c in order} for rid in trajs}

    # background: racks dark, floor light
    grid = np.zeros((wh.height, wh.width))
    for (x, y) in wh.blocked:
        grid[y, x] = 1
    fig, ax = plt.subplots(figsize=(wh.width * 0.42, wh.height * 0.42 + 0.6), dpi=90)
    ax.imshow(grid, origin="lower", cmap="Greys", vmin=-0.15, vmax=1.6,
              extent=(-0.5, wh.width - 0.5, -0.5, wh.height - 0.5))
    for x, d in wh.aisle_dir.items():
        for y in range(wh.height):
            if (x, y) not in wh.blocked and y not in wh.cross_rows:
                ax.text(x, y, "↑" if d > 0 else "↓", ha="center", va="center", fontsize=8, color="#B4B2A9")
    ax.set_xticks([]); ax.set_yticks([])

    rids = sorted(trajs)
    dots = ax.scatter([0] * len(rids), [0] * len(rids), s=170, c=[COLORS[i % len(COLORS)] for i in rids],
                      edgecolors="none", zorder=3)
    labels = [ax.text(0, 0, str(i + 1), ha="center", va="center", fontsize=7, color="white",
                      fontweight="bold", zorder=4) for i in rids]
    title = ax.set_title("", fontsize=10)

    def update(frame):
        t = frame * dt
        xs, ys, edges, waiting = [], [], [], 0
        for i, rid in enumerate(rids):
            p = position_at(trajs[rid], t)
            if p is None:                                   # finished: hide off-screen
                xs.append(-10); ys.append(-10); edges.append("none")
                labels[i].set_position((-10, -10))
                continue
            x, y, moving = p
            stopped_at = (round(x), round(y))
            is_waiting = (not moving) and stopped_at not in picks_of[rid] and t > 0
            waiting += is_waiting
            xs.append(x); ys.append(y)
            edges.append("black" if is_waiting else "none")
            labels[i].set_position((x, y))
        dots.set_offsets(np.c_[xs, ys])
        dots.set_edgecolors(edges)
        dots.set_linewidths(3)
        title.set_text(f"t = {t:5.1f}   |   robots waiting: {waiting}   (black ring = blocked)")
        return [dots, title, *labels]

    ax.set_xlim(-0.5, wh.width - 0.5)
    ax.set_ylim(-0.5, wh.height - 0.5)
    fig.tight_layout()
    frames = int(t_end / dt) + 1
    anim = FuncAnimation(fig, update, frames=frames, blit=False)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    anim.save(out_path, writer=PillowWriter(fps=fps))
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--robots", type=int, default=8)
    ap.add_argument("--width", type=int, default=1, help="1 = narrow aisles, 2 = wide aisles")
    ap.add_argument("--policy", default="replan", choices=["wait", "replan"])
    ap.add_argument("--sequencer", default="NN2opt")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=120, help="how much simulated time to animate")
    ap.add_argument("--out", default="figures/simulation.gif")
    args = ap.parse_args()

    cfg = SimConfig(n_robots=args.robots, aisle_width=args.width, policy=args.policy,
                    sequencer=args.sequencer, seed=args.seed)
    sim = Simulation(cfg)
    result = sim.run()
    print(f"success={result.success}  makespan={result.makespan:.0f}  conflicts={result.conflicts}  "
          f"deadlocks={result.deadlocks}")
    print(f"Rendering {args.seconds:.0f} time units to {args.out} ... (takes ~30 s)")
    animate(sim, args.out, t_end=min(args.seconds, result.makespan))
    print("Saved", args.out)


if __name__ == "__main__":
    main()