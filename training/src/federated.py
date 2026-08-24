from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from .attacks import gradient_concentration_attack, norm_inflation_attack
from .screening import (
    build_sketch_matrices,
    calibrate_threshold,
    sketch_energies,
    two_layer_screen,
    update_norm,
)
from .model import build_model, get_flat_params, set_flat_params


def local_train(
    global_parameters: torch.Tensor,
    dataset,
    device,
    epochs: int,
    learning_rate: float,
    batch_size: int,
    seed: int,
    dataset_name: str = "mnist",
) -> np.ndarray:
    torch.manual_seed(seed)
    model = build_model(dataset_name).to(device)
    set_flat_params(model, global_parameters.to(device))
    model.train()
    optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, generator=generator)
    for _ in range(epochs):
        for inputs, labels in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = F.cross_entropy(model(inputs), labels)
            loss.backward()
            optimizer.step()
    trained_parameters = get_flat_params(model)
    return (trained_parameters - global_parameters.to(device)).cpu().numpy()


@torch.no_grad()
def evaluate(
    parameters: torch.Tensor,
    dataset,
    device,
    batch_size: int = 256,
    dataset_name: str = "mnist",
) -> float:
    model = build_model(dataset_name).to(device)
    set_flat_params(model, parameters.to(device))
    model.eval()
    loader = DataLoader(dataset, batch_size=batch_size)
    correct = 0
    total = 0
    for inputs, labels in loader:
        inputs, labels = inputs.to(device), labels.to(device)
        predictions = model(inputs).argmax(1)
        correct += (predictions == labels).sum().item()
        total += labels.size(0)
    return correct / total


def run_federated_training(
    client_datasets: list,
    malicious_ids: set[int],
    attack: str,
    method: str,
    evaluation_dataset,
    rounds: int,
    local_epochs: int,
    learning_rate: float,
    batch_size: int,
    device,
    seed: int,
    sketch: dict,
    minimum_accepted: int = 1,
    dataset_name: str = "mnist",
    norm_inflation: float = 20.0,
    concentrated_coordinates: int = 20,
) -> list[dict]:
    if method not in {"fedavg", "rivet"}:
        raise ValueError("method must be 'fedavg' or 'rivet'")
    if attack not in {"none", "norm_inflation", "gradient_concentration"}:
        raise ValueError("unknown attack")

    torch.manual_seed(seed)
    np.random.seed(seed)
    rng = np.random.default_rng(seed)
    model = build_model(dataset_name).to(device)
    global_parameters = get_flat_params(model).cpu()
    dimension = global_parameters.numel()
    history = []
    for round_index in range(rounds):
        updates = []
        for client_id, dataset in enumerate(client_datasets):
            update = local_train(
                global_parameters,
                dataset,
                device,
                local_epochs,
                learning_rate,
                batch_size,
                seed=seed * 1000 + round_index * 37 + client_id,
                dataset_name=dataset_name,
            )
            if client_id in malicious_ids and attack == "norm_inflation":
                update = norm_inflation_attack(update, scale=norm_inflation)
            elif client_id in malicious_ids and attack == "gradient_concentration":
                update = gradient_concentration_attack(
                    update,
                    target_norm=float(np.linalg.norm(update)),
                    n_coordinates=concentrated_coordinates,
                    rng=rng,
                )
            updates.append(update)

        norm_threshold = None
        energy_threshold = None
        if method == "rivet":
            matrices = build_sketch_matrices(
                d=dimension,
                n_matrices=sketch["L"],
                n_rows=sketch["k"],
                row_weight=sketch["q_sk"],
                seed=seed * 1000 + round_index + 999,
            )
            norm_threshold = calibrate_threshold([update_norm(update) for update in updates])
            energy_threshold = calibrate_threshold([
                max(sketch_energies(update, matrices)) for update in updates
            ])
            diagnostics = [
                two_layer_screen(update, matrices, norm_threshold, energy_threshold)[1]
                for update in updates
            ]
            accepted_ids = [
                client_id
                for client_id, diag in enumerate(diagnostics)
                if diag["layer1_ok"] and diag["layer2_ok"]
            ]
        else:
            accepted_ids = list(range(len(updates)))
            diagnostics = [
                {
                    "norm_ok": True,
                    "layer1_ok": True,
                    "sketch_ok": True,
                    "layer2_ok": True,
                }
                for _ in updates
            ]

        aborted = len(accepted_ids) < minimum_accepted
        if not aborted:
            aggregate = np.mean([updates[client_id] for client_id in accepted_ids], axis=0)
            global_parameters = global_parameters + torch.from_numpy(aggregate).float()

        history.append({
            "round": round_index,
            "test_accuracy": evaluate(
                global_parameters,
                evaluation_dataset,
                device,
                dataset_name=dataset_name,
            ),
            "n_accepted": len(accepted_ids),
            "n_benign_total": len(client_datasets) - len(malicious_ids),
            "n_benign_accepted": sum(
                client_id not in malicious_ids for client_id in accepted_ids
            ),
            "n_malicious_accepted": sum(client_id in malicious_ids for client_id in accepted_ids),
            "n_rejected_norm": sum(not diag["layer1_ok"] for diag in diagnostics),
            "n_rejected_sketch": sum(
                diag["layer1_ok"] and not diag["layer2_ok"] for diag in diagnostics
            ),
            "aborted": aborted,
            "norm_threshold": norm_threshold,
            "energy_threshold": energy_threshold,
            "sketch_threshold": energy_threshold,
        })

    return history
