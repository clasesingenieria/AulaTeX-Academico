param(
    [switch]$Execute,
    [string]$Root = ".",
    [int]$ExpectedScopes = 459,
    [int]$Iterations = 2,
    [int]$MaxTokens = 4096,
    [int]$BatchSize = 1,
    [int]$MaxBatches = 0,
    [int]$TimeoutSeconds = 900,
    [int]$RetroDnaMaxChars = 700000,
    [int]$RetroFileMaxChars = 50000,
    [int]$HistoricalDnaPromptChars = 300000,
    [int]$CodexDnaPromptChars = 300000,
    [int]$ModelRouterDnaPromptChars = 300000,
    [int]$ClaudeDnaPromptChars = 300000,
    [int]$GptProDnaPromptChars = 300000,
    [int]$CodexMaxOutputTokens = 4096,
    [int]$ModelRouterMaxOutputTokens = 4096,
    [int]$ClaudeMaxOutputTokens = 4096,
    [int]$GptProMaxOutputTokens = 4096,
    [string[]]$Engine = @("Codex", "Auto (model-router)", "Claude Foundry"),
    [switch]$NoDeleteRetroalimentacion,
    [switch]$KeepTemp,
    [switch]$AllowDnaTruncation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$baseScript = Join-Path $PSScriptRoot 'prueeba-lote-ejecucion.ps1'
$tempRoot = Join-Path $repoRoot '.aulatex-temp'
$seedRoot = Join-Path $tempRoot 'editorial-memory\runs\legacy-retroalimentacion-seed'
$retroRoot = Join-Path $repoRoot 'aulaTEX/retroalimentacion-editorial'
$summaryPath = Join-Path $tempRoot 'editorial-memory\legacy-retroalimentacion-seed-summary.json'

if (-not (Test-Path $baseScript)) {
    throw "No se encontró script base: $baseScript"
}

if (Test-Path $tempRoot) {
    Remove-Item -Path $tempRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $seedRoot | Out-Null

$engineDnaPromptChars = @{
    'Codex' = $CodexDnaPromptChars
    'Auto (model-router)' = $ModelRouterDnaPromptChars
    'Claude Foundry' = $ClaudeDnaPromptChars
    'GPT-Pro' = $GptProDnaPromptChars
}
$selectedPromptBudgets = @($Engine | ForEach-Object { if ($engineDnaPromptChars.ContainsKey($_)) { [int]$engineDnaPromptChars[$_] } })
if ($selectedPromptBudgets.Count -gt 0) {
    $minSelectedPromptBudget = ($selectedPromptBudgets | Measure-Object -Minimum).Minimum
    $autoShardChars = [Math]::Max(50000, [int][Math]::Floor([double]$minSelectedPromptBudget * 0.85))
    if (-not $PSBoundParameters.ContainsKey('RetroDnaMaxChars')) {
        $RetroDnaMaxChars = $autoShardChars
    }
    elseif ($RetroDnaMaxChars -gt $autoShardChars) {
        Write-Host "Aviso: RetroDnaMaxChars=$RetroDnaMaxChars supera el presupuesto seguro calculado=$autoShardChars para los motores seleccionados." -ForegroundColor Yellow
    }
}

Write-Host "AulaTeX codificación final de retroalimentacion-editorial" -ForegroundColor Cyan
Write-Host "Repositorio: $repoRoot"
Write-Host "Modo: $(if ($Execute) { 'EJECUCION' } else { 'PLAN' })"
Write-Host "Nodos esperados: $ExpectedScopes"
Write-Host "Iteraciones por nodo: $Iterations"
Write-Host "Max tokens: $MaxTokens"
Write-Host "Retro DNA shard chars: $RetroDnaMaxChars"
Write-Host "DNA prompt chars por motor: Codex=$CodexDnaPromptChars; ModelRouter=$ModelRouterDnaPromptChars; Claude=$ClaudeDnaPromptChars; GPT-Pro=$GptProDnaPromptChars"
Write-Host "Max output tokens por motor: Codex=$CodexMaxOutputTokens; ModelRouter=$ModelRouterMaxOutputTokens; Claude=$ClaudeMaxOutputTokens; GPT-Pro=$GptProMaxOutputTokens"
Write-Host "Semillas temporales: $seedRoot"

$seedCode = @'
import hashlib
import json
import os
import re
import sys
from pathlib import Path

repo = Path(os.environ["AULATEX_REPO_ROOT"])
retro = Path(os.environ["AULATEX_RETRO_ROOT"])
seed_root = Path(os.environ["AULATEX_SEED_ROOT"])
summary_path = Path(os.environ["AULATEX_SUMMARY_PATH"])
expected = int(os.environ.get("AULATEX_EXPECTED_SCOPES", "0") or 0)
seed_root.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(repo))

from aulaTEX.aulatex.workspace import AulaTeXWorkspace

TEXT_EXTENSIONS = {".md", ".txt", ".json", ".bib", ".tex"}
SKIP_PARTS = {".git", "node_modules", "__pycache__", "editorial-memory"}
SHARD_CHARS = int(os.environ.get("AULATEX_RETRO_DNA_MAX_CHARS", "700000"))
MAX_FILE_CHARS = int(os.environ.get("AULATEX_RETRO_FILE_MAX_CHARS", "50000"))
ALLOW_TRUNCATION = os.environ.get("AULATEX_ALLOW_DNA_TRUNCATION", "0") == "1"
MAX_LINE_CHARS = 2_000


def safe_scope_slug(scope_key: str, max_prefix: int = 72) -> str:
    normalized = scope_key.replace("/", "__")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", normalized).strip("._")
    digest = hashlib.sha1(scope_key.encode("utf-8", errors="replace")).hexdigest()[:12]
    if len(safe) > max_prefix:
        safe = safe[:max_prefix].rstrip("._-")
    return f"{safe}--{digest}"


def useful_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_CHARS]
    lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        if len(line) < 18 and not line.startswith(("#", "-", "*")):
            continue
        if line.startswith("```"):
            continue
        line = line[:MAX_LINE_CHARS]
        line = line.lstrip("#-* ").strip()
        if line:
            lines.append(line)
    return lines

workspace = AulaTeXWorkspace(repo)
scopes = workspace.scan_editorial_scopes()
if expected and len(scopes) != expected:
    raise SystemExit(f"Inventario inesperado: {len(scopes)} scopes detectados, se esperaban {expected}.")

source_files = []
if retro.exists():
    for path in sorted(retro.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        source_files.append(path)

items: list[str] = []
seen = set()
for path in source_files:
    rel = path.relative_to(repo).as_posix()
    for line in useful_lines(path):
        item = f"{rel}: {line}"
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(item)

header = [
    "## retroalimentacion_editorial_central",
    "- Objetivo: codificar la carpeta retroalimentacion-editorial como ADN editorial distribuido.",
    "- Regla: integrar patrones útiles en cada nodo sin conservar una memoria centralizada permanente.",
    "- Regla: después de una ejecución completa y validada, las salidas pueden eliminarse; la auditoría versionada se conserva.",
]
shards: list[str] = []
current = list(header)
current_chars = sum(len(line) + 1 for line in current)
for item in items:
    line = f"- {item}"
    line_size = len(line) + 1
    if current_chars + line_size > SHARD_CHARS and len(current) > len(header):
        shards.append("\n".join(current) + "\n")
        current = list(header)
        current_chars = sum(len(line) + 1 for line in current)
    current.append(line)
    current_chars += line_size
if len(current) > len(header):
    shards.append("\n".join(current) + "\n")
if not shards:
    shards.append("\n".join(header) + "\n")

created = 0
for scope in scopes:
    slug = safe_scope_slug(scope.key)
    for index, seed_text in enumerate(shards, start=1):
        target = seed_root / f"0000-{slug}-Retroalimentacion_Central_shard-{index:03d}.md"
        target.write_text(seed_text, encoding="utf-8")
        created += 1

summary = {
    "scope_count": len(scopes),
    "seed_files": created,
    "seed_shards_per_scope": len(shards),
    "retro_source_files": len(source_files),
    "seed_items": len(items),
    "seed_chars_total": sum(len(text) for text in shards),
    "truncated": False,
    "shard_chars": SHARD_CHARS,
    "max_file_chars": MAX_FILE_CHARS,
    "seed_root": str(seed_root),
}
summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
'@

$env:AULATEX_REPO_ROOT = [string]$repoRoot
$env:AULATEX_RETRO_ROOT = [string]$retroRoot
$env:AULATEX_SEED_ROOT = [string]$seedRoot
$env:AULATEX_SUMMARY_PATH = [string]$summaryPath
$env:AULATEX_EXPECTED_SCOPES = [string]$ExpectedScopes
$env:AULATEX_HISTORICAL_DNA_PROMPT_CHARS = [string]$HistoricalDnaPromptChars
$env:AULATEX_HISTORICAL_DNA_PROMPT_CHARS_CODEX = [string]$CodexDnaPromptChars
$env:AULATEX_HISTORICAL_DNA_PROMPT_CHARS_MODEL_ROUTER = [string]$ModelRouterDnaPromptChars
$env:AULATEX_HISTORICAL_DNA_PROMPT_CHARS_ANTHROPIC_FOUNDRY = [string]$ClaudeDnaPromptChars
$env:AULATEX_HISTORICAL_DNA_PROMPT_CHARS_GPT_PRO = [string]$GptProDnaPromptChars
$env:AULATEX_MAX_OUTPUT_TOKENS_CODEX = [string]$CodexMaxOutputTokens
$env:AULATEX_MAX_OUTPUT_TOKENS_MODEL_ROUTER = [string]$ModelRouterMaxOutputTokens
$env:AULATEX_MAX_OUTPUT_TOKENS_ANTHROPIC_FOUNDRY = [string]$ClaudeMaxOutputTokens
$env:AULATEX_MAX_OUTPUT_TOKENS_GPT_PRO = [string]$GptProMaxOutputTokens
$env:AULATEX_RETRO_DNA_MAX_CHARS = [string]$RetroDnaMaxChars
$env:AULATEX_RETRO_FILE_MAX_CHARS = [string]$RetroFileMaxChars
$env:AULATEX_ALLOW_DNA_TRUNCATION = if ($AllowDnaTruncation) { '1' } else { '0' }
$seedScript = Join-Path $tempRoot 'editorial-memory\build-retroalimentacion-seeds.py'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $seedScript) | Out-Null
$seedCode | Set-Content -Path $seedScript -Encoding UTF8
python $seedScript
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron construir las semillas temporales de retroalimentación."
}

if (-not $Execute) {
    Write-Host ""
    Write-Host "Plan preparado. Para ejecutar codificación final:"
    Write-Host "  .\aulaTEX\prueeba-lote-ejecucion-1.ps1 -Execute"
    Write-Host ""
    Write-Host "No se eliminaron salidas de aulaTEX/retroalimentacion-editorial porque no se ejecutó el lote."
    return
}

$baseParams = @{
    Execute = $true
    Root = $Root
    Levels = 'all'
    PropagationMode = 'local'
    Iterations = $Iterations
    BatchSize = $BatchSize
    MaxBatches = $MaxBatches
    MaxTokens = $MaxTokens
    TimeoutSeconds = $TimeoutSeconds
    CheckpointName = 'codificacion-retroalimentacion-adn'
    Engine = $Engine
}

& $baseScript @baseParams
if ($LASTEXITCODE -ne 0) {
    throw "La codificación distribuida falló. Se conserva retroalimentacion-editorial para diagnóstico."
}

$validateCode = @'
import json
import re
from pathlib import Path
import os

repo = Path(os.environ["AULATEX_REPO_ROOT"])
temp = repo / ".aulatex-temp" / "editorial-memory" / "batch-plans"
expected = int(os.environ.get("AULATEX_EXPECTED_SCOPES", "0") or 0)
pattern = re.compile(r'\[(.*?)\] MONITOR (.*?) completed=(\w+) manifestOk=(\w+) cycles=(\d+) cycleOk=(\d+) fusedFiles=(\d+) cycleClusters=(\d+) historicalClusters=(\d+) historicalSources=(\d+)')
latest = {}
for log in sorted(temp.glob("*-prueeba-lote-ejecucion.log")):
    text = log.read_text(encoding="utf-16", errors="ignore")
    if "MONITOR" not in text:
        text = log.read_text(encoding="utf-8", errors="ignore")
    for match in pattern.finditer(text):
        scope = match.group(2)
        data = {
            "timestamp": match.group(1),
            "scope": scope,
            "completed": match.group(3) == "True",
            "cycles": int(match.group(5)),
            "cycleOk": int(match.group(6)),
            "fusedFiles": int(match.group(7)),
            "cycleClusters": int(match.group(8)),
            "historicalClusters": int(match.group(9)),
            "historicalSources": int(match.group(10)),
            "log": str(log),
        }
        if scope not in latest or data["timestamp"] > latest[scope]["timestamp"]:
            latest[scope] = data
bad = [item for item in latest.values() if not item["completed"] or item["cycleOk"] < 1 or item["fusedFiles"] < 1 or item["cycleClusters"] < 1 or item["historicalClusters"] < 1]
summary = {
    "unique_scopes_monitored": len(latest),
    "expected_scopes": expected,
    "bad_latest": len(bad),
    "cycleOk_total_latest": sum(item["cycleOk"] for item in latest.values()),
    "cycleClusters_total_latest": sum(item["cycleClusters"] for item in latest.values()),
    "historicalClusters_total_latest": sum(item["historicalClusters"] for item in latest.values()),
    "historicalSources_total_latest": sum(item["historicalSources"] for item in latest.values()),
    "bad_scopes": bad[:20],
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
if len(latest) != expected or bad:
    raise SystemExit(2)
'@

$validateScript = Join-Path $tempRoot 'editorial-memory\validate-retroalimentacion-codificacion.py'
$validateCode | Set-Content -Path $validateScript -Encoding UTF8
$validationJson = python $validateScript
if ($LASTEXITCODE -ne 0) {
    $validationJson | Write-Host
    throw "La validación final no pasó. Se conserva retroalimentacion-editorial."
}
$validationJson | Write-Host

if (-not $NoDeleteRetroalimentacion -and (Test-Path $retroRoot)) {
    $historicalAudit = Join-Path $retroRoot 'aulatex/limpieza-temporales-2026-10-10'
    $feedbackDir = Join-Path $retroRoot 'aulatex'
    if (Test-Path $feedbackDir) {
        Get-ChildItem -LiteralPath $feedbackDir -Force |
            Where-Object { $_.FullName -ne $historicalAudit } |
            Remove-Item -Recurse -Force
    }
    Write-Host "Salidas editoriales eliminadas; auditoría histórica conservada: $historicalAudit" -ForegroundColor Green
}
else {
    Write-Host "Carpeta central conservada por configuración: $retroRoot" -ForegroundColor Yellow
}

if (-not $KeepTemp -and (Test-Path $tempRoot)) {
    Remove-Item -Path $tempRoot -Recurse -Force
    Write-Host "Temporales eliminados: $tempRoot" -ForegroundColor Green
}
