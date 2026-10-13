param(
    [string]$PythonExe = "",
    [switch]$UpgradePip
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$venvDir = Join-Path $repoRoot '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$requirements = Join-Path $PSScriptRoot 'requirements-aulatex-langchain.txt'

if (-not (Test-Path $requirements)) {
    throw "No se encontro el archivo de dependencias: $requirements"
}

function Resolve-BootstrapPython {
    param([string]$Requested)

    if ($Requested) {
        return [pscustomobject]@{ Command = $Requested; Arguments = @() }
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $py) {
        return [pscustomobject]@{ Command = $py.Source; Arguments = @('-3') }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $python) {
        return [pscustomobject]@{ Command = $python.Source; Arguments = @() }
    }

    throw 'No se encontro un interprete Python para crear .venv. Use -PythonExe.'
}

if (-not (Test-Path $venvPython)) {
    $bootstrap = Resolve-BootstrapPython -Requested $PythonExe
    Write-Host "Creando entorno virtual en $venvDir" -ForegroundColor Cyan
    & $bootstrap.Command @($bootstrap.Arguments) -m venv $venvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
        throw 'No se pudo crear el entorno virtual de AulaTeX.'
    }
}

if ($UpgradePip) {
    Write-Host 'Actualizando pip, setuptools y wheel...' -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip setuptools wheel
    if ($LASTEXITCODE -ne 0) {
        throw 'Fallo la actualizacion base de pip/setuptools/wheel.'
    }
}

Write-Host 'Instalando dependencias LangChain/LangGraph para AulaTeX...' -ForegroundColor Cyan
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw 'Fallo la instalacion de dependencias LangChain/LangGraph.'
}

Write-Host 'Verificando paquetes instalados...' -ForegroundColor Cyan
& $venvPython -m pip show langchain langgraph langchain-openai langchain-anthropic
if ($LASTEXITCODE -ne 0) {
    throw 'La verificacion final de paquetes no fue satisfactoria.'
}

Write-Host 'Instalacion completada. AulaTeX usara .venv automaticamente.' -ForegroundColor Green