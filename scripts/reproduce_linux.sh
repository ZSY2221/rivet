#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
./scripts/run_security_checks.sh
./scripts/run_training.sh
./scripts/generate_figures.sh
./scripts/run_rust_benchmarks.sh
bash mpc/setup.sh
bash mpc/run_all.sh
