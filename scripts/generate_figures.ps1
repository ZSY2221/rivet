$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
Push-Location $Root
try {
    & $Python plotting\summarize_accuracy.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $Python plotting\plot_accuracy_curves.py --input results\training_results.csv --output-dir figures
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $Python plotting\plot_security_checks.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
