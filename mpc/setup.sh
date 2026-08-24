#!/usr/bin/env bash
set -euo pipefail
root=${RIVET_MPSPDZ_ROOT:-MP-SPDZ}
commit=6a2256e327b507918859f605735543bb32a39d9d
libote_commit=1264725c3f08c2acaed70b2f3f67a68f38c53012
sudo apt-get update
sudo apt-get install -y git build-essential clang cmake automake libtool libboost-thread-dev libboost-filesystem-dev libboost-iostreams-dev libboost-program-options-dev libboost-system-dev libssl-dev libgmp-dev libsodium-dev libntl-dev libomp-dev python3 python3-pip iproute2 time
if [[ ! -d "$root/.git" ]]; then
    git clone https://github.com/data61/MP-SPDZ.git "$root"
fi
git -C "$root" checkout "$commit"
git -C "$root" submodule update --init deps/libOTe
git -C "$root/deps/libOTe" checkout "$libote_commit"
make -C "$root" -j"$(nproc)" mascot-party.x
