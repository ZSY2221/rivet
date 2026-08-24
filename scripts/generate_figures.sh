#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
python_bin=${RIVET_PYTHON:-$root/.venv/bin/python}
"$python_bin" plotting/summarize_accuracy.py
"$python_bin" plotting/plot_accuracy_curves.py --input results/training_results.csv --output-dir figures
"$python_bin" plotting/plot_security_checks.py
