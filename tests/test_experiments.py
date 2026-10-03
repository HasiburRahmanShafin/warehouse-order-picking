from experiments.run import run_seq_job, run_sim_job, job_id, seq_jobs, sim_jobs


def test_sequencing_job_gives_every_algorithm_the_same_order():
    rows = run_seq_job(dict(exp="seq", blocks=2, one_way=True, k=6, seed=1))
    assert [r["algo"] for r in rows] == ["HeldKarp", "NN", "NN2opt", "GA", "ACO", "ALO", "Hybrid"]
    optimal = rows[0]["cost"]
    assert all(r["cost"] >= optimal and r["optimal"] == optimal for r in rows)


def test_held_karp_skipped_for_large_orders():
    rows = run_seq_job(dict(exp="seq", blocks=1, one_way=True, k=15, seed=0))
    assert "HeldKarp" not in [r["algo"] for r in rows]


def test_sim_job_returns_one_row():
    rows = run_sim_job(dict(exp="sim", width=1, robots=2, algo="Hybrid", policy="wait", seed=0, one_way=True))
    assert len(rows) == 1 and rows[0]["success"]


def test_job_ids_are_unique():
    for jobs in (list(seq_jobs(False)), list(sim_jobs(False))):
        assert len({job_id(j) for j in jobs}) == len(jobs)