from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from . import crypto_core as cc
from .params import ExperimentParams


@dataclass
class ClientMaterial:
    client_id: int
    sk: object
    pk: object
    r_i: list[int]
    rho_i: int
    rho_i_r: int
    c_i_r: object
    W_i: object
    c_i_rho: object


@dataclass
class Setup:
    params: ExperimentParams
    generators: list
    g0: object
    clients: dict = field(default_factory=dict)

    def H(self, x):
        return cc.H_Z(x, self.generators)


def setup_round(d_test: int = 32, n_test: int = 20, seed: str = "rivet-accountability-v1",
                 lambda_override: int | None = None) -> Setup:
    params = ExperimentParams(d_test=d_test, n_test=n_test, seed=seed, lambda_override=lambda_override)
    assert params.no_wraparound_ok(cc.R), "The test parameters do not satisfy the no-wraparound condition."

    all_gens = cc.gen_generators(seed, params.d)
    g0, gens = all_gens[0], all_gens[1:]

    setup = Setup(params=params, generators=gens, g0=g0)
    for i in range(n_test):
        sk = cc.gen_signing_key()
        pk = sk.public_key()
        r_i = [secrets.randbelow(2 * params.M + 1) - params.M for _ in range(params.d)]
        rho_i = secrets.randbelow(cc.R)
        rho_i_r = secrets.randbelow(cc.R)
        c_i_r = cc.pedersen_commit(r_i, gens, rho_i_r, g0)
        W_i = cc.scalar_mul(g0, rho_i - rho_i_r)
        c_i_rho = cc.scalar_mul(g0, rho_i)
        setup.clients[i] = ClientMaterial(
            client_id=i, sk=sk, pk=pk, r_i=r_i, rho_i=rho_i, rho_i_r=rho_i_r,
            c_i_r=c_i_r, W_i=W_i, c_i_rho=c_i_rho,
        )
    return setup


def sample_bounded_vector(d: int, B: int) -> list[int]:
    return [secrets.randbelow(2 * B + 1) - B for _ in range(d)]


def client_commit(setup: Setup, cm: ClientMaterial, x_i: list[int], t: int = 1):
    eps_i = [xv - rv for xv, rv in zip(x_i, cm.r_i)]
    c_i = cc.point_add(setup.H(x_i), cm.c_i_rho)
    msg = t.to_bytes(8, "big") + cm.client_id.to_bytes(8, "big") + cc.point_to_bytes(c_i)
    sig_i = cc.sign(cm.sk, msg)
    return eps_i, c_i, sig_i, msg


def binding_check(
    setup: Setup,
    cm: ClientMaterial,
    eps_i_submitted: list[int],
    c_i: object,
    self_compute_lhh: bool = True,
    reported_H_eps: object | None = None,
    w_i_used: object | None = None,
) -> bool:
    if self_compute_lhh:
        H_eps = setup.H(eps_i_submitted)
    else:
        assert reported_H_eps is not None, "reported_H_eps is required when self_compute_lhh=False."
        H_eps = reported_H_eps
    w_i = w_i_used if w_i_used is not None else cm.W_i
    rhs = cc.point_add(cc.point_add(cm.c_i_r, H_eps), w_i)
    return cc.point_eq(c_i, rhs)


def verify_signature_and_message(cm: ClientMaterial, msg: bytes, sig_i: bytes) -> bool:
    return cc.verify_sig(cm.pk, msg, sig_i)


def aggregate_honest(setup: Setup, accepted: list[tuple[ClientMaterial, list[int]]]):
    d = setup.params.d
    G_Z = [0] * d
    R_total = 0
    for cm, x_i in accepted:
        for ell in range(d):
            G_Z[ell] += x_i[ell]
        R_total += cm.rho_i
    R_total %= cc.R
    return G_Z, R_total


def leaf_bytes(client_id: int, c_i: object, sig_i: bytes) -> bytes:
    return client_id.to_bytes(8, "big") + cc.point_to_bytes(c_i) + sig_i


def client_verify_membership(
    cm: ClientMaterial,
    msg: bytes,
    sig_i: bytes,
    c_i: object,
    merkle_root: bytes,
    proof,
    require_merkle: bool = True,
) -> bool:
    if not cc.verify_sig(cm.pk, msg, sig_i):
        return False
    if not require_merkle:
        return True
    leaf = leaf_bytes(cm.client_id, c_i, sig_i)
    return cc.verify_merkle_proof(leaf, proof, merkle_root)


def client_verify_aggregate(setup: Setup, G_Z: list[int], R_total: int, commitments: list[object]) -> bool:
    H_check = setup.H(G_Z)
    lhs = cc.point_add(H_check, cc.scalar_mul(setup.g0, R_total))
    C_A = cc.Z1 if not commitments else commitments[0]
    for c in commitments[1:]:
        C_A = cc.point_add(C_A, c)
    if not commitments:
        C_A = cc.Z1
    return cc.point_eq(lhs, C_A)
