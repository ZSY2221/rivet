from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import TensorDataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))
sys.path.insert(0, str(ROOT / "plotting"))

from plot_accuracy_curves import PANELS, draw_panel, select_panel
from src.data import partition_dirichlet
from src.federated import run_federated_training
from src.model import CIFAR10CNN, MNISTCNN


def training_check(dataset_name: str, shape: tuple[int, ...]) -> None:
    inputs = torch.randn((8,) + shape)
    labels = torch.arange(8) % 10
    dataset = TensorDataset(inputs, labels)
    for method in ("fedavg", "rivet"):
        history = run_federated_training(
            client_datasets=[dataset, dataset],
            malicious_ids={0},
            attack="norm_inflation",
            method=method,
            evaluation_dataset=dataset,
            rounds=1,
            local_epochs=1,
            learning_rate=0.01,
            batch_size=4,
            device=torch.device("cpu"),
            seed=7,
            sketch={"L": 2, "k": 2, "q_sk": 2},
            minimum_accepted=1,
            dataset_name=dataset_name,
        )
        assert len(history) == 1


def partition_check() -> None:
    dataset = TensorDataset(torch.randn(200, 1, 28, 28), torch.arange(200) % 10)
    dataset.targets = torch.arange(200) % 10
    clients = partition_dirichlet(dataset, 10, 10, 0.1, 7)
    assert [len(client) for client in clients] == [10] * 10


def plotting_check() -> None:
    rows = []
    for dataset, partition, alpha, attack, _ in PANELS:
        for scheme in ("FedAvg", "RIVET"):
            for round_index in (1, 2):
                rows.append({
                    "dataset": dataset,
                    "partition": partition,
                    "alpha": alpha,
                    "attack": attack,
                    "scheme": scheme,
                    "seed": 0,
                    "malicious_fraction": 0.3,
                    "round": round_index,
                    "test_accuracy": 0.5,
                })
    data = pd.DataFrame(rows)
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        for dataset, partition, alpha, attack, filename in PANELS:
            panel = select_panel(data, dataset, partition, alpha, attack)
            draw_panel(panel, output / filename)
        assert len(list(output.glob("*.pdf"))) == len(PANELS)


def main() -> None:
    assert MNISTCNN()(torch.zeros(1, 1, 28, 28)).shape == (1, 10)
    assert CIFAR10CNN()(torch.zeros(1, 3, 32, 32)).shape == (1, 10)
    partition_check()
    training_check("mnist", (1, 28, 28))
    training_check("cifar10", (3, 32, 32))
    plotting_check()
    print("RIVET setup ready")


if __name__ == "__main__":
    main()
