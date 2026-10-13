Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve repo root (script may be in aulaTEX/)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = if ((Split-Path -Leaf $scriptDir) -ieq 'scripts') { Split-Path -Parent $scriptDir } else { $scriptDir }
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $pythonExe)) {
    throw "No se encontró el intérprete virtual en: $pythonExe"
}

Push-Location $repoRoot
& $pythonExe -c "from src.worker import run_once; print(run_once())"
Pop-Location
