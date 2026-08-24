from __future__ import annotations

import csv
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import protocol as ps
from src import crypto_core as cc

RESULTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "results"
RESULTS_DIR.mkdir(exist_ok=True)

D_TEST = 24
N_TEST = 30
M_MIN = 5
DROPOUT_RATES = [0.0, 0.10, 0.20, 0.30, 0.50]
TRIALS_PER_RATE = 20
LAMBDA_OVERRIDE = 16


def simulate_round(setup, dropout_p: float, rng_seed: int):
    delivered_s1 = {}
    delivered_s2 = {}
    submissions = {}
    rng = random.Random(rng_seed)
    for i, cm in setup.clients.items():
        x_i = ps.sample_bounded_vector(setup.params.d, setup.params.B)
        eps_i, c_i, sig_i, msg = ps.client_commit(setup, cm, x_i, t=1)
        submissions[i] = (x_i, eps_i, c_i, sig_i, msg)
        delivered_s1[i] = rng.random() >= dropout_p
        delivered_s2[i] = rng.random() >= dropout_p

    R_t = []
    for i, cm in setup.clients.items():
        x_i, eps_i, c_i, sig_i, msg = submissions[i]
        bind_ok = ps.verify_signature_and_message(cm, msg, sig_i) and \
            ps.binding_check(setup, cm, eps_i, c_i, self_compute_lhh=True)
        s1_ok = delivered_s1[i] and bind_ok
        s2_ok = delivered_s2[i] and bind_ok
        if s1_ok and s2_ok:
            R_t.append(i)

    return R_t, submissions, delivered_s1, delivered_s2


def main():
    setup = ps.setup_round(d_test=D_TEST, n_test=N_TEST, seed="dropout-robustness", lambda_override=LAMBDA_OVERRIDE)
    rows = []

    rate_summary = []
    for p in DROPOUT_RATES:
        print(f"[dropout] dropout_p={p} ...", flush=True)
        sizes = []
        verify_oks = []
        aborts = 0
        for trial in range(TRIALS_PER_RATE):
            trial_seed = int(round(p * 100)) * 1_000_000 + trial
            R_t, submissions, _, _ = simulate_round(setup, p, rng_seed=trial_seed)
            sizes.append(len(R_t))
            if len(R_t) < M_MIN:
                aborts += 1
                rows.append({"scenario": "dropout_rate_sweep", "dropout_p": p, "trial": trial,
                             "R_t_size": len(R_t), "verify_ok": None, "status": "aborted"})
                continue
            accepted = [(setup.clients[i], submissions[i][0]) for i in R_t]
            commitments = [submissions[i][2] for i in R_t]
            G_Z, R_total = ps.aggregate_honest(setup, accepted)
            ok = ps.client_verify_aggregate(setup, G_Z, R_total, commitments)
            verify_oks.append(ok)
            rows.append({"scenario": "dropout_rate_sweep", "dropout_p": p, "trial": trial,
                         "R_t_size": len(R_t), "verify_ok": ok, "status": "verified"})
        rate_summary.append({
            "dropout_p": p,
            "mean_R_t_size": sum(sizes) / len(sizes),
            "expected_R_t_size_approx": N_TEST * (1 - p) ** 2,
            "abort_count": aborts,
            "verify_all_ok": all(verify_oks) if verify_oks else None,
            "n_verify_trials": len(verify_oks),
        })

    single_side_setup = ps.setup_round(d_test=D_TEST, n_test=6, seed="dropout-single-side",
                                        lambda_override=LAMBDA_OVERRIDE)
    submissions = {}
    for i, cm in single_side_setup.clients.items():
        x_i = ps.sample_bounded_vector(single_side_setup.params.d, single_side_setup.params.B)
        eps_i, c_i, sig_i, msg = ps.client_commit(single_side_setup, cm, x_i, t=1)
        submissions[i] = (x_i, eps_i, c_i, sig_i, msg)

    delivery_plan = {0: (True, True), 1: (True, True), 2: (True, False),
                      3: (False, True), 4: (False, False), 5: (False, False)}
    R_t_manual = []
    for i, (d1, d2) in delivery_plan.items():
        cm = single_side_setup.clients[i]
        x_i, eps_i, c_i, sig_i, msg = submissions[i]
        bind_ok = ps.verify_signature_and_message(cm, msg, sig_i) and \
            ps.binding_check(single_side_setup, cm, eps_i, c_i, self_compute_lhh=True)
        s1_ok = d1 and bind_ok
        s2_ok = d2 and bind_ok
        in_R = s1_ok and s2_ok
        if in_R:
            R_t_manual.append(i)
        rows.append({"scenario": "single_side_dropout", "dropout_p": None, "trial": i,
                     "R_t_size": None, "verify_ok": None,
                     "status": f"client{i}_in_set={in_R}"})

    accepted_manual = [(single_side_setup.clients[i], submissions[i][0]) for i in R_t_manual]
    commitments_manual = [submissions[i][2] for i in R_t_manual]
    G_Z_m, R_m = ps.aggregate_honest(single_side_setup, accepted_manual)
    ok_manual = ps.client_verify_aggregate(single_side_setup, G_Z_m, R_m, commitments_manual)

    expected_R_t = [0, 1]
    single_side_ok = (sorted(R_t_manual) == expected_R_t) and ok_manual

    csv_path = RESULTS_DIR / "dropout_robustness.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario", "dropout_p", "trial", "R_t_size", "verify_ok", "status"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    summary = {
        "d_test": D_TEST, "n_test": N_TEST, "m_min": M_MIN,
        "trials_per_rate": TRIALS_PER_RATE,
        "dropout_rate_sweep": rate_summary,
        "single_side_dropout": {
            "delivery_plan": {str(k): v for k, v in delivery_plan.items()},
            "R_t_actual": sorted(R_t_manual),
            "R_t_expected": expected_R_t,
            "aggregate_verify_ok": ok_manual,
            "matches_theorem7": single_side_ok,
        },
    }
    with open(RESULTS_DIR / "dropout_robustness_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Details: {csv_path}")

    for rs in rate_summary:
        if rs["n_verify_trials"] > 0:
            assert rs["verify_all_ok"], f"Verification failed at dropout_p={rs['dropout_p']}."
    assert single_side_ok, "The single-server dropout case did not match the expected set."
    print("Dropout robustness checks passed.")


if __name__ == "__main__":
    main()
