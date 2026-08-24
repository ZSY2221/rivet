from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt
import pandas as pd

SCHEMES = ("FedAvg", "RIVET")
COLORS = {"FedAvg": "#7f7f7f", "RIVET": "#d62728"}
STYLES = {"FedAvg": "--", "RIVET": "-"}

PANELS = (
    ("MNIST", "iid", None, "norm_inflation", "fig_06a_mnist_norm_inflation_accuracy_curve.pdf"),
    ("MNIST", "iid", None, "gradient_concentration", "fig_06b_mnist_gradient_concentration_accuracy_curve.pdf"),
    ("CIFAR-10", "iid", None, "norm_inflation", "fig_07a_cifar10_norm_inflation_accuracy_curve.pdf"),
    ("CIFAR-10", "iid", None, "gradient_concentration", "fig_07b_cifar10_gradient_concentration_accuracy_curve.pdf"),
    ("MNIST", "dirichlet", 0.1, "norm_inflation", "fig_08a_noniid_mnist_norm_inflation_accuracy_curve_alpha_01.pdf"),
    ("MNIST", "dirichlet", 0.5, "norm_inflation", "fig_08b_noniid_mnist_norm_inflation_accuracy_curve_alpha_05.pdf"),
    ("MNIST", "dirichlet", 0.1, "gradient_concentration", "fig_08c_noniid_mnist_gradient_concentration_accuracy_curve_alpha_01.pdf"),
    ("MNIST", "dirichlet", 0.5, "gradient_concentration", "fig_08d_noniid_mnist_gradient_concentration_accuracy_curve_alpha_05.pdf"),
    ("CIFAR-10", "dirichlet", 0.1, "norm_inflation", "fig_09a_noniid_cifar10_norm_inflation_accuracy_curve_alpha_01.pdf"),
    ("CIFAR-10", "dirichlet", 0.5, "norm_inflation", "fig_09b_noniid_cifar10_norm_inflation_accuracy_curve_alpha_05.pdf"),
    ("CIFAR-10", "dirichlet", 0.1, "gradient_concentration", "fig_09c_noniid_cifar10_gradient_concentration_accuracy_curve_alpha_01.pdf"),
    ("CIFAR-10", "dirichlet", 0.5, "gradient_concentration", "fig_09d_noniid_cifar10_gradient_concentration_accuracy_curve_alpha_05.pdf"),
)

REQUIRED_COLUMNS = {
    "dataset", "partition", "alpha", "attack", "scheme", "seed",
    "malicious_fraction", "round", "test_accuracy",
}


def read_results(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        raise ValueError(f"missing columns: {', '.join(sorted(missing))}")
    data = data[data["scheme"].isin(SCHEMES)].copy()
    data = data[(data["malicious_fraction"] - 0.30).abs() < 1e-12]
    return data


def select_panel(data: pd.DataFrame, dataset: str, partition: str, alpha, attack: str):
    selected = data[
        data["dataset"].eq(dataset)
        & data["partition"].eq(partition)
        & data["attack"].eq(attack)
    ]
    if alpha is None:
        selected = selected[selected["alpha"].isna()]
    else:
        selected = selected[(selected["alpha"] - alpha).abs() < 1e-12]
    return selected


def draw_panel(data: pd.DataFrame, output: Path) -> None:
    means = data.groupby(["scheme", "round"], as_index=False)["test_accuracy"].mean()
    fig, axis = plt.subplots(figsize=(4.88, 3.70))
    for scheme in SCHEMES:
        series = means[means["scheme"].eq(scheme)].sort_values("round")
        if series.empty:
            raise ValueError(f"missing {scheme} rows for {output.name}")
        axis.plot(
            series["round"],
            series["test_accuracy"],
            label=scheme,
            color=COLORS[scheme],
            linestyle=STYLES[scheme],
            linewidth=1.5,
        )
    axis.set_xlabel("Communication rounds")
    axis.set_ylabel("Test accuracy")
    axis.grid(True, linewidth=0.35, alpha=0.35)
    axis.legend(loc="best", frameon=True)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, format="pdf")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render the paper's FedAvg and RIVET accuracy curves from per-round CSV data."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()

    data = read_results(args.input)
    for dataset, partition, alpha, attack, filename in PANELS:
        panel = select_panel(data, dataset, partition, alpha, attack)
        if panel.empty and args.allow_partial:
            continue
        if panel.empty:
            raise ValueError(f"no rows available for {filename}")
        draw_panel(panel, args.output_dir / filename)


if __name__ == "__main__":
    main()
