from __future__ import annotations

import numpy as np


def update_norm(update: np.ndarray) -> float:
    return float(np.linalg.norm(update))


def calibrate_threshold(values: list[float], multiplier: float = 4.0) -> float:
    samples = np.asarray(values, dtype=float)
    median = float(np.median(samples))
    mad = float(np.median(np.abs(samples - median)))
    return median + multiplier * mad


def build_sketch_matrices(d: int, n_matrices: int, n_rows: int, row_weight: int, seed: int):
    rng = np.random.default_rng(seed)
    matrices = []
    for _ in range(n_matrices):
        rows = []
        for _ in range(n_rows):
            columns = rng.choice(d, size=min(row_weight, d), replace=False)
            signs = rng.choice([-1.0, 1.0], size=len(columns))
            rows.append((columns, signs))
        matrices.append(rows)
    return matrices


def sketch_energies(update: np.ndarray, matrices) -> list[float]:
    energies = []
    for rows in matrices:
        energy = 0.0
        for columns, signs in rows:
            projection = float(np.dot(update[columns], signs))
            energy += projection * projection
        energies.append(energy)
    return energies


def two_layer_screen(
    update: np.ndarray,
    matrices,
    norm_threshold: float,
    energy_threshold: float,
) -> tuple[bool, dict]:
    norm = update_norm(update)
    maximum_energy = max(sketch_energies(update, matrices))
    norm_ok = norm <= norm_threshold
    sketch_ok = maximum_energy <= energy_threshold
    return norm_ok and sketch_ok, {
        "norm": norm,
        "norm_ok": norm_ok,
        "layer1_ok": norm_ok,
        "sketch_energy": maximum_energy,
        "sketch_ok": sketch_ok,
        "layer2_ok": sketch_ok,
    }
