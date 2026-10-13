param(
    [string[]]$Model = @(),
    [int]$InputTimeoutSeconds = 120,
    [int]$OutputTimeoutSeconds = 120,
    [int]$MaxReductions = 8,
    [int]$RefineSteps = 4,
    [string]$OutputRoot = '.aulatex-temp/deployment-limit-probe'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { 'python' }
$entry = Join-Path $PSScriptRoot 'deployment_limit_probe.py'

$argsList = @(
    $entry,
    '--input-timeout-seconds', [string]$InputTimeoutSeconds,
    '--output-timeout-seconds', [string]$OutputTimeoutSeconds,
    '--max-reductions', [string]$MaxReductions,
    '--refine-steps', [string]$RefineSteps,
    '--output-root', $OutputRoot
)

foreach ($modelId in $Model) {
    $argsList += @('--model', $modelId)
}

& $pythonCmd @argsList
exit $LASTEXITCODE