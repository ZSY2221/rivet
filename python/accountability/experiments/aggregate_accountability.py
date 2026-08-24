from __future__ import annotations

import csv
import json
import pathlib
import secrets
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import protocol as ps
from src import crypto_core as cc

RESULTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "results"
RESULTS_DIR.mkdir(exist_ok=True)

D_TEST = 24
N_TEST = 10
TRIALS_PER_FORGE_SCENARIO = 100


def run_honest_round(setup):
    accepted = []
    commitments = []
    for i, cm in setup.clients.items():
        x_i = ps.sample_bounded_vector(setup.params.d, setup.params.B)
        eps_i, c_i, sig_i, msg = ps.client_commit(setup, cm, x_i, t=1)
        assert ps.verify_signature_and_message(cm, msg, sig_i)
        assert ps.binding_check(setup, cm, eps_i, c_i, self_compute_lhh=True)
        accepted.append((cm, x_i))
        commitments.append(c_i)
    G_Z, R_total = ps.aggregate_honest(setup, accepted)
    return accepted, commitments, G_Z, R_total


def random_delta_vector(d: int, magnitude: int = 10) -> list[int]:
    return [secrets.randbelow(2 * magnitude + 1) - magnitude for _ in range(d)]


def main():
    rows = []
    setup = ps.setup_round(d_test=D_TEST, n_test=N_TEST, seed="aggregate-accountability")

    accepted, commitments, G_Z, R_total = run_honest_round(setup)
    honest_ok = ps.client_verify_aggregate(setup, G_Z, R_total, commitments)
    rows.append({"scenario": "honest_baseline", "trial": 0, "accepted": honest_ok,
                 "expected_accept": True})
    assert honest_ok, "The honest baseline should pass."

    forge_G_count_accept = 0
    for trial in range(TRIALS_PER_FORGE_SCENARIO):
        delta = random_delta_vector(setup.params.d, magnitude=1 + trial % 50)
        if all(v == 0 for v in delta):
            delta[0] = 1
        G_forged = [g + dlt for g, dlt in zip(G_Z, delta)]
        ok = ps.client_verify_aggregate(setup, G_forged, R_total, commitments)
        forge_G_count_accept += int(ok)
        rows.append({"scenario": "forge_G_only", "trial": trial, "accepted": ok,
                     "expected_accept": False})

    forge_R_count_accept = 0
    for trial in range(TRIALS_PER_FORGE_SCENARIO):
        delta0 = secrets.randbelow(cc.R - 1) + 1
        R_forged = (R_total + delta0) % cc.R
        ok = ps.client_verify_aggregate(setup, G_Z, R_forged, commitments)
        forge_R_count_accept += int(ok)
        rows.append({"scenario": "forge_R_only", "trial": trial, "accepted": ok,
                     "expected_accept": False})

    forge_both_count_accept = 0
    for trial in range(TRIALS_PER_FORGE_SCENARIO):
        delta = random_delta_vector(setup.params.d, magnitude=1 + trial % 50)
        delta0 = secrets.randbelow(cc.R)
        if all(v == 0 for v in delta) and delta0 == 0:
            delta0 = 1
        G_forged = [g + dlt for g, dlt in zip(G_Z, delta)]
        R_forged = (R_total + delta0) % cc.R
        ok = ps.client_verify_aggregate(setup, G_forged, R_forged, commitments)
        forge_both_count_accept += int(ok)
        rows.append({"scenario": "forge_both", "trial": trial, "accepted": ok,
                     "expected_accept": False})

    csv_path = RESULTS_DIR / "aggregate_accountability.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario", "trial", "accepted", "expected_accept"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    summary = {
        "d_test": D_TEST,
        "n_test": N_TEST,
        "trials_per_forge_scenario": TRIALS_PER_FORGE_SCENARIO,
        "honest_baseline_accepted": honest_ok,
        "forge_G_only_false_accept_rate": forge_G_count_accept / TRIALS_PER_FORGE_SCENARIO,
        "forge_R_only_false_accept_rate": forge_R_count_accept / TRIALS_PER_FORGE_SCENARIO,
        "forge_both_false_accept_rate": forge_both_count_accept / TRIALS_PER_FORGE_SCENARIO,
    }
    with open(RESULTS_DIR / "aggregate_accountability_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Details: {csv_path}")

    assert forge_G_count_accept == 0, "A forged aggregate vector was accepted."
    assert forge_R_count_accept == 0, "A forged aggregate blinding value was accepted."
    assert forge_both_count_accept == 0, "A jointly forged aggregate was accepted."
    print("Accountability checks passed.")


if __name__ == "__main__":
    main()
