from __future__ import annotations

import math
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[3]
PARAMS_PATH = ROOT / "configs" / "params.toml"


def load_root_params() -> dict:
    with open(PARAMS_PATH, "rb") as f:
        return tomllib.load(f)


class ExperimentParams:
    def __init__(self, d_test: int = 32, n_test: int = 20, seed: str = "rivet-accountability-v1",
                 lambda_override: int | None = None):
        root = load_root_params()
        self.lam = int(lambda_override if lambda_override is not None else root["security"]["lambda"])
        self.s = root["fixed_point"]["s"]
        self.C = root["fixed_point"]["C"]
        self.B = int(root["fixed_point"]["B"])
        expected_B = math.ceil(self.s * self.C)
        assert self.B == expected_B, f"B={self.B} does not match ceil(s*C)={expected_B}"

        self.d = d_test
        self.N = n_test
        self.N_max = n_test
        self.seed = seed

        self.M = self.d * self.B * (2 ** self.lam)

    def no_wraparound_ok(self, r: int) -> bool:
        return self.N_max * (self.B + self.M) < r // 2
