<#
.SYNOPSIS
  Orquesta los 100 ciclos de realizar-actividad del motor-inteligente para la
  Actividad 2 de Derecho a la Seguridad Social en LOTES OBSERVABLES con watchdog.

.DESCRIPTION
  El flujo `agent --cycle-mode full --iterations 100` es vulnerable a cuelgues de
  red sin timeout (documentado en activity_contract.iterative_improvement_rules).
  Este orquestador lo divide en lotes pequeños, cada uno como un Job con timeout
  (watchdog). Si un lote se cuelga, se detiene y continúa con el siguiente, de
  modo que el avance es observable y resistente a cuelgues.

.NOTES
  Cada lote escribe su propio run en retroalimentacion-editorial/aulatex/runs.
  El progreso agregado se registra en el log de progreso.
#>
param(
    [ValidateRange(1, 10000)][int]$TotalCycles = 100,
    [ValidateRange(1, 100)][int]$BatchSize = 5,
    [ValidateRange(1, 3600)][int]$LlmTimeoutSeconds = 120,
    [ValidateRange(1, 200000)][int]$LlmMaxTokens = 6000,
    [ValidateRange(30, 86400)][int]$BatchWatchdogSeconds = 1500,
    [ValidateRange(1, 100)][int]$MaxBatchRetries = 5,
    [int]$Activity = 2,
    [string]$LogName = 'act2-100ciclos',
    [string]$Target = '.\UnADM\licenciatura-en-derecho-unadm\derecho-a-la-seguridad-social-lde\reporte-derecho-a-la-seguridad-social-Actividad-1.tex',
    [switch]$Resume
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$logDir = Join-Path $root ".aulatex-temp\$LogName"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$progressLog = Join-Path $logDir 'progreso-lotes.log'
$lockPath = Join-Path $logDir 'execution.lock'
$engines = @('GPT-5.6-SOL', 'GPT-5.6-Luna', 'GPT-5.6-Terra')

if (-not (Test-Path (Join-Path $root '.venv\Scripts\python.exe'))) {
    throw 'No se encontró .venv\Scripts\python.exe.'
}
if (-not (Test-Path $Target)) {
    throw "No se encontró el destino: $Target"
}
if ([string]::IsNullOrWhiteSpace($env:AULATEX_MASTER_PIN)) {
    throw 'AULATEX_MASTER_PIN no está definido en la sesión.'
}

$lockStream = $null
try {
    $lockStream = [System.IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None')
}
catch {
    throw "Ya existe una ejecución activa para '$LogName'."
}

$batches = [math]::Ceiling($TotalCycles / $BatchSize)
$completedCycles = 0
if ($Resume -and (Test-Path $progressLog)) {
    $progressMatches = Select-String -Path $progressLog -Pattern 'acumulado=(\d+)/' -AllMatches
    $values = @($progressMatches | ForEach-Object { $_.Matches } | ForEach-Object { [int]$_.Groups[1].Value })
    if ($values.Count -gt 0) { $completedCycles = ($values | Measure-Object -Maximum).Maximum }
}
$startedAt = Get-Date

function Write-Progress-Line([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg
    Write-Host $line
    Add-Content -Path $progressLog -Value $line -Encoding UTF8
}

Write-Progress-Line "INICIO/REANUDACIÓN: objetivo=$TotalCycles, completados=$completedCycles, lotes=$batches, tamaño=$BatchSize (LLM timeout=$LlmTimeoutSeconds s, max_tokens=$LlmMaxTokens, watchdog=$BatchWatchdogSeconds s)"

try {
    $batchNumber = [math]::Floor($completedCycles / $BatchSize) + 1
    while ($completedCycles -lt $TotalCycles) {
        $remaining = $TotalCycles - $completedCycles
        $thisBatch = [math]::Min($BatchSize, $remaining)
        $attempt = 0
        $batchSucceeded = $false

        while (-not $batchSucceeded -and $attempt -lt $MaxBatchRetries) {
            $attempt++
            Write-Progress-Line "LOTE $batchNumber/$batches intento $attempt/$MaxBatchRetries -> ejecutando $thisBatch ciclos (acumulado previo: $completedCycles)"

            # Start-Job no hereda el PIN; se transmite solo a la sesión hija.
            $job = Start-Job -ScriptBlock {
                param($r, $tgt, $iters, $llmTo, $llmMax, $eng, $act, $pin)
                Set-Location $r
                $env:AULATEX_MASTER_PIN = $pin
                $env:AULATEX_LLM_TIMEOUT_SECONDS = "$llmTo"
                $env:AULATEX_LLM_MAX_TOKENS = "$llmMax"
                $env:PYTHONUTF8 = '1'
                $env:TOKENIZERS_PARALLELISM = 'false'
                $engineArgs = @()
                foreach ($e in $eng) { $engineArgs += '--engine'; $engineArgs += $e }
                & '.\.venv\Scripts\python.exe' '.\aulaTEX\aulatex_agent.py' agent `
                    --action realizar-actividad --target $tgt --activity $act `
                    --iterations $iters --cycle-mode full --no-compile --no-detail-planner `
                    @engineArgs 2>&1
                $exitCode = $LASTEXITCODE
                [pscustomobject]@{ AulaTeXExitCode = $exitCode }
            } -ArgumentList $root, $Target, $thisBatch, $LlmTimeoutSeconds, $LlmMaxTokens, $engines, $Activity, $env:AULATEX_MASTER_PIN

            $done = Wait-Job $job -Timeout $BatchWatchdogSeconds
            $out = @()
            if ($done) {
                # Las respuestas HTTP de error llegan como ErrorRecord; deben registrarse,
                # no terminar al orquestador antes de evaluar el código de salida.
                $out = @(Receive-Job $job -ErrorAction Continue -ErrorVariable receiveErrors)
                $exitRecord = $out | Where-Object { $_.PSObject.Properties.Name -contains 'AulaTeXExitCode' } | Select-Object -Last 1
                $exitCode = if ($null -ne $exitRecord) { [int]$exitRecord.AulaTeXExitCode } else { 1 }
                $tail = (@($out | Where-Object { $_ -ne $exitRecord }) + @($receiveErrors) | Select-Object -Last 5) -join ' | '
                if ($exitCode -eq 0) {
                    $completedCycles += $thisBatch
                    $batchSucceeded = $true
                    Write-Progress-Line "LOTE $batchNumber OK. acumulado=$completedCycles/$TotalCycles. cola: $tail"
                }
                else {
                    Write-Progress-Line "LOTE $batchNumber FALLÓ (exit=$exitCode). Reintento pendiente. cola: $tail"
                }
            }
            else {
                Stop-Job $job -ErrorAction SilentlyContinue
                Write-Progress-Line "LOTE $batchNumber TIMEOUT (watchdog $BatchWatchdogSeconds s). Reintento pendiente."
                # Solo termina los procesos del mismo destino, sin afectar otras materias.
                Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
                    Where-Object { $_.CommandLine -like "*$Target*" } |
                    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
            }
            Remove-Job $job -Force -ErrorAction SilentlyContinue
        }

        if (-not $batchSucceeded) {
            throw "El lote $batchNumber agotó $MaxBatchRetries intentos; se conserva el progreso para reanudar."
        }
        $batchNumber++
    }

    $elapsed = [math]::Round(((Get-Date) - $startedAt).TotalMinutes, 1)
    Write-Progress-Line "FIN. ciclos completados=$completedCycles/$TotalCycles en $elapsed min."
}
catch {
    Write-Progress-Line "INTERRUMPIDO. ciclos completados=$completedCycles/$TotalCycles. error=$($_.Exception.Message)"
    throw
}
finally {
    if ($null -ne $lockStream) { $lockStream.Dispose() }
    Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
}
