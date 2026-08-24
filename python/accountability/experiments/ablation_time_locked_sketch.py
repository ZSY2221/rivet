from __future__ import annotations

import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

RESULTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "results"
RESULTS_DIR.mkdir(exist_ok=True)

D = 1024
L = 8
K = 16
Q_SK = 4
TRIALS = 5000


def sample_sketch_matrices(d: int, L: int, k: int, q_sk: int, seed: int):
    rng = random.Random(seed)
    matrices = []
    touched = set()
    for _ in range(L):
        rows = []
        for _ in range(k):
            cols = rng.sample(range(d), q_sk)
            signs = [rng.choice([-1, 1]) for _ in cols]
            rows.append(list(zip(cols, signs)))
            touched.update(cols)
        matrices.append(rows)
    return matrices, touched


def sketch_energy_at_single_coord(matrices, coord: int, magnitude: int) -> float:
    total = 0
    for rows in matrices:
        for row in rows:
            y = sum(sign * magnitude for col, sign in row if col == coord)
            total += y * y
    return total


def adaptive_attack_trial(seed: int) -> dict:
    matrices, touched = sample_sketch_matrices(D, L, K, Q_SK, seed)
    untouched = [c for c in range(D) if c not in touched]
    if not untouched:
        return {"evaded": False, "reason": "no_untouched_coord"}
    rng = random.Random(seed + 1)
    coord = rng.choice(untouched)
    energy = sketch_energy_at_single_coord(matrices, coord, magnitude=4096)
    return {"evaded": energy == 0, "energy": energy}


def non_adaptive_attack_trial(seed: int) -> dict:
    rng = random.Random(seed)
    coord = rng.randrange(D)
    matrices, touched = sample_sketch_matrices(D, L, K, Q_SK, seed + 10_000_000)
    energy = sketch_energy_at_single_coord(matrices, coord, magnitude=4096)
    return {"evaded": energy == 0, "energy": energy, "coord_touched": coord in touched}


def theoretical_miss_probability(d: int, L: int, k: int, q_sk: int) -> float:
    return (1 - q_sk / d) ** (L * k)


def main():
    adaptive_results = [adaptive_attack_trial(seed=i) for i in range(TRIALS)]
    non_adaptive_results = [non_adaptive_attack_trial(seed=i) for i in range(TRIALS)]

    adaptive_evasion_rate = sum(r["evaded"] for r in adaptive_results) / TRIALS
    non_adaptive_evasion_rate = sum(r["evaded"] for r in non_adaptive_results) / TRIALS
    theory_miss_p = theoretical_miss_probability(D, L, K, Q_SK)

    result = {
        "experiment": "time_locked_sketch_ablation",
        "d": D, "L": L, "k": K, "q_sk": Q_SK, "trials": TRIALS,
        "adaptive_evasion_rate": adaptive_evasion_rate,
        "non_adaptive_evasion_rate": non_adaptive_evasion_rate,
        "theoretical_miss_probability": theory_miss_p,
    }

    with open(RESULTS_DIR / "ablation_time_locked_sketch.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    assert adaptive_evasion_rate > 0.99, "The adaptive attack should usually find an uncovered coordinate."
    assert non_adaptive_evasion_rate < adaptive_evasion_rate - 0.1, (
        "The pre-commitment escape rate should be lower than the adaptive rate."
    )
    assert abs(non_adaptive_evasion_rate - theory_miss_p) < 0.1, "The measured rate should match the approximation."
    print("Time-locked sketch ablation passed.")


if __name__ == "__main__":
    main()
