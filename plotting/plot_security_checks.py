from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt
import pandas as pd


def plot_forgery_interception(results_dir: Path, output_dir: Path) -> None:
    data = pd.read_csv(results_dir / "aggregate_accountability.csv")
    forged = data[data["scenario"].isin(("forge_G_only", "forge_R_only", "forge_both"))].copy()
    forged["accepted"] = forged["accepted"].astype(str).str.lower().eq("true")
    rates = 1.0 - forged.groupby("scenario")["accepted"].mean()
    labels = ("Aggregate", "Blinding", "Both")
    values = [rates[name] for name in ("forge_G_only", "forge_R_only", "forge_both")]

    fig, axis = plt.subplots(figsize=(4.2, 2.8))
    axis.bar(labels, values, color="#4c72b0")
    axis.set_ylabel("Interception rate")
    axis.set_ylim(0, 1.05)
    axis.grid(axis="y", linewidth=0.35, alpha=0.35)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_04a_g3_forgery_interception.pdf")
    plt.close(fig)


def plot_dropout(results_dir: Path, output_dir: Path) -> None:
    with open(results_dir / "dropout_robustness_summary.json", encoding="utf-8") as file:
        summary = json.load(file)
    rows = summary["dropout_rate_sweep"]
    rates = [row["dropout_p"] for row in rows]
    measured = [row["mean_R_t_size"] for row in rows]
    expected = [row["expected_R_t_size_approx"] for row in rows]

    fig, axis = plt.subplots(figsize=(4.2, 2.8))
    axis.plot(rates, measured, marker="o", label="Measured")
    axis.plot(rates, expected, linestyle="--", label=r"$N(1-p)^2$")
    axis.set_xlabel("Dropout probability")
    axis.set_ylabel("Accepted clients")
    axis.grid(True, linewidth=0.35, alpha=0.35)
    axis.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_04c_dropout_robustness.pdf")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the G3 and dropout validation figures.")
    parser.add_argument("--results-dir", type=Path, default=Path("python/results"))
    parser.add_argument("--output-dir", type=Path, default=Path("figures"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plot_forgery_interception(args.results_dir, args.output_dir)
    plot_dropout(args.results_dir, args.output_dir)


if __name__ == "__main__":
    main()
