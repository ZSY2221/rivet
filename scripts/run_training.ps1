$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { $Python = 'py' }
Push-Location $Root
try {
    if ($Python -eq 'py') { & $Python -3 training/run_training.py @args }
    else { & $Python training/run_training.py @args }
    $Code = $LASTEXITCODE
} finally {
    Pop-Location
}
if ($Code -ne 0) { exit $Code }
