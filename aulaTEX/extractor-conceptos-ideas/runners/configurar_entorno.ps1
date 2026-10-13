Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (!(Test-Path '.venv')) {
    python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-azure.txt
if (Test-Path 'requirements-anthropic.txt') {
    pip install -r requirements-anthropic.txt
}

if (!(Test-Path 'extractor.ev') -and (Test-Path 'extractor.ev.example')) {
    Copy-Item 'extractor.ev.example' 'extractor.ev'
    Write-Host 'Se creó extractor.ev desde extractor.ev.example. Edita credenciales y rutas antes de ejecutar.'
}

python run.py --probar-config
