$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'run_security_checks.ps1')
& (Join-Path $PSScriptRoot 'run_training.ps1')
& (Join-Path $PSScriptRoot 'generate_figures.ps1')
& (Join-Path $PSScriptRoot 'run_rust_benchmarks.ps1')
