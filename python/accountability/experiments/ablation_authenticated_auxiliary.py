from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import protocol as ps
from src import crypto_core as cc

RESULTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "results"
RESULTS_DIR.mkdir(exist_ok=True)

D_TEST = 24


def main():
    setup = ps.setup_round(d_test=D_TEST, n_test=1, seed="authenticated-auxiliary-ablation")
    cm = setup.clients[0]

    x_benign = [0] * D_TEST
    x_malicious = [setup.params.B * 50] * D_TEST

    eps_submitted = [b - r for b, r in zip(x_benign, cm.r_i)]
    delta_x = [m - b for m, b in zip(x_malicious, x_benign)]
    w_i_tampered = cc.point_add(cm.W_i, setup.H(delta_x))

    c_i_attack = cc.point_add(setup.H(x_malicious), cm.c_i_rho)

    ablated_pass = ps.binding_check(
        setup, cm, eps_submitted, c_i_attack,
        self_compute_lhh=True, w_i_used=w_i_tampered,
    )
    bva_violated = ablated_pass and (x_benign != x_malicious)

    normal_pass = ps.binding_check(
        setup, cm, eps_submitted, c_i_attack,
        self_compute_lhh=True, w_i_used=cm.W_i,
    )

    result = {
        "experiment": "authenticated_auxiliary_ablation",
        "d_test": D_TEST,
        "ablation_attack_succeeded": bva_violated,
        "full_protocol_attack_blocked": not normal_pass,
    }

    assert ablated_pass, "The modified auxiliary point should pass the ablation."
    assert bva_violated, "The ablation should violate the binding relation."
    assert not normal_pass, "The authenticated auxiliary point should reject the input."

    with open(RESULTS_DIR / "ablation_authenticated_auxiliary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Authenticated auxiliary-point ablation passed.")


if __name__ == "__main__":
    main()
