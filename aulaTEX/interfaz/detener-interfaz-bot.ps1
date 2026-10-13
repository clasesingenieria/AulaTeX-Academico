Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $repoRoot 'data\notas-bot.pid'

function Get-NotasBotProcess {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object {
            $cmd = $_.CommandLine
            $cmd -and
            $cmd.IndexOf('-m src.bot', [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
            $cmd.IndexOf($repoRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0
        }
}

$processIds = New-Object 'System.Collections.Generic.HashSet[int]'
if (Test-Path $pidFile) {
    $storedPid = (Get-Content $pidFile -Raw).Trim()
    if ($storedPid) {
        [void]$processIds.Add([int]$storedPid)
    }
}

foreach ($botProcess in @(Get-NotasBotProcess)) {
    [void]$processIds.Add([int]$botProcess.ProcessId)
}

if ($processIds.Count -eq 0) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host 'El bot no parece estar ejecutandose.'
    exit 0
}

foreach ($processId in $processIds) {
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Milliseconds 500

foreach ($botProcess in @(Get-NotasBotProcess)) {
    Stop-Process -Id $botProcess.ProcessId -Force -ErrorAction SilentlyContinue
}

Remove-Item $pidFile -Force -ErrorAction SilentlyContinue

Write-Host "Bot detenido. Procesos: $($processIds -join ', ')"
