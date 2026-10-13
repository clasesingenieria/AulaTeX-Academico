Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $repoRoot 'interfaz-telegram.ps1'

& $launcher -BootstrapOnly
if ($LASTEXITCODE -ne 0) {
    throw 'El bootstrap del bot no termino correctamente.'
}

$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) {
    throw 'No se creo ni detecto la .venv local del bot.'
}