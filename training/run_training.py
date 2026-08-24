from __future__ import annotations

import argparse
import csv
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import torch

from src.data import load_dataset, partition_dirichlet, partition_iid
from src.federated import run_federated_training

DATASET_LABELS = {"mnist": "MNIST", "cifar10": "CIFAR-10"}
SCHEME_LABELS = {"fedavg": "FedAvg", "rivet": "RIVET"}
ROOT = Path(__file__).resolve().parents[1]
with (ROOT / "configs" / "params.toml").open("rb") as config_file:
    CONFIG = tomllib.load(config_file)
TRAINING = CONFIG["training"]
TRAINING_SKETCH = CONFIG["sketch"]["training"]
DEFAULT_ROUNDS = {
    "mnist": TRAINING["mnist_rounds"],
    "cifar10": TRAINING["cifar10_rounds"],
}
FIELDS = (
    "dataset",
    "partition",
    "alpha",
    "attack",
    "scheme",
    "seed",
    "malicious_fraction",
    "round",
    "test_accuracy",
    "n_accepted",
    "n_benign_total",
    "n_benign_accepted",
    "n_malicious_accepted",
    "n_rejected_norm",
    "n_rejected_sketch",
    "norm_threshold",
    "sketch_threshold",
    "aborted",
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", nargs="+", choices=DATASET_LABELS, default=list(DATASET_LABELS))
    parser.add_argument("--partition", nargs="+", choices=("iid", "dirichlet"), default=["iid", "dirichlet"])
    parser.add_argument("--alpha", nargs="+", type=float, default=TRAINING["dirichlet_alpha"])
    parser.add_argument(
        "--attack",
        nargs="+",
        choices=("norm_inflation", "gradient_concentration"),
        default=["norm_inflation", "gradient_concentration"],
    )
    parser.add_argument("--scheme", nargs="+", choices=SCHEME_LABELS, default=list(SCHEME_LABELS))
    parser.add_argument("--seeds", nargs="+", type=int, default=TRAINING["seeds"])
    parser.add_argument("--malicious-fractions", nargs="+", type=float, default=TRAINING["malicious_fractions"])
    parser.add_argument("--clients", type=int, default=TRAINING["clients"])
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--local-epochs", type=int, default=TRAINING["local_epochs"])
    parser.add_argument("--learning-rate", type=float, default=TRAINING["learning_rate"])
    parser.add_argument("--batch-size", type=int, default=TRAINING["batch_size"])
    parser.add_argument("--minimum-accepted", type=int, default=TRAINING["minimum_accepted"])
    parser.add_argument("--samples-per-client", type=int, default=TRAINING["samples_per_client"])
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("results") / "training_results.csv")
    return parser.parse_args()


def partitions(args, dataset, partition: str, alpha: float | None, seed: int):
    if partition == "iid":
        return partition_iid(dataset, args.clients, args.samples_per_client, seed)
    return partition_dirichlet(dataset, args.clients, args.samples_per_client, alpha, seed)


def result_key(
    dataset: str,
    partition: str,
    alpha,
    attack: str,
    scheme: str,
    seed,
    fraction,
):
    alpha_value = "" if alpha in (None, "", "nan") else f"{float(alpha):g}"
    return (
        dataset,
        partition,
        alpha_value,
        attack,
        scheme,
        str(seed),
        f"{float(fraction):g}",
    )


def completed_runs(path: Path):
    completed = {}
    if not path.exists():
        return completed
    with path.open(newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            key = result_key(
                row["dataset"],
                row["partition"],
                row["alpha"],
                row["attack"],
                row["scheme"],
                row["seed"],
                row["malicious_fraction"],
            )
            completed[key] = max(completed.get(key, 0), int(row["round"]))
    return completed


def main() -> None:
    args = parse_args()
    device = torch.device(args.device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    completed = completed_runs(args.output)
    new_file = not args.output.exists() or args.output.stat().st_size == 0
    with args.output.open("a", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for dataset_name in args.dataset:
            train_set, test_set = load_dataset(dataset_name, str(args.data_root / dataset_name))
            rounds = args.rounds or DEFAULT_ROUNDS[dataset_name]
            for partition in args.partition:
                alpha_values = [None] if partition == "iid" else args.alpha
                for alpha in alpha_values:
                    for seed in args.seeds:
                        client_sets = partitions(args, train_set, partition, alpha, seed)
                        for attack in args.attack:
                            for fraction in args.malicious_fractions:
                                malicious_count = round(args.clients * fraction)
                                malicious_ids = set(range(malicious_count))
                                for scheme in args.scheme:
                                    key = result_key(
                                        DATASET_LABELS[dataset_name],
                                        partition,
                                        alpha,
                                        attack,
                                        SCHEME_LABELS[scheme],
                                        seed,
                                        fraction,
                                    )
                                    if completed.get(key, 0) >= rounds:
                                        continue
                                    print(
                                        DATASET_LABELS[dataset_name],
                                        partition,
                                        alpha if alpha is not None else "-",
                                        attack,
                                        SCHEME_LABELS[scheme],
                                        seed,
                                        fraction,
                                        flush=True,
                                    )
                                    history = run_federated_training(
                                        client_datasets=client_sets,
                                        malicious_ids=malicious_ids,
                                        attack=attack,
                                        method=scheme,
                                        evaluation_dataset=test_set,
                                        rounds=rounds,
                                        local_epochs=args.local_epochs,
                                        learning_rate=args.learning_rate,
                                        batch_size=args.batch_size,
                                        device=device,
                                        seed=seed,
                                        sketch=TRAINING_SKETCH,
                                        minimum_accepted=args.minimum_accepted,
                                        dataset_name=dataset_name,
                                        norm_inflation=TRAINING["norm_inflation"],
                                        concentrated_coordinates=TRAINING["concentrated_coordinates"],
                                    )
                                    for row in history:
                                        writer.writerow({
                                            "dataset": DATASET_LABELS[dataset_name],
                                            "partition": partition,
                                            "alpha": "" if alpha is None else alpha,
                                            "attack": attack,
                                            "scheme": SCHEME_LABELS[scheme],
                                            "seed": seed,
                                            "malicious_fraction": fraction,
                                            "round": row["round"] + 1,
                                            "test_accuracy": row["test_accuracy"],
                                            "n_accepted": row["n_accepted"],
                                            "n_benign_total": row["n_benign_total"],
                                            "n_benign_accepted": row["n_benign_accepted"],
                                            "n_malicious_accepted": row["n_malicious_accepted"],
                                            "n_rejected_norm": row["n_rejected_norm"],
                                            "n_rejected_sketch": row["n_rejected_sketch"],
                                            "norm_threshold": row["norm_threshold"],
                                            "sketch_threshold": row["sketch_threshold"],
                                            "aborted": row["aborted"],
                                        })
                                    output.flush()


if __name__ == "__main__":
    main()
