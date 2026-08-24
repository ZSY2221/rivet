from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import protocol as ps

RESULTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "results"
RESULTS_DIR.mkdir(exist_ok=True)

D_TEST = 24


def main():
    setup = ps.setup_round(d_test=D_TEST, n_test=1, seed="hash-recompute-ablation")
    cm = setup.clients[0]

    x_benign = [0] * D_TEST
    x_malicious = [setup.params.B * 50] * D_TEST

    eps_submitted = [b - r for b, r in zip(x_benign, cm.r_i)]
    eps_for_malicious = [m - r for m, r in zip(x_malicious, cm.r_i)]
    H_eps_reported = setup.H(eps_for_malicious)

    c_i_attack = ps.cc.point_add(setup.H(x_malicious), cm.c_i_rho)

    ablated_pass = ps.binding_check(
        setup, cm, eps_submitted, c_i_attack,
        self_compute_lhh=False, reported_H_eps=H_eps_reported,
    )
    bva_violated = ablated_pass and (x_benign != x_malicious)

    normal_pass = ps.binding_check(
        setup, cm, eps_submitted, c_i_attack,
        self_compute_lhh=True,
    )

    result = {
        "experiment": "hash_recompute_ablation",
        "d_test": D_TEST,
        "ablation_attack_succeeded": bva_violated,
        "full_protocol_attack_blocked": not normal_pass,
    }

    assert ablated_pass, "The reported-hash ablation should pass."
    assert bva_violated, "The ablation should produce different screened and committed vectors."
    assert not normal_pass, "Recomputing the hash should reject the input."

    with open(RESULTS_DIR / "ablation_hash_recompute.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Hash recomputation ablation passed.")


if __name__ == "__main__":
    main()
