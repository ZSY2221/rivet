#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
cargo test --manifest-path rust/Cargo.toml
cargo run --release --manifest-path rust/Cargo.toml --bin client_commitment_benchmark
cargo run --release --manifest-path rust/Cargo.toml --bin server_binding_benchmark
