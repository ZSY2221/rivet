$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'py' }
$env:PYTHONPATH = Join-Path $repo 'python/accountability'
Push-Location (Join-Path $repo 'python/accountability')
try {
  $modules = @(
    'experiments.aggregate_accountability',
    'experiments.ablation_hash_recompute',
    'experiments.ablation_authenticated_auxiliary',
    'experiments.ablation_merkle_membership',
    'experiments.ablation_mask_privacy',
    'experiments.ablation_time_locked_sketch',
    'experiments.dropout_robustness'
  )
  foreach ($module in $modules) {
    if ($python -eq 'py') { & $python -3 -B -m $module }
    else { & $python -B -m $module }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
}
finally {
  Pop-Location
}
