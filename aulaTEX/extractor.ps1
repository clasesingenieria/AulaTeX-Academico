Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$extractorRoot = Join-Path $root 'aulaTEX\extractor-conceptos-ideas'

Set-Location $extractorRoot

if (!(Test-Path '.venv')) {
    python -m venv .venv
}

$pythonExe = Join-Path $extractorRoot '.venv\Scripts\python.exe'

if (!(Test-Path $pythonExe)) {
    throw "No se encontró el intérprete virtual: $pythonExe"
}

Start-Process -FilePath $pythonExe -ArgumentList 'run.py','--gui' -WorkingDirectory $extractorRoot
