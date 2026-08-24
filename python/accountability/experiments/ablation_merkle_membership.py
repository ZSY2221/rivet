from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import protocol as ps
from src import crypto_core as cc

RESULTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "results"
RESULTS_DIR.mkdir(exist_ok=True)

D_TEST = 16
N_TEST = 5


def main():
    setup = ps.setup_round(d_test=D_TEST, n_test=N_TEST, seed="merkle-membership-ablation")

    round_submissions = {}
    leaves = []
    for i, cm in setup.clients.items():
        x_i = ps.sample_bounded_vector(setup.params.d, setup.params.B)
        eps_i, c_i, sig_i, msg = ps.client_commit(setup, cm, x_i, t=1)
        assert ps.verify_signature_and_message(cm, msg, sig_i)
        assert ps.binding_check(setup, cm, eps_i, c_i, self_compute_lhh=True)
        round_submissions[i] = (x_i, c_i, sig_i, msg)
        leaves.append(ps.leaf_bytes(i, c_i, sig_i))

    root_D, levels = cc.build_merkle_tree(leaves)

    cm0 = setup.clients[0]
    x_0_old = ps.sample_bounded_vector(setup.params.d, setup.params.B)
    eps_0_old, c_0_old, sig_0_old, msg_0_old = ps.client_commit(setup, cm0, x_0_old, t=0)
    assert ps.verify_signature_and_message(cm0, msg_0_old, sig_0_old), "The replayed signature should be valid."

    forged_members = list(round_submissions.items()) + [(0, (x_0_old, c_0_old, sig_0_old, msg_0_old))]

    def run_client_side(require_merkle: bool):
        accepted_commitments = []
        accepted_x = []
        all_member_ok = True
        for idx, (i, (x_i, c_i, sig_i, msg)) in enumerate(forged_members):
            cm = setup.clients[i]
            if i in round_submissions and (x_i, c_i, sig_i, msg) == round_submissions[i]:
                proof = ps.cc.merkle_proof(levels, list(round_submissions.keys()).index(i))
            else:
                proof = ps.cc.merkle_proof(levels, 0)
            ok = ps.client_verify_membership(cm, msg, sig_i, c_i, root_D, proof, require_merkle=require_merkle)
            if not ok:
                all_member_ok = False
                continue
            accepted_commitments.append(c_i)
            accepted_x.append(x_i)
        return all_member_ok, accepted_commitments, accepted_x

    ablated_all_ok, ablated_commits, ablated_xs = run_client_side(require_merkle=False)
    if ablated_all_ok:
        G_Z_forged = [0] * setup.params.d
        for x_i in ablated_xs:
            for ell in range(setup.params.d):
                G_Z_forged[ell] += x_i[ell]
        R_forged = sum(setup.clients[i].rho_i for i, _ in forged_members) % cc.R
        eq7_holds_for_forged_set = ps.client_verify_aggregate(setup, G_Z_forged, R_forged, ablated_commits)
    else:
        eq7_holds_for_forged_set = None

    normal_all_ok, normal_commits, _ = run_client_side(require_merkle=True)

    result = {
        "experiment": "merkle_membership_ablation",
        "d_test": D_TEST, "n_honest_this_round": N_TEST,
        "ablation_replay_accepted": ablated_all_ok and eq7_holds_for_forged_set,
        "full_protocol_replay_blocked": not normal_all_ok,
        "full_protocol_accepted_members": len(normal_commits),
    }

    assert ablated_all_ok, "Signature-only membership should accept the replayed submission."
    assert not normal_all_ok, "The locked Merkle root should reject the replayed submission."

    with open(RESULTS_DIR / "ablation_merkle_membership.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Merkle membership ablation passed.")


if __name__ == "__main__":
    main()
