$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
py -3 -c "import sys; assert (3, 10) <= sys.version_info[:2] <= (3, 12), 'Python 3.10-3.12 required'"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& .\.venv\Scripts\python.exe scripts\check_environment.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& .\.venv\Scripts\python.exe scripts\check_setup.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
