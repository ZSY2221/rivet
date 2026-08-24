#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 4 ]]; then
    echo "usage: $0 D L K RTT_MS" >&2
    exit 2
fi
d=$1
L=$2
k=$3
rtt=$4
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/.." && pwd)
mp_spdz_root=${RIVET_MPSPDZ_ROOT:-$repo_root/MP-SPDZ}
result_dir=${RIVET_MPC_RESULTS_DIR:-$repo_root/mpc/results}
name="rivet_screen-${d}-${L}-${k}"
mkdir -p "$result_dir"
cp "$script_dir/rivet_screen.mpc" "$mp_spdz_root/Programs/Source/rivet_screen.mpc"
cd "$mp_spdz_root"
./compile.py rivet_screen "$d" "$L" "$k" | tee "$result_dir/${name}_compile.log"
half_rtt=$(python3 -c "print(float('$rtt') / 2)")
cleanup() {
    sudo tc qdisc del dev lo root 2>/dev/null || true
}
trap cleanup EXIT
sudo tc qdisc replace dev lo root netem delay "${half_rtt}ms"
echo "CONFIG d=$d L=$L k=$k rtt_ms=$rtt half_delay_ms=$half_rtt" | tee "$result_dir/${name}_rtt${rtt}ms.log"
Scripts/mascot.sh -v "$name" 2>&1 | tee -a "$result_dir/${name}_rtt${rtt}ms.log"
