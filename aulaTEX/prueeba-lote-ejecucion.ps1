param(
    [switch]$Execute,
    [string]$Root = ".",
    [ValidateSet("actividad", "materia", "carrera", "institucion", "interinstitucional", "all")]
    [string]$Levels = "all",
    [ValidateSet("local", "ascendente", "ascendente-exhaustivo", "recursivo")]
    [string]$PropagationMode = "local",
    [int]$Iterations = 1,
    [int]$BatchSize = 1,
    [int]$MaxBatches = 0,
    [int]$MaxTokens = 8192,
    [int]$TimeoutSeconds = 300,
    [string[]]$Engine = @("Codex", "Auto (model-router)", "Claude Foundry", "GPT-Pro"),
    [string]$CheckpointName = "workspace-memory-unification",
    [switch]$IncludeInterinstitucional,
    [switch]$CleanTemp,
    [switch]$CleanAfter
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$entry = Join-Path $PSScriptRoot 'aulatex_agent.py'
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { 'python' }
$tempRoot = Join-Path $repoRoot '.aulatex-temp'
$planDir = Join-Path $tempRoot 'editorial-memory\batch-plans'
if ($CleanTemp -and (Test-Path $tempRoot)) {
    Remove-Item -Path $tempRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $planDir | Out-Null

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$planPath = Join-Path $planDir "$timestamp-prueeba-lote-ejecucion.json"
$logPath = Join-Path $planDir "$timestamp-prueeba-lote-ejecucion.log"

$levelOrder = @('actividad', 'materia', 'carrera', 'institucion', 'interinstitucional')
if ($Levels -ne 'all') {
    $levelOrder = @($Levels)
}
elseif (-not $IncludeInterinstitucional) {
    # Compatibilidad: antes este switch activaba el nodo global; ahora all ya cubre todo el workspace.
    $IncludeInterinstitucional = $true
}

Write-Host "AulaTeX lote de memoria" -ForegroundColor Cyan
Write-Host "Repositorio: $repoRoot"
Write-Host "Modo: $(if ($Execute) { 'EJECUCION' } else { 'PLAN' })"
Write-Host "Raiz: $Root"
Write-Host "Niveles: $($levelOrder -join ', ')"
Write-Host "Propagacion: $PropagationMode"
Write-Host "Iteraciones: $Iterations"
Write-Host "BatchSize: $BatchSize | MaxBatches: $MaxBatches"
Write-Host "Plan: $planPath"
Write-Host "Log: $logPath"

$pythonCode = @'
import json
import os
import sys
from pathlib import Path

root = os.environ.get("AULATEX_BATCH_ROOT", ".")
levels = [item for item in os.environ.get("AULATEX_BATCH_LEVELS", "").split(";") if item]
repo = Path(os.environ["AULATEX_REPO_ROOT"])
sys.path.insert(0, str(repo))
from aulaTEX.aulatex.workspace import AulaTeXWorkspace
workspace = AulaTeXWorkspace(repo)
start = workspace.find_scope_for_target(root)
if start is None:
    raise SystemExit(f"No se pudo resolver scope para {root}")
all_scopes = workspace.scan_editorial_scopes()
start_path = start.relative_path
selected = []
for scope in all_scopes:
    if scope.level not in levels:
        continue
    if start.key == "interinstitucional":
        include = True
    elif scope.key == start.key:
        include = True
    elif start_path and scope.relative_path:
        include = scope.relative_path == start_path or scope.relative_path.startswith(start_path + "/")
    else:
        include = scope.key.startswith(start.key + "/")
    if include:
        selected.append(scope)
order = {level: index for index, level in enumerate(levels)}
selected.sort(key=lambda scope: (order.get(scope.level, 999), scope.key))
print(json.dumps({
    "root": root,
    "source_scope": start.key,
    "source_level": start.level,
    "count": len(selected),
    "scopes": [
        {
            "key": scope.key,
            "level": scope.level,
            "label": scope.label,
            "relative_path": scope.relative_path,
            "activity": scope.activity,
        }
        for scope in selected
    ],
}, ensure_ascii=False, indent=2))
'@

$env:AULATEX_REPO_ROOT = [string]$repoRoot
$env:AULATEX_BATCH_ROOT = $Root
$env:AULATEX_BATCH_LEVELS = ($levelOrder -join ';')
$pythonPlanPath = Join-Path $planDir "$timestamp-prueeba-lote-plan.py"
$pythonCode | Set-Content -Path $pythonPlanPath -Encoding UTF8
$planJson = python $pythonPlanPath
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo construir el plan de lote."
}
$planJson | Set-Content -Path $planPath -Encoding UTF8
Remove-Item -Path $pythonPlanPath -Force -ErrorAction SilentlyContinue
$plan = $planJson | ConvertFrom-Json

Write-Host "Scopes planificados: $($plan.count)" -ForegroundColor Green
$plan.scopes | ForEach-Object {
    Write-Host ("- {0} | {1} | {2}" -f $_.level, $_.key, $_.relative_path)
}

if (-not $Execute) {
    Write-Host ""
    Write-Host "Plan generado. Para ejecutar:"
    Write-Host "  .\aulaTEX\prueeba-lote-ejecucion.ps1 -Execute"
    Write-Host ""
    Write-Host "Sugerencia: empieza con -BatchSize 1 -MaxBatches 1 para validar una corrida controlada."
    return
}

$completed = 0
$failed = 0
foreach ($scope in $plan.scopes) {
    $target = [string]$scope.relative_path
    if ([string]::IsNullOrWhiteSpace($target)) {
        $target = "."
    }

    $hashInput = [System.Text.Encoding]::UTF8.GetBytes([string]$scope.key)
    $hash = [System.BitConverter]::ToString([System.Security.Cryptography.SHA1]::Create().ComputeHash($hashInput)).Replace('-', '').Substring(0, 12).ToLowerInvariant()
    $checkpointId = "$CheckpointName-$($scope.level)-$hash"

    $commandArgs = @(
        'editorial-memory',
        '--target', $target,
        '--build-level', ([string]$scope.level),
        '--propagation-mode', $PropagationMode,
        '--iterations', ([string]$Iterations),
        '--max-tokens', ([string]$MaxTokens),
        '--timeout-seconds', ([string]$TimeoutSeconds),
        '--batch-size', ([string]$BatchSize),
        '--checkpoint', $checkpointId
    )
    if ($MaxBatches -gt 0) {
        $commandArgs += @('--max-batches', ([string]$MaxBatches))
    }
    foreach ($item in $Engine) {
        if (-not [string]::IsNullOrWhiteSpace($item)) {
            $commandArgs += @('--engine', $item)
        }
    }
    if ($scope.level -eq 'actividad' -and -not [string]::IsNullOrWhiteSpace([string]$scope.activity)) {
        $number = ([regex]::Match([string]$scope.activity, '\d+')).Value
        if ($number) {
            $commandArgs += @('--activity', $number)
        }
    }

    $line = "[$(Get-Date -Format o)] EJECUTA $($scope.level) $($scope.key) :: $($commandArgs -join ' ')"
    $line | Tee-Object -FilePath $logPath -Append
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $rawOutput = & $pythonCmd $entry @commandArgs 2>&1
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    $rawOutput | Tee-Object -FilePath $logPath -Append
    if ($exitCode -ne 0) {
        $failed += 1
        "[$(Get-Date -Format o)] ERROR en $($scope.key) con codigo $exitCode" | Tee-Object -FilePath $logPath -Append
        break
    }

    $jsonText = ($rawOutput | Out-String)
    $match = [regex]::Match($jsonText, '(?s)\{\s*"ok".*\}\s*$')
    if (-not $match.Success) {
        $failed += 1
        "[$(Get-Date -Format o)] ERROR en $($scope.key): no se pudo leer JSON de salida." | Tee-Object -FilePath $logPath -Append
        break
    }

    $result = $match.Value | ConvertFrom-Json
    $manifestPath = [string]$result.last_manifest
    if ([string]::IsNullOrWhiteSpace($manifestPath) -or -not (Test-Path $manifestPath)) {
        $failed += 1
        "[$(Get-Date -Format o)] ERROR en $($scope.key): manifiesto no encontrado." | Tee-Object -FilePath $logPath -Append
        break
    }

    $manifest = Get-Content -Path $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $runDir = Split-Path -Parent $manifestPath
    $fusedDir = Join-Path $runDir 'fused-memory'
    $fusedFiles = @()
    if (Test-Path $fusedDir) {
        $fusedFiles = @(Get-ChildItem -Path $fusedDir -Filter '*.json' -File)
    }
    $cycleClusters = 0
    foreach ($fusedFile in $fusedFiles) {
        $fusedPayload = Get-Content -Path $fusedFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($null -ne $fusedPayload.cluster_count) {
            $cycleClusters += [int]$fusedPayload.cluster_count
        }
    }
    $safeScopeSlug = ([string]$scope.key -replace '/', '__') -replace '[^A-Za-z0-9_.-]+', '_'
    $safeScopeSlug = $safeScopeSlug.Trim('._')
    if ($safeScopeSlug.Length -gt 72) {
        $safeScopeSlug = $safeScopeSlug.Substring(0, 72).Trim('._-')
    }
    $safeScopeSlug = "$safeScopeSlug--$hash"
    $dnaPath = Join-Path $repoRoot ('.build\editorial-dna\' + $safeScopeSlug + '--historical-dna.json')
    $legacyDnaPath = Join-Path $repoRoot ('.build\editorial-dna\' + ([string]$scope.key -replace '/', '__') + '--historical-dna.json')
    if ((-not (Test-Path $dnaPath)) -and (Test-Path $legacyDnaPath)) {
        $dnaPath = $legacyDnaPath
    }
    $historicalClusters = 0
    $historicalSources = 0
    if (Test-Path $dnaPath) {
        $dnaPayload = Get-Content -Path $dnaPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($null -ne $dnaPayload.cluster_count) {
            $historicalClusters = [int]$dnaPayload.cluster_count
        }
        if ($null -ne $dnaPayload.source_files) {
            $historicalSources = @($dnaPayload.source_files).Count
        }
    }

    $cycleOk = @($manifest.cycles | Where-Object { $_.ok -eq $true }).Count
    $monitorLine = "[$(Get-Date -Format o)] MONITOR $($scope.key) completed=$($result.completed) manifestOk=$($manifest.ok) cycles=$(@($manifest.cycles).Count) cycleOk=$cycleOk fusedFiles=$($fusedFiles.Count) cycleClusters=$cycleClusters historicalClusters=$historicalClusters historicalSources=$historicalSources"
    $monitorLine | Tee-Object -FilePath $logPath -Append

    if (($result.completed -ne $true) -or ($fusedFiles.Count -lt 1) -or ($cycleClusters -lt 1) -or ($cycleOk -lt 1)) {
        $failed += 1
        "[$(Get-Date -Format o)] ERROR en $($scope.key): ciclo incompleto, sin LLM exitoso o sin fusión de memoria útil." | Tee-Object -FilePath $logPath -Append
        break
    }

    $completed += 1
}

Write-Host "Lote terminado. Completados: $completed | Fallidos: $failed" -ForegroundColor Cyan
Write-Host "Plan: $planPath"
Write-Host "Log: $logPath"

if ($CleanAfter -and $failed -eq 0 -and (Test-Path $tempRoot)) {
    Remove-Item -Path $tempRoot -Recurse -Force
    Write-Host "Temporales eliminados: $tempRoot" -ForegroundColor Green
}
