$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    cargo test --manifest-path rust\Cargo.toml
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    cargo run --release --manifest-path rust\Cargo.toml --bin client_commitment_benchmark
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    cargo run --release --manifest-path rust\Cargo.toml --bin server_binding_benchmark
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
