<#
.SYNOPSIS
Orquestador cíclico UCNL para memoria editorial, TEX y PDF.

.DESCRIPTION
Audita UCNL y ejecuta ciclos controlados inspirados en aulaTEX/prueeba-lote-ejecucion-1.ps1:
1. auditoría memoria editorial <-> TEX <-> PDF;
2. refuerzo de nodos de memoria editorial con LLM/AulaTeX;
3. mejora de reportes con activity-monitor/activity-revise;
4. mejora de presentaciones al estilo IIIEPE/UnADM mediante prompt LLM y artefactos de parche;
5. compilación final de TEX/PDF;
6. nueva auditoría por ciclo.

Este script no borra retroalimentacion-editorial. Las ediciones de presentaciones se generan como planes/patches
cuando no existe todavía un subcomando AulaTeX especializado para aplicar Beamer avanzado.
#>
[CmdletBinding()]
param(
    [string]$Root = "UCNL",
    [string]$OutputDir = ".aulatex-temp\ucnl-editorial-cycle",
    [int]$Cycles = 1,
    [switch]$Execute,
    [switch]$Apply,
    [switch]$RunMemory,
    [switch]$RunReports,
    [switch]$RunPresentations,
    [switch]$Compile,
    [int]$MaxMemoryNodes = 8,
    [int]$MaxReportNodes = 8,
    [int]$MaxPresentationNodes = 8,
    [int]$MaxCompileNodes = 80,
    [int]$EditorialBatchSize = 1,
    [int]$EditorialMaxBatches = 1,
    [int]$Iterations = 2,
    [int]$MaxTokens = 4096,
    [int]$TimeoutSeconds = 900,
    [string[]]$Engine = @("Codex", "Auto (model-router)", "Claude Foundry"),
    [string]$ReferencePresentationIIIEPE = "aulaTEX/base/latex/adaptadas/instituciones/iiiepe/plantilla-presentacion-iiiepe.tex",
    [string]$ReferencePresentationUnADM = "UnADM/presentacion-unadm.tex"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $RepoRoot

$RootPath = Resolve-Path $Root
$OutputPath = Join-Path $RepoRoot $OutputDir
New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null

$AulaTeX = Join-Path $RepoRoot 'aulaTEX\aulatex.ps1'
$LatexBuild = Join-Path $RepoRoot 'aulaTEX\latexmk-build.ps1'
$BatchMemoryScript = Join-Path $RepoRoot 'aulaTEX\prueeba-lote-ejecucion.ps1'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$CycleRoot = Join-Path $OutputPath "run-$Stamp"
$AgentLogDir = Join-Path $CycleRoot 'agent-logs'
$PatchDir = Join-Path $CycleRoot 'patches'
New-Item -ItemType Directory -Path $AgentLogDir,$PatchDir -Force | Out-Null

function Get-RelativePath {
    param([Parameter(Mandatory)][string]$Path)
    $full = [System.IO.Path]::GetFullPath($Path)
    $rootFull = [System.IO.Path]::GetFullPath($RepoRoot)
    if (-not $rootFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $rootFull = $rootFull + [System.IO.Path]::DirectorySeparatorChar
    }
    $rootUri = New-Object System.Uri($rootFull)
    $fullUri = New-Object System.Uri($full)
    return [System.Uri]::UnescapeDataString($rootUri.MakeRelativeUri($fullUri).ToString()).Replace('/', [System.IO.Path]::DirectorySeparatorChar).Replace('\', '/')
}

function Read-JsonFile {
    param([Parameter(Mandatory)][string]$Path)
    try { return Get-Content -Raw -Encoding UTF8 $Path | ConvertFrom-Json -ErrorAction Stop }
    catch { return $null }
}

function Get-SafeLogName {
    param([Parameter(Mandatory)][string]$Name)
    $safe = ($Name -replace '[^A-Za-z0-9_.-]', '_')
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Name)
    $hash = [System.BitConverter]::ToString([System.Security.Cryptography.SHA1]::Create().ComputeHash($bytes)).Replace('-', '').Substring(0, 10).ToLowerInvariant()
    if ($safe.Length -gt 96) { $safe = $safe.Substring(0, 96).Trim('._-') }
    return "$safe--$hash"
}

function Invoke-LoggedCommand {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments
    )
    $safe = Get-SafeLogName $Name
    $out = Join-Path $AgentLogDir "$safe.out.log"
    $err = Join-Path $AgentLogDir "$safe.err.log"
    Push-Location $RepoRoot
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $FilePath @Arguments > $out 2> $err
        $exitCode = $LASTEXITCODE
        if ($null -eq $exitCode) { $exitCode = 0 }
    }
    catch {
        $exitCode = 1
        ($_ | Out-String) | Add-Content -Path $err -Encoding UTF8
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
        Pop-Location
    }
    return [pscustomobject]@{
        Name = $Name
        ExitCode = $exitCode
        Stdout = Get-RelativePath $out
        Stderr = Get-RelativePath $err
    }
}

function Invoke-AulaTeX {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string[]]$Arguments
    )
    return Invoke-LoggedCommand -Name $Name -FilePath $AulaTeX -Arguments $Arguments
}

function Invoke-AulaTeXPromptFile {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$PromptPath,
        [Parameter(Mandatory)][string]$EngineName,
        [int]$PromptMaxTokens = 4096
    )
    $runner = Join-Path $AgentLogDir ((Get-SafeLogName "$Name-runner") + '.ps1')
    $pythonRunner = Join-Path $AgentLogDir ((Get-SafeLogName "$Name-runner") + '.py')
    @'
import sys
from pathlib import Path

repo = Path(sys.argv[1])
prompt_path = Path(sys.argv[2])
engine_name = sys.argv[3]
max_tokens = int(sys.argv[4])
sys.path.insert(0, str(repo))

from aulaTEX.aulatex.llm_bridge import AulaTeXLLMClient

prompt = prompt_path.read_text(encoding="utf-8", errors="replace")
result = AulaTeXLLMClient().call(engine_name, prompt, max_tokens=max_tokens)
if not result.ok:
    print(result.error or "LLM call failed", file=sys.stderr)
    raise SystemExit(2)
print(result.text or "")
'@ | Set-Content -Path $pythonRunner -Encoding UTF8
    @"
param(
    [string]`$RepoRoot,
    [string]`$PythonRunner,
    [string]`$PromptPath,
    [string]`$EngineName,
    [string]`$MaxTokens
)
`$python = Join-Path `$RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path `$python)) { `$python = 'python' }
`$env:AULATEX_LLM_TIMEOUT_SECONDS = if (`$env:AULATEX_LLM_TIMEOUT_SECONDS) { `$env:AULATEX_LLM_TIMEOUT_SECONDS } else { '1800' }
& `$python `$PythonRunner `$RepoRoot `$PromptPath `$EngineName `$MaxTokens
exit `$LASTEXITCODE
"@ | Set-Content -Path $runner -Encoding UTF8
    return Invoke-LoggedCommand -Name $Name -FilePath $runner -Arguments @([string]$RepoRoot, $pythonRunner, $PromptPath, $EngineName, ([string]$PromptMaxTokens))
}

function Get-MemoryInfo {
    param([Parameter(Mandatory)][System.IO.FileInfo]$File)
    $json = Read-JsonFile $File.FullName
    $meta = $null
    if ($null -ne $json -and $json.PSObject.Properties.Name -contains 'node_metadata') { $meta = $json.node_metadata }
    $sources = @()
    if ($null -ne $json -and $json.PSObject.Properties.Name -contains 'sources') { $sources += @($json.sources) }
    if ($null -ne $json -and $json.PSObject.Properties.Name -contains 'source_documents') { $sources += @($json.source_documents) }
    return [pscustomobject]@{
        Path = Get-RelativePath $File.FullName
        FullName = $File.FullName
        JsonOk = ($null -ne $json)
        Level = if ($null -ne $meta) { [string]$meta.level } else { '' }
        ScopeKey = if ($null -ne $meta) { [string]$meta.scope_key } else { '' }
        RelativePath = if ($null -ne $meta) { [string]$meta.relative_path } else { '' }
        Sources = @($sources | Where-Object { $_ } | Select-Object -Unique)
    }
}

function Get-TexInfo {
    param([Parameter(Mandatory)][System.IO.FileInfo]$File)
    $text = Get-Content -Raw -Encoding UTF8 $File.FullName
    $isPresentation = $File.Name -like 'presentacion-*.tex'
    $isReport = $File.Name -like 'reporte-*.tex'
    $pdf = [System.IO.Path]::ChangeExtension($File.FullName, '.pdf')
    $pdfInfo = Get-Item $pdf -ErrorAction SilentlyContinue
    $sections = [regex]::Matches($text, '\\section\{([^}]+)\}') | ForEach-Object { $_.Groups[1].Value }
    $frames = [regex]::Matches($text, '\\begin\{frame\}')
    $beamerFramesWithTitles = [regex]::Matches($text, '\\begin\{frame\}(\[[^\]]+\])?\{[^}]+\}')
    $qualityFlags = New-Object System.Collections.Generic.List[string]

    if ($isPresentation) {
        if ($frames.Count -lt 5) { $qualityFlags.Add('presentacion-muy-breve') }
        if ($text -notmatch '\\usetheme|\\usecolortheme|\\definecolor|\\setbeamercolor|\\setbeamertemplate') { $qualityFlags.Add('presentacion-sin-tema-visual') }
        if ($text -notmatch '\\titlegraphic|\\includegraphics') { $qualityFlags.Add('presentacion-sin-identidad-grafica') }
        if ($text -notmatch '\\AtBeginSection|\\tableofcontents|\\section\{') { $qualityFlags.Add('presentacion-sin-estructura-navegable') }
        if ($text -notmatch '\\begin\{block\}|\\begin\{alertblock\}|\\begin\{exampleblock\}|tikzpicture|columns') { $qualityFlags.Add('presentacion-sin-recursos-didacticos') }
        if ($beamerFramesWithTitles.Count -lt 3) { $qualityFlags.Add('presentacion-pocos-frames-con-titulo') }
    }

    if ($isReport) {
        if ($text -match '\\pendiente\{|\[PENDIENTE|clave1|clave2|TODO') { $qualityFlags.Add('reporte-con-pendientes-o-placeholders') }
        if ($text -notmatch '\\cite[p|t]?\{') { $qualityFlags.Add('reporte-sin-citas') }
        if ($text -notmatch '\\bibliography\{') { $qualityFlags.Add('reporte-sin-bibliografia') }
        if ($sections.Count -lt 4) { $qualityFlags.Add('reporte-estructura-minima-debil') }
        if ($text -notmatch 'Criterios de entrega|evaluaci[oó]n|Producto solicitado|Tecnica didactica|T[eé]cnica did[aá]ctica') { $qualityFlags.Add('reporte-sin-criterios-o-tecnica-explicita') }
    }

    return [pscustomobject]@{
        Path = Get-RelativePath $File.FullName
        FullName = $File.FullName
        Directory = Get-RelativePath $File.DirectoryName
        Name = $File.Name
        IsPresentation = $isPresentation
        IsReport = $isReport
        IsActivity = ($File.BaseName -match 'Actividad[-_ ]?\d+')
        ActivityNumber = if ($File.BaseName -match 'Actividad[-_ ]?(\d+)') { [int]$Matches[1] } else { 0 }
        PdfPath = Get-RelativePath $pdf
        PdfExists = ($null -ne $pdfInfo)
        PdfStale = ($null -ne $pdfInfo -and $pdfInfo.LastWriteTime -lt $File.LastWriteTime)
        Sections = @($sections)
        FrameCount = $frames.Count
        QualityFlags = @($qualityFlags)
    }
}

function Invoke-UcnlAudit {
    param([Parameter(Mandatory)][string]$CycleDir)
    New-Item -ItemType Directory -Path $CycleDir -Force | Out-Null
    $texFiles = Get-ChildItem $RootPath -Recurse -Filter '*.tex' | Sort-Object FullName
    $memoryFiles = Get-ChildItem $RootPath -Recurse -Filter '*.json' | Where-Object { $_.FullName -like '*\.memoria-aulatex\*' } | Sort-Object FullName
    $texInfos = @($texFiles | ForEach-Object { Get-TexInfo $_ })
    $memoryInfos = @($memoryFiles | ForEach-Object { Get-MemoryInfo $_ })
    $issues = New-Object System.Collections.Generic.List[object]

    foreach ($tex in $texInfos) {
        $dirMems = @($memoryInfos | Where-Object { $_.RelativePath -eq $tex.Directory -or $_.Sources -contains $tex.Path })
        if ($dirMems.Count -eq 0 -and ($tex.IsReport -or $tex.IsPresentation)) {
            $issues.Add([pscustomobject]@{ Severity='warning'; Kind='tex-sin-memoria-directa'; Target=$tex.Path; Detail='No se encontro memoria editorial que apunte a la carpeta o fuente TEX.' })
        }
        if (-not $tex.PdfExists -and ($tex.IsReport -or $tex.IsPresentation)) {
            $issues.Add([pscustomobject]@{ Severity='error'; Kind='pdf-faltante'; Target=$tex.Path; Detail="No existe PDF final esperado: $($tex.PdfPath)" })
        }
        elseif ($tex.PdfStale) {
            $issues.Add([pscustomobject]@{ Severity='warning'; Kind='pdf-desactualizado'; Target=$tex.Path; Detail="PDF anterior al TEX: $($tex.PdfPath)" })
        }
        foreach ($flag in $tex.QualityFlags) {
            $severity = if ($flag -like 'presentacion-*') { 'quality' } else { 'warning' }
            $issues.Add([pscustomobject]@{ Severity=$severity; Kind=$flag; Target=$tex.Path; Detail='Bandera editorial detectada por heuristica local.' })
        }
    }

    foreach ($mem in $memoryInfos) {
        if (-not $mem.JsonOk) {
            $issues.Add([pscustomobject]@{ Severity='error'; Kind='memoria-json-invalido'; Target=$mem.Path; Detail='No se pudo parsear JSON.' })
            continue
        }
        if ($mem.RelativePath -and -not (Test-Path (Join-Path $RepoRoot $mem.RelativePath))) {
            $issues.Add([pscustomobject]@{ Severity='error'; Kind='memoria-ruta-inexistente'; Target=$mem.Path; Detail="relative_path inexistente: $($mem.RelativePath)" })
        }
        foreach ($src in $mem.Sources) {
            if (($src -like '*.tex' -or $src -like '*.bib') -and -not (Test-Path (Join-Path $RepoRoot $src))) {
                $issues.Add([pscustomobject]@{ Severity='warning'; Kind='memoria-fuente-inexistente'; Target=$mem.Path; Detail="Fuente no existe: $src" })
            }
        }
    }

    $summary = [pscustomobject]@{
        timestamp = (Get-Date).ToString('s')
        root = Get-RelativePath $RootPath
        tex_total = $texInfos.Count
        report_total = @($texInfos | Where-Object { $_.IsReport }).Count
        presentation_total = @($texInfos | Where-Object { $_.IsPresentation }).Count
        memory_total = $memoryInfos.Count
        pdf_missing = @($issues | Where-Object { $_.Kind -eq 'pdf-faltante' }).Count
        pdf_stale = @($issues | Where-Object { $_.Kind -eq 'pdf-desactualizado' }).Count
        presentation_quality_flags = @($issues | Where-Object { $_.Kind -like 'presentacion-*' }).Count
        report_quality_flags = @($issues | Where-Object { $_.Kind -like 'reporte-*' }).Count
        issue_total = $issues.Count
    }

    $manifest = [pscustomobject]@{
        summary = $summary
        issues = @($issues.ToArray())
    }
    $jsonPath = Join-Path $CycleDir 'audit.json'
    $mdPath = Join-Path $CycleDir 'audit.md'
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -Path $jsonPath -Encoding UTF8

    $md = New-Object System.Collections.Generic.List[string]
    $md.Add('# Auditoria editorial UCNL')
    $md.Add('')
    $md.Add("- Fecha: $($summary.timestamp)")
    $md.Add("- TEX: $($summary.tex_total) total, $($summary.report_total) reportes, $($summary.presentation_total) presentaciones")
    $md.Add("- Memorias editoriales: $($summary.memory_total)")
    $md.Add("- PDFs faltantes: $($summary.pdf_missing)")
    $md.Add("- PDFs desactualizados: $($summary.pdf_stale)")
    $md.Add("- Banderas de calidad en presentaciones: $($summary.presentation_quality_flags)")
    $md.Add("- Banderas de calidad en reportes: $($summary.report_quality_flags)")
    $md.Add('')
    $md.Add('## Primeros hallazgos')
    foreach ($issue in @($issues | Select-Object -First 80)) {
        $md.Add(('- [{0}] {1}: {2} - {3}' -f $issue.Severity, $issue.Kind, $issue.Target, $issue.Detail))
    }
    if ($issues.Count -gt 80) {
        $md.Add(('- ... {0} hallazgos adicionales en JSON.' -f ($issues.Count - 80)))
    }
    $md -join "`n" | Set-Content -Path $mdPath -Encoding UTF8
    return [pscustomobject]@{
        Summary = $summary
        Issues = @($issues.ToArray())
        Json = Get-RelativePath $jsonPath
        Markdown = Get-RelativePath $mdPath
    }
}

function Get-TargetsFromAudit {
    param(
        [Parameter(Mandatory)]$Audit,
        [Parameter(Mandatory)][string]$KindPattern,
        [int]$Limit = 10
    )
    return @($Audit.Issues | Where-Object { $_.Kind -like $KindPattern } | Select-Object -ExpandProperty Target -Unique | Select-Object -First $Limit)
}

function Invoke-MemoryCycle {
    param([Parameter(Mandatory)][string]$CycleDir)
    $result = New-Object System.Collections.Generic.List[object]
    if (-not $RunMemory) { return @() }
    $args = @(
        '-Execute',
        '-Root', $Root,
        '-Levels', 'all',
        '-PropagationMode', 'local',
        '-Iterations', ([string]$Iterations),
        '-BatchSize', ([string]$EditorialBatchSize),
        '-MaxBatches', ([string]$EditorialMaxBatches),
        '-MaxTokens', ([string]$MaxTokens),
        '-TimeoutSeconds', ([string]$TimeoutSeconds),
        '-CheckpointName', ('ucnl-cycle-' + (Get-Date -Format 'yyyyMMddHHmmss'))
    )
    foreach ($engineName in $Engine) { $args += @('-Engine', $engineName) }
    $result.Add((Invoke-LoggedCommand -Name 'memory-cycle' -FilePath $BatchMemoryScript -Arguments $args))
    return @($result.ToArray())
}

function Invoke-ReportCycle {
    param(
        [Parameter(Mandatory)]$Audit,
        [Parameter(Mandatory)][string]$CycleDir
    )
    $results = New-Object System.Collections.Generic.List[object]
    if (-not $RunReports) { return @() }
    $targets = Get-TargetsFromAudit -Audit $Audit -KindPattern 'reporte-*' -Limit $MaxReportNodes
    foreach ($target in $targets) {
        $activity = if ($target -match 'Actividad[-_ ]?(\d+)') { [int]$Matches[1] } else { 1 }
        $args = @('activity-monitor','--target',$target,'--activity',([string]$activity),'--max-cycles',([string]$Iterations),'--compile-check','--apply-bibliography-repair','--keep-going')
        if (-not $Apply) { $args += '--no-apply-revision-patches' }
        $results.Add((Invoke-AulaTeX -Name ('report-' + ($target -replace '[^A-Za-z0-9_.-]', '_')) -Arguments $args))
    }
    return @($results.ToArray())
}

function New-PresentationImprovementPrompt {
    param([Parameter(Mandatory)][string]$Target)
    $targetText = Get-Content -Raw -Encoding UTF8 (Join-Path $RepoRoot $Target)
    $iiiepeText = if (Test-Path (Join-Path $RepoRoot $ReferencePresentationIIIEPE)) { Get-Content -Raw -Encoding UTF8 (Join-Path $RepoRoot $ReferencePresentationIIIEPE) } else { '' }
    $unadmText = if (Test-Path (Join-Path $RepoRoot $ReferencePresentationUnADM)) { Get-Content -Raw -Encoding UTF8 (Join-Path $RepoRoot $ReferencePresentationUnADM) } else { '' }
    $targetText = $targetText.Substring(0, [Math]::Min(18000, $targetText.Length))
    $iiiepeText = $iiiepeText.Substring(0, [Math]::Min(16000, $iiiepeText.Length))
    $unadmText = $unadmText.Substring(0, [Math]::Min(12000, $unadmText.Length))
    return @"
Actua como editor LaTeX Beamer experto de AulaTeX.
Objetivo: mejorar la presentacion UCNL indicada para que alcance calidad visual y didactica comparable a IIIEPE y UnADM.

Reglas obligatorias:
- Conservar identidad UCNL y logos UCNL/Nuevo Leon.
- Mantener compilacion con pdflatex/latexmk.
- Crear estilo visual consistente: paleta, footline, frametitle, portada, secciones, bloques, columnas o TikZ cuando aporte.
- Aumentar estructura didactica: objetivo, ruta, desarrollo, producto/actividad, cierre y referencias si aplica.
- No inventar datos personales ni fuentes.
- Devuelve un plan de parche por secciones y un bloque TEX completo sugerido o instrucciones precisas de reemplazo.

ARCHIVO OBJETIVO: $Target

TEX ACTUAL:
$targetText

REFERENCIA IIIEPE:
$iiiepeText

REFERENCIA UnADM:
$unadmText
"@
}

function Invoke-PresentationCycle {
    param(
        [Parameter(Mandatory)]$Audit,
        [Parameter(Mandatory)][string]$CycleDir
    )
    $results = New-Object System.Collections.Generic.List[object]
    if (-not $RunPresentations) { return @() }
    $targets = Get-TargetsFromAudit -Audit $Audit -KindPattern 'presentacion-*' -Limit $MaxPresentationNodes
    foreach ($target in $targets) {
        $prompt = New-PresentationImprovementPrompt -Target $target
        $safe = Get-SafeLogName $target
        $promptPath = Join-Path $PatchDir "$safe.prompt.md"
        $patchPath = Join-Path $PatchDir "$safe.llm.md"
        $prompt | Set-Content -Path $promptPath -Encoding UTF8
        foreach ($engineName in $Engine) {
            $engineSafe = ($engineName -replace '[^A-Za-z0-9_.-]', '_')
            $results.Add((Invoke-AulaTeXPromptFile -Name "presentation-$safe-$engineSafe" -PromptPath $promptPath -EngineName $engineName -PromptMaxTokens $MaxTokens))
            $last = $results[$results.Count - 1]
            if ($last.ExitCode -eq 0) {
                Get-Content -Raw -Encoding UTF8 (Join-Path $RepoRoot $last.Stdout) | Set-Content -Path $patchPath -Encoding UTF8
                break
            }
        }
        if ($Apply) {
            # Aplicación automática conservadora no implementada: requiere revisión humana del patch LLM.
            # El patch queda en .aulatex-temp para que un agente editor aplique cambios con control de diff.
        }
    }
    return @($results.ToArray())
}

function Invoke-CompileCycle {
    param(
        [Parameter(Mandatory)]$Audit,
        [Parameter(Mandatory)][string]$CycleDir
    )
    $results = New-Object System.Collections.Generic.List[object]
    if (-not $Compile) { return @() }
    $targets = @($Audit.Issues | Where-Object { $_.Kind -in @('pdf-faltante','pdf-desactualizado') } | Select-Object -ExpandProperty Target -Unique | Select-Object -First $MaxCompileNodes)
    if ($targets.Count -eq 0) {
        $targets = @($Audit.Issues | Where-Object { $_.Kind -like 'reporte-*' -or $_.Kind -like 'presentacion-*' } | Select-Object -ExpandProperty Target -Unique | Select-Object -First $MaxCompileNodes)
    }
    foreach ($target in $targets) {
        $results.Add((Invoke-LoggedCommand -Name ('compile-' + ($target -replace '[^A-Za-z0-9_.-]', '_')) -FilePath $LatexBuild -Arguments @($target)))
    }
    return @($results.ToArray())
}

$cycleRecords = New-Object System.Collections.Generic.List[object]
Write-Host "AulaTeX UCNL ciclo editorial" -ForegroundColor Cyan
Write-Host "Repositorio: $RepoRoot"
Write-Host "Raiz: $Root"
Write-Host "Modo: $(if ($Execute) { 'EJECUCION' } else { 'PLAN/AUDITORIA' })"
Write-Host "Ciclos: $Cycles"

for ($cycle = 1; $cycle -le [Math]::Max(1, $Cycles); $cycle++) {
    $cycleDir = Join-Path $CycleRoot ("cycle-{0:00}" -f $cycle)
    New-Item -ItemType Directory -Path $cycleDir -Force | Out-Null
    $auditBefore = Invoke-UcnlAudit -CycleDir $cycleDir
    $runs = New-Object System.Collections.Generic.List[object]

    if ($Execute) {
        foreach ($item in @(Invoke-MemoryCycle -CycleDir $cycleDir)) { $runs.Add($item) }
        foreach ($item in @(Invoke-ReportCycle -Audit $auditBefore -CycleDir $cycleDir)) { $runs.Add($item) }
        foreach ($item in @(Invoke-PresentationCycle -Audit $auditBefore -CycleDir $cycleDir)) { $runs.Add($item) }
        foreach ($item in @(Invoke-CompileCycle -Audit $auditBefore -CycleDir $cycleDir)) { $runs.Add($item) }
    }

    $auditAfter = if ($Execute) { Invoke-UcnlAudit -CycleDir (Join-Path $cycleDir 'after') } else { $null }
    $cycleRecords.Add([pscustomobject]@{
        cycle = $cycle
        audit_before = $auditBefore.Json
        audit_after = if ($null -ne $auditAfter) { $auditAfter.Json } else { '' }
        issue_total_before = $auditBefore.Summary.issue_total
        issue_total_after = if ($null -ne $auditAfter) { $auditAfter.Summary.issue_total } else { $null }
        runs = @($runs.ToArray())
    })
}

$manifestPath = Join-Path $CycleRoot 'manifest.json'
$reportPath = Join-Path $CycleRoot 'reporte-ciclo-ucnl.md'
$manifest = [pscustomobject]@{
    timestamp = (Get-Date).ToString('s')
    root = Get-RelativePath $RootPath
    execute = [bool]$Execute
    apply = [bool]$Apply
    cycles = @($cycleRecords.ToArray())
}
$manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $manifestPath -Encoding UTF8

$md = New-Object System.Collections.Generic.List[string]
$md.Add('# Ciclo editorial UCNL')
$md.Add('')
$md.Add("- Fecha: $($manifest.timestamp)")
$md.Add("- Raiz: $($manifest.root)")
$md.Add("- Execute: $Execute")
$md.Add("- Apply: $Apply")
$md.Add('')
foreach ($record in $cycleRecords) {
    $md.Add("## Ciclo $($record.cycle)")
    $md.Add("- Auditoria inicial: $($record.audit_before)")
    if ($record.audit_after) { $md.Add("- Auditoria posterior: $($record.audit_after)") }
    $md.Add("- Issues antes: $($record.issue_total_before)")
    if ($null -ne $record.issue_total_after) { $md.Add("- Issues despues: $($record.issue_total_after)") }
    foreach ($run in @($record.runs)) {
        $md.Add("- $($run.Name): exit=$($run.ExitCode), stdout=$($run.Stdout), stderr=$($run.Stderr)")
    }
    $md.Add('')
}
$md -join "`n" | Set-Content -Path $reportPath -Encoding UTF8

Write-Host "manifest=$(Get-RelativePath $manifestPath)"
Write-Host "report=$(Get-RelativePath $reportPath)"
Write-Host "cycle_root=$(Get-RelativePath $CycleRoot)"
Write-Host "cycles=$($cycleRecords.Count)"
Write-Host "execute=$Execute"
