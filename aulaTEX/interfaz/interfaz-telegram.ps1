param(
    [switch]$Gui,
    [switch]$BootstrapOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

$repoRoot = (Resolve-Path (Split-Path -Parent $PSCommandPath)).Path
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
$requirementsFile = Join-Path $repoRoot 'requirements.txt'
$pidFile = Join-Path $repoRoot 'data\notas-bot.pid'
$logDir = Join-Path $repoRoot 'data\logs'
$stdoutLog = Join-Path $logDir 'notas-bot.out.log'
$stderrLog = Join-Path $logDir 'notas-bot.err.log'
$lockPort = 58731
if ($env:BOT_INSTANCE_LOCK_PORT) {
    $lockPort = [int]$env:BOT_INSTANCE_LOCK_PORT
}

function Get-NotasBotProcess {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object {
            $cmd = $_.CommandLine
            $cmd -and
            $cmd.IndexOf('-m interfaz.bot', [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
            $cmd.IndexOf($repoRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0
        }
}

function Get-PreferredBotPid {
    param([object[]]$Processes)

    $lockOwner = $null
    try {
        $lockOwner = Get-NetTCPConnection -LocalPort $lockPort -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty OwningProcess
    } catch {
        $lockOwner = $null
    }

    if ($lockOwner) {
        foreach ($botProcess in $Processes) {
            if ([int]$botProcess.ProcessId -eq [int]$lockOwner) {
                return [int]$lockOwner
            }
        }
    }

    if ($Processes.Count -gt 0) {
        return [int]($Processes | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId
    }

    return $null
}

function Get-BotBootstrapPython {
    $launchers = @(
        @{ Command = 'py'; Arguments = @('-3.14', '-c', 'import sys; print(sys.executable)') },
        @{ Command = 'py'; Arguments = @('-3', '-c', 'import sys; print(sys.executable)') },
        @{ Command = 'python'; Arguments = @('-c', 'import sys; print(sys.executable)') }
    )

    foreach ($launcher in $launchers) {
        $command = Get-Command $launcher.Command -ErrorAction SilentlyContinue
        if (-not $command) {
            continue
        }
        try {
            $output = & $command.Source @($launcher.Arguments) 2>$null
            if ($LASTEXITCODE -eq 0 -and $output) {
                return [string]($output | Select-Object -First 1)
            }
        } catch {
            continue
        }
    }

    throw 'No se encontro un interprete base para crear la .venv local del bot. Instala Python 3 y vuelve a intentar.'
}

function Test-BotDependencies {
    param([string]$PythonPath)

    if (-not (Test-Path $PythonPath)) {
        return $false
    }

    $imports = 'import telegram, dotenv, openai, requests, pypdf, docx, langchain, langgraph, langchain_openai, langchain_anthropic'
    $escapedImports = $imports.Replace('"', '\"')
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $PythonPath
    $startInfo.Arguments = "-c `"$escapedImports`""
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true

    $process = [System.Diagnostics.Process]::Start($startInfo)
    $process.WaitForExit()
    return ($process.ExitCode -eq 0)
}

function Initialize-BotEnvironment {
    if (-not (Test-Path $pythonExe)) {
        $bootstrapPython = Get-BotBootstrapPython
        Write-Host "Creando .venv local para bot-interfaz con: $bootstrapPython"
        & $bootstrapPython -m venv (Join-Path $repoRoot '.venv')
        if ($LASTEXITCODE -ne 0) {
            throw 'No se pudo crear la .venv local de bot-interfaz.'
        }
    }

    if (-not (Test-BotDependencies -PythonPath $pythonExe)) {
        Write-Host 'Instalando dependencias locales del bot...'
        & $pythonExe -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) {
            throw 'No se pudo actualizar pip en la .venv local del bot.'
        }
        & $pythonExe -m pip install -r $requirementsFile
        if ($LASTEXITCODE -ne 0) {
            throw 'No se pudieron instalar las dependencias de bot-interfaz.'
        }
    }

    if (-not (Test-BotDependencies -PythonPath $pythonExe)) {
        throw 'La .venv local del bot existe, pero las dependencias requeridas siguen incompletas.'
    }
}

Initialize-BotEnvironment

if ($BootstrapOnly) {
    Write-Host "Entorno local listo: $pythonExe"
    exit 0
}

if ($Gui -or $env:NOTAS_GUI_MODE -eq '1') {
    Write-Host "Iniciando interfaz grafica local (GUI)..."
    & $pythonExe -m src.gui
    exit $LASTEXITCODE
}

New-Item -ItemType Directory -Path (Split-Path -Parent $pidFile) -Force | Out-Null
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$runningBotProcesses = @(Get-NotasBotProcess)
if ($runningBotProcesses.Count -gt 0) {
    $existingPid = Get-PreferredBotPid -Processes $runningBotProcesses
    Set-Content -Path $pidFile -Value $existingPid -Encoding ascii
    Write-Host "El bot ya esta en ejecucion con PID $existingPid"
    exit 0
}

if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

$process = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList '-m', 'interfaz.bot' `
    -WorkingDirectory $repoRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 1

$runningBotProcesses = @(Get-NotasBotProcess)
if ($runningBotProcesses.Count -eq 0) {
    throw "El bot no quedo en ejecucion. Revisa el log: $stderrLog"
}

$startedPid = Get-PreferredBotPid -Processes $runningBotProcesses
if (-not $startedPid) {
    $startedPid = $process.Id
}

Set-Content -Path $pidFile -Value $startedPid -Encoding ascii

Write-Host "Bot iniciado. PID: $startedPid"
Write-Host "PID file: $pidFile"
Write-Host "Logs: $stdoutLog y $stderrLog"
