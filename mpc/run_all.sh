#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
bash mpc/run_benchmark.sh 10000 16 128 1
bash mpc/run_benchmark.sh 10000 16 128 10
bash mpc/run_benchmark.sh 100000 16 128 1
bash mpc/run_benchmark.sh 100000 16 128 10
python3 mpc/summarize_results.py
