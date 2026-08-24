from __future__ import annotations

import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

RESULTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "results"
RESULTS_DIR.mkdir(exist_ok=True)

B = 4096
LAMBDA = 128
TRIALS = 200_000


def optimal_distinguisher_advantage_theory(B: int, M: int) -> float:
    if M < B:
        return 0.5
    return B / (2 * (2 * M + 1))


def monte_carlo_advantage(B: int, M: int, trials: int, seed: int) -> float:
    rng = random.Random(seed)
    correct = 0
    upper_cut = M - B
    lower_cut = -M + B
    for _ in range(trials):
        x = 0 if rng.random() < 0.5 else B
        r = rng.randint(-M, M)
        eps = x - r
        if eps > upper_cut:
            guess = B
        elif eps < lower_cut:
            guess = 0
        else:
            guess = 0 if rng.random() < 0.5 else B
        if guess == x:
            correct += 1
    return correct / trials - 0.5


def main():
    ablated_Ms = [2 * B, 10 * B, 100 * B, 10_000 * B]
    rows = []
    for M in ablated_Ms:
        theory = optimal_distinguisher_advantage_theory(B, M)
        empirical = monte_carlo_advantage(B, M, TRIALS, seed=M)
        rows.append({"M": M, "M_over_B": M / B, "theory_advantage": theory,
                     "empirical_advantage": empirical, "trials": TRIALS})

    M_secure_d1 = B * (2 ** LAMBDA)
    secure_theory_adv = optimal_distinguisher_advantage_theory(B, M_secure_d1)

    d_vector = 24
    M_secure_vector = d_vector * B * (2 ** LAMBDA)
    secure_vector_theory_adv = optimal_distinguisher_advantage_theory(B, M_secure_vector)

    result = {
        "experiment": "mask_privacy_ablation",
        "B": B, "lambda": LAMBDA, "trials_per_point": TRIALS,
        "ablated_mask_sweep": rows,
        "full_mask_single_coordinate": {
            "M": M_secure_d1,
            "theory_advantage": secure_theory_adv,
        },
        "full_mask_vector": {
            "d": d_vector, "M": M_secure_vector,
            "theory_advantage": secure_vector_theory_adv,
        },
    }

    with open(RESULTS_DIR / "ablation_mask_privacy.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    mc_noise = 3 * (0.25 / TRIALS) ** 0.5
    assert rows[0]["empirical_advantage"] > 0.05, "The small-mask advantage is too low."
    for row in rows:
        tol = max(mc_noise, 0.15 * row["theory_advantage"])
        assert abs(row["empirical_advantage"] - row["theory_advantage"]) < tol, (
            f"M={row['M']} differs from the analytical estimate."
        )
    assert secure_vector_theory_adv < 2 ** -100, "The configured mask bound is not negligible."
    print("Mask privacy ablation passed.")


if __name__ == "__main__":
    main()
