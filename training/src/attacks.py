from __future__ import annotations

import numpy as np


def norm_inflation_attack(update: np.ndarray, scale: float = 20.0) -> np.ndarray:
    return update * scale


def gradient_concentration_attack(
    update: np.ndarray,
    target_norm: float,
    n_coordinates: int,
    rng: np.random.Generator,
) -> np.ndarray:
    support_size = min(max(1, n_coordinates), update.size)
    support = rng.choice(update.size, size=support_size, replace=False)
    poisoned = np.zeros_like(update)
    magnitude = target_norm / np.sqrt(support_size)
    poisoned[support] = magnitude * rng.choice([-1.0, 1.0], size=support_size)
    return poisoned
