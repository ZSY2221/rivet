from __future__ import annotations

import hashlib
from typing import Sequence

from py_ecc.bls.hash_to_curve import hash_to_G1
from py_ecc.bls12_381 import FQ, G1, Z1, add, multiply, neg, curve_order, eq, field_modulus
from py_ecc.optimized_bls12_381 import normalize
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature

R = curve_order

Point = tuple


def sha256(*parts: bytes) -> bytes:
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.digest()


def derive_generator(seed: str, index: int) -> Point:
    message = seed.encode("utf-8") + index.to_bytes(8, "big")
    dst = b"RIVET-G1-BLIND-v1" if index == 0 else b"RIVET-G1-LHH-v1"
    point_jacobian = hash_to_G1(message, dst, hashlib.sha256)
    x, y = normalize(point_jacobian)
    return (FQ(int(x)), FQ(int(y)))


def gen_generators(seed: str, d: int) -> list[Point]:
    return [derive_generator(seed, i) for i in range(d + 1)]


def H_Z(x: Sequence[int], generators: Sequence[Point]) -> Point:
    assert len(x) == len(generators), "Vector and generator lengths differ."
    acc = Z1
    for x_l, g_l in zip(x, generators):
        if x_l == 0:
            continue
        if x_l > 0:
            term = multiply(g_l, x_l)
        else:
            term = neg(multiply(g_l, -x_l))
        acc = add(acc, term)
    return acc


def pedersen_commit(x: Sequence[int], generators: Sequence[Point], rho: int, g0: Point) -> Point:
    return add(H_Z(x, generators), multiply(g0, rho % R))


def point_add(p1: Point, p2: Point) -> Point:
    return add(p1, p2)


def point_neg(p: Point) -> Point:
    return neg(p)


def point_sub(p1: Point, p2: Point) -> Point:
    return add(p1, neg(p2))


def scalar_mul(p: Point, k: int) -> Point:
    if k >= 0:
        return multiply(p, k % R)
    return neg(multiply(p, (-k) % R))


def point_eq(p1: Point, p2: Point) -> bool:
    return eq(p1, p2)


def point_to_bytes(p: Point) -> bytes:
    if p is None:
        return ((1 << 383) | (1 << 382)).to_bytes(48, "big")
    x, y = p
    sign = (2 * int(y)) // field_modulus
    encoded = int(x) | (1 << 383) | (sign << 381)
    return encoded.to_bytes(48, "big")


def gen_signing_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def sign(sk: Ed25519PrivateKey, message: bytes) -> bytes:
    return sk.sign(message)


def verify_sig(pk: Ed25519PublicKey, message: bytes, signature: bytes) -> bool:
    try:
        pk.verify(signature, message)
        return True
    except InvalidSignature:
        return False


def merkle_leaf(data: bytes) -> bytes:
    return sha256(b"\x00", data)


def merkle_node(left: bytes, right: bytes) -> bytes:
    return sha256(b"\x01", left, right)


def build_merkle_tree(leaves_data: list[bytes]):
    if not leaves_data:
        return sha256(b"EMPTY_TREE"), [[]]
    level = [merkle_leaf(d) for d in leaves_data]
    levels = [level]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(merkle_node(left, right))
        levels.append(nxt)
        level = nxt
    return level[0], levels


def merkle_proof(levels, index: int):
    proof = []
    idx = index
    for level in levels[:-1]:
        if idx % 2 == 0:
            sib_idx = idx + 1 if idx + 1 < len(level) else idx
            sibling_is_left = False
        else:
            sib_idx = idx - 1
            sibling_is_left = True
        proof.append((level[sib_idx], sibling_is_left))
        idx //= 2
    return proof


def verify_merkle_proof(leaf_data: bytes, proof, root: bytes) -> bool:
    cur = merkle_leaf(leaf_data)
    for sib, sibling_is_left in proof:
        if sibling_is_left:
            cur = merkle_node(sib, cur)
        else:
            cur = merkle_node(cur, sib)
    return cur == root
