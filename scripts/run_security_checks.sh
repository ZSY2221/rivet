#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
python_bin=${RIVET_PYTHON:-$root/.venv/bin/python}
export PYTHONPATH="$root/python/accountability"
modules=(
    experiments.aggregate_accountability
    experiments.ablation_hash_recompute
    experiments.ablation_authenticated_auxiliary
    experiments.ablation_merkle_membership
    experiments.ablation_mask_privacy
    experiments.ablation_time_locked_sketch
    experiments.dropout_robustness
)
for module in "${modules[@]}"; do
    "$python_bin" -B -m "$module"
done
