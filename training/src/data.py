from __future__ import annotations

import numpy as np
from torch.utils.data import Dataset, Subset


def load_mnist(data_root: str):
    from torchvision import datasets, transforms

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])
    train_set = datasets.MNIST(data_root, train=True, download=True, transform=transform)
    test_set = datasets.MNIST(data_root, train=False, download=True, transform=transform)
    return train_set, test_set


def load_cifar10(data_root: str):
    from torchvision import datasets, transforms

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(
            (0.4914, 0.4822, 0.4465),
            (0.2023, 0.1994, 0.2010),
        ),
    ])
    train_set = datasets.CIFAR10(
        data_root,
        train=True,
        download=True,
        transform=transform,
    )
    test_set = datasets.CIFAR10(
        data_root,
        train=False,
        download=True,
        transform=transform,
    )
    return train_set, test_set


def load_dataset(name: str, data_root: str):
    if name == "mnist":
        return load_mnist(data_root)
    if name == "cifar10":
        return load_cifar10(data_root)
    raise ValueError(f"unknown dataset: {name}")


def partition_iid(
    dataset: Dataset,
    n_clients: int,
    samples_per_client: int | None = None,
    seed: int = 0,
):
    samples_per_client = samples_per_client or len(dataset) // n_clients
    requested = n_clients * samples_per_client
    if requested > len(dataset):
        raise ValueError(f"requested {requested} samples from a dataset of size {len(dataset)}")
    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(dataset))[:requested]
    return [
        Subset(dataset, indices[i * samples_per_client:(i + 1) * samples_per_client].tolist())
        for i in range(n_clients)
    ]


def partition_dirichlet(
    dataset: Dataset,
    n_clients: int,
    samples_per_client: int,
    alpha: float,
    seed: int = 0,
):
    if alpha <= 0 or n_clients <= 0 or samples_per_client <= 0:
        raise ValueError("alpha, n_clients, and samples_per_client must be positive")
    requested = n_clients * samples_per_client
    if requested > len(dataset):
        raise ValueError(f"requested {requested} samples from a dataset of size {len(dataset)}")
    rng = np.random.default_rng(seed)
    labels = np.asarray(dataset.targets)
    classes = np.unique(labels)
    pools = {
        label: rng.permutation(np.flatnonzero(labels == label)).tolist()
        for label in classes
    }
    proportions = rng.dirichlet(np.full(n_clients, alpha), size=len(classes))
    client_indices = [[] for _ in range(n_clients)]
    remaining = np.full(n_clients, samples_per_client, dtype=int)
    while remaining.sum():
        assigned = False
        for class_id, label in enumerate(classes):
            if not pools[label]:
                continue
            eligible = np.flatnonzero(remaining > 0)
            if not len(eligible):
                break
            weights = proportions[class_id, eligible] * remaining[eligible]
            probabilities = weights / weights.sum() if weights.sum() else None
            client_id = int(rng.choice(eligible, p=probabilities))
            client_indices[client_id].append(pools[label].pop())
            remaining[client_id] -= 1
            assigned = True
        if not assigned:
            raise RuntimeError("dataset exhausted before completing client partitions")
    return [Subset(dataset, indices) for indices in client_indices]


def make_eval_subset(dataset: Dataset, n_samples: int, seed: int = 0):
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(dataset), size=min(n_samples, len(dataset)), replace=False)
    return Subset(dataset, indices.tolist())
