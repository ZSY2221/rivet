#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
python3 -c "import sys; assert (3, 10) <= sys.version_info[:2] <= (3, 12), 'Python 3.10-3.12 required'"
python3 -m venv .venv
"$root/.venv/bin/python" -m pip install --upgrade pip
"$root/.venv/bin/python" -m pip install -r requirements.txt
"$root/.venv/bin/python" scripts/check_environment.py
"$root/.venv/bin/python" scripts/check_setup.py
