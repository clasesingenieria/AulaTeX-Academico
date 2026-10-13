param(
    [switch]$UpgradePip
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$requirements = Join-Path $PSScriptRoot 'requirements-aulatex-deepagents.txt'

if (-not (Test-Path $venvPython)) {
    throw 'No existe .venv en la raiz. Ejecute primero .\aulaTEX\install-aulatex-langchain.ps1.'
}

if (-not (Test-Path $requirements)) {
    throw "No se encontro el archivo de dependencias: $requirements"
}

if ($UpgradePip) {
    & $venvPython -m pip install --upgrade pip setuptools wheel
    if ($LASTEXITCODE -ne 0) {
        throw 'Fallo la actualizacion base del entorno antes de instalar deepagents.'
    }
}

Write-Host 'Instalando deepagents como dependencia experimental opcional...' -ForegroundColor Yellow
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw 'Fallo la instalacion de deepagents.'
}

& $venvPython -m pip show deepagents
if ($LASTEXITCODE -ne 0) {
    throw 'La verificacion final de deepagents no fue satisfactoria.'
}

Write-Host 'deepagents quedo instalado como dependencia experimental opcional.' -ForegroundColor Green