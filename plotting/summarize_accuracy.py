from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("results/training_results.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/final_accuracy.csv"))
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    keys = ["dataset", "partition", "alpha", "attack", "scheme", "malicious_fraction"]
    final_rounds = data.groupby(keys + ["seed"], dropna=False)["round"].transform("max")
    final = data[data["round"].eq(final_rounds)]
    summary = final.groupby(keys, dropna=False)["test_accuracy"].agg(["mean", "std"]).reset_index()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
