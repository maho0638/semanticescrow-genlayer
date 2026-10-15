$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
Write-Host 'SemanticEscrow Phase 7 - Bradbury Testnet'
$venv = Join-Path $root '.phase7-venv'
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.12 -m venv $venv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m venv $venv
} else {
    Write-Host 'Python missing. Please install Python 3.12 from python.org.'
    exit 2
}
if ($LASTEXITCODE -ne 0) { throw 'Python venv failed. Please install Python 3.12.' }
$python = Join-Path $venv 'Scripts\python.exe'
& $python -m pip install --disable-pip-version-check 'genlayer-test==0.30.0rc2' 'eth-account==0.14.0' 'requests==2.32.5' 'pytest==9.1.1'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $python 'tools/phase7_bradbury_windows.py'
exit $LASTEXITCODE
