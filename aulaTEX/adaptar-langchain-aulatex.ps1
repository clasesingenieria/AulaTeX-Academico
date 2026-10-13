param(
    [switch]$Execute,
    [switch]$Monitor,
    [int]$Iterations = 100,
    [string]$Target = ".",
    [string[]]$Engine = @("Codex", "Claude Foundry", "GPT-Pro", "Auto (model-router)"),
    [int]$MaxTokens = 128000,
    [int]$TimeoutSeconds = 1800
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$tempRoot = Join-Path $repoRoot '.aulatex-temp\langchain-adaptation'
$logRoot = Join-Path $tempRoot 'logs'
$langchainRoot = Join-Path $PSScriptRoot 'aulatex\langchain'

New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

function Test-PythonPackage {
    param([string]$Package)
    $result = python -c "import importlib.util;print(importlib.util.find_spec('$Package') is not None)" 2>$null
    return ($result -match 'True')
}

function Initialize-LangChainProject {
    New-Item -ItemType Directory -Force -Path $langchainRoot | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $langchainRoot 'memory') | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $langchainRoot 'graphs') | Out-Null

    $graphPy = @'
from typing import TypedDict
from langgraph.graph import StateGraph, END
import json
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent.parent / "memory" / "editorial_memory.json"

class EditorialState(TypedDict, total=False):
    prompt: str
    proposals: list[str]
    fused: str

def load_memory():
    if MEMORY_FILE.exists():
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    return {"history": []}

def save_memory(data):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def consensus_node(state: EditorialState):
    proposals = state.get("proposals", [])
    unique = []
    for item in proposals:
        if item and item not in unique:
            unique.append(item)
    fused = "\n\n===== CONSENSO =====\n\n".join(unique)
    memory = load_memory()
    memory.setdefault("history", []).append(fused)
    save_memory(memory)
    return {"fused": fused}

def build_graph():
    graph = StateGraph(EditorialState)
    graph.add_node("consensus", consensus_node)
    graph.set_entry_point("consensus")
    graph.add_edge("consensus", END)
    return graph.compile()
'@

    $fusionPy = @'
from collections import Counter

def fuse_responses(responses:list[str]) -> str:
    cleaned=[r.strip() for r in responses if r and r.strip()]
    counts=Counter(cleaned)
    ranked=[text for text,_ in counts.most_common()]
    return "\n\n---FUSION---\n\n".join(ranked)
'@

    Set-Content -Path (Join-Path $langchainRoot 'graphs\aulatex_graph.py') -Value $graphPy -Encoding UTF8
    Set-Content -Path (Join-Path $langchainRoot 'fusion.py') -Value $fusionPy -Encoding UTF8
}

$langchainInstalled = Test-PythonPackage 'langchain'
$langgraphInstalled = Test-PythonPackage 'langgraph'

$EngineLimits = @{
    'Codex' = @{ Context = 400000; Input = 272000; Output = 128000 }
    'GPT-Pro' = @{ Context = 1050000; Input = 922000; Output = 128000 }
    'Claude Foundry' = @{ Context = 1000000; Input = 872000; Output = 128000 }
    'Auto (model-router)' = @{ Context = 200000; Input = 72000; Output = 128000; VariableOutput = $true }
}

$PromptMaxTokens = 4096

Initialize-LangChainProject

$previousTimeout = $env:AULATEX_LLM_TIMEOUT_SECONDS
$env:AULATEX_LLM_TIMEOUT_SECONDS = [string]$TimeoutSeconds

Write-Host 'AulaTeX + LangChain Adaptation Loop' -ForegroundColor Cyan
Write-Host "Iterations: $Iterations"
Write-Host "Target: $Target"
Write-Host "LangChain: $langchainInstalled"
Write-Host "LangGraph: $langgraphInstalled"
Write-Host "MaxTokens: $MaxTokens"
Write-Host "Limites oficiales AulaTeX cargados desde README"

if (-not $Execute) {
    Write-Host 'Plan generado. Ejecute con -Execute para iniciar la adaptación incremental.'
    return
}

if (-not $langgraphInstalled) {
    Write-Warning 'LangGraph no esta instalado. Se ejecutara en modo de compatibilidad.'
}

try {
    for ($i = 1; $i -le $Iterations; $i++) {
        $cycleLog = Join-Path $logRoot ("cycle-{0:D3}.log" -f $i)

        $prompt = @"
Objetivo: adaptar LangChain a los flujos AulaTeX.
Ciclo: $i de $Iterations.
Acciones:
- Analizar memoria editorial disponible.
- Proponer integración incremental compatible con LangChain.
- Fusionar hallazgos con el estado previo.
- No romper compatibilidad con CLI AulaTeX.
"@

        $responses = @()
        $engineFailures = @()
        foreach ($engineName in $Engine) {
            $engineLog = Join-Path $logRoot ("cycle-{0:D3}-{1}.log" -f $i, ($engineName -replace '[^A-Za-z0-9]','_'))
            $effectiveTokens = if ($EngineLimits.ContainsKey($engineName)) { $EngineLimits[$engineName].Output } else { $MaxTokens }
            $promptTokens = [Math]::Min($effectiveTokens, $PromptMaxTokens)
            $exitCode = 0
            try {
                python -m aulaTEX.aulatex.cli llm-prompt $prompt --engine $engineName --max-tokens $promptTokens --timeout-seconds $TimeoutSeconds *> $engineLog
                $exitCode = $LASTEXITCODE
            } catch {
                $exitCode = if ($LASTEXITCODE) { $LASTEXITCODE } else { 1 }
                $_ | Out-String | Add-Content -Path $engineLog -Encoding UTF8
            }

            if (Test-Path $engineLog) {
                $engineOutput = Get-Content $engineLog -Raw
                if ($exitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($engineOutput)) {
                    $responses += $engineOutput
                }
            }

            if ($exitCode -ne 0) {
                $engineFailures += [pscustomobject]@{
                    engine = $engineName
                    exit_code = $exitCode
                    log = $engineLog
                }
                Write-Warning ("Motor {0} fallo en el ciclo {1}. Revise {2}" -f $engineName, $i, $engineLog)
            }
        }

        if (-not $responses) {
            throw "Ningun motor produjo una respuesta valida en el ciclo $i. Revise los logs en $logRoot"
        }

        $fusionText = ($responses | Where-Object { $_ } | Select-Object -Unique) -join "`n`n---FUSION---`n`n"
        $fusionText | Set-Content $cycleLog -Encoding UTF8

        python -m aulaTEX.aulatex.cli agent `
            --target $Target `
            --action evaluar `
            --iterations 1 `
            --cycle-mode full `
            --no-compile `
            --engine $Engine[0] | Out-Null

        $fusionReport = @{
            cycle = $i
            timestamp = (Get-Date).ToString('s')
            strategy = 'multi-llm-code-fusion'
            engines = $Engine
            timeout_seconds = $TimeoutSeconds
            langchain = $langchainInstalled
            langgraph = $langgraphInstalled
            failed_engines = $engineFailures
            shared_memory = (Join-Path $langchainRoot 'memory')
            graph = (Join-Path $langchainRoot 'graphs\aulatex_graph.py')
        } | ConvertTo-Json -Depth 4

        $fusionReport | Set-Content (Join-Path $logRoot ("fusion-{0:D3}.json" -f $i)) -Encoding UTF8

        if ($Monitor) {
            $failedEngineNames = @($engineFailures | ForEach-Object { $_.engine })
            [pscustomobject]@{
                Cycle = $i
                Engines = $Engine.Count
                LangGraph = $langgraphInstalled
                FailedEngines = $failedEngineNames
                Timestamp = (Get-Date).ToString('s')
            } | ConvertTo-Json -Compress | Add-Content (Join-Path $logRoot 'monitor.jsonl')
        }

        Write-Host ("Ciclo completado {0}/{1}" -f $i, $Iterations)
    }
}
finally {
    if ($null -ne $previousTimeout) {
        $env:AULATEX_LLM_TIMEOUT_SECONDS = $previousTimeout
    }
    else {
        Remove-Item Env:AULATEX_LLM_TIMEOUT_SECONDS -ErrorAction SilentlyContinue
    }
}

Write-Host 'Adaptación LangChain finalizada.' -ForegroundColor Green