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
    [switch]$RunReportLlmRevision,
    [switch]$RunPresentations,
    [switch]$Compile,
    [int]$MaxMemoryNodes = 8,
    [int]$MaxReportNodes = 8,
    [int]$MaxPresentationNodes = 8,
    [int]$MaxCompileNodes = 80,
    [double]$MinimumImprovementPercent = 5.0,
    [switch]$AllTex,
    [switch]$SkipLlmPresentationPatch,
    [switch]$SkipActivityMonitor,
    [int]$EditorialBatchSize = 1,
    [int]$EditorialMaxBatches = 1,
    [int]$Iterations = 2,
    [int]$MaxTokens = 128000,
    [int]$TimeoutSeconds = 1800,
    [string[]]$Engine = @("Codex", "Auto (model-router)", "GPT-Pro", "Claude Foundry"),
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

$LlmLimits = @{
    'Codex' = [pscustomobject]@{ Deployment='gpt-5.3-codex'; Context=400000; Input=272000; Output=128000; PromptBudget=240000 }
    'Auto (model-router)' = [pscustomobject]@{ Deployment='model-router'; Context=200000; Input=200000; Output=128000; PromptBudget=160000 }
    'GPT-Pro' = [pscustomobject]@{ Deployment='gpt-5.4-pro'; Context=1050000; Input=922000; Output=128000; PromptBudget=850000 }
    'Claude Foundry' = [pscustomobject]@{ Deployment='claude-opus-4-8'; Context=1000000; Input=872000; Output=128000; PromptBudget=800000 }
}

function Get-EngineLimit {
    param([Parameter(Mandatory)][string]$EngineName)
    if ($LlmLimits.ContainsKey($EngineName)) { return $LlmLimits[$EngineName] }
    return [pscustomobject]@{ Deployment=$EngineName; Context=200000; Input=160000; Output=32768; PromptBudget=120000 }
}

function Get-OutputTokenLimit {
    param([Parameter(Mandatory)][string]$EngineName)
    $limit = Get-EngineLimit $EngineName
    return [Math]::Min([int]$MaxTokens, [int]$limit.Output)
}

function Get-PromptCharBudget {
    param([Parameter(Mandatory)][string]$EngineName)
    $limit = Get-EngineLimit $EngineName
    return [int]$limit.PromptBudget
}

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

function Get-NormalizedLatexText {
    param([AllowNull()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return '' }
    $normalized = [regex]::Replace($Text, '\\[a-zA-Z]+(\[[^\]]*\])?(\{[^{}]*\})?', ' ')
    $normalized = [regex]::Replace($normalized, '[^\p{L}\p{Nd}]+', ' ').Trim().ToLowerInvariant()
    return [regex]::Replace($normalized, '\s+', ' ')
}

function Get-DuplicateQuestionRows {
    param([Parameter(Mandatory)][string]$Text)
    $seen = @{}
    $duplicates = New-Object System.Collections.Generic.List[object]
    $rowPattern = '(?m)^\s*(\d+)\s*&\s*([^&\\]+?)\s*&\s*([^\\]+?)\\\\'
    foreach ($match in [regex]::Matches($Text, $rowPattern)) {
        $number = [int]$match.Groups[1].Value
        $question = $match.Groups[2].Value
        $answer = $match.Groups[3].Value
        $key = Get-NormalizedLatexText $question
        if ($key.Length -lt 20) { continue }
        if ($seen.ContainsKey($key)) {
            $first = $seen[$key]
            $duplicates.Add([pscustomobject]@{
                FirstNumber = $first.Number
                DuplicateNumber = $number
                Question = $question.Trim()
                Answer = $answer.Trim()
            })
        }
        else {
            $seen[$key] = [pscustomobject]@{ Number = $number; Question = $question.Trim(); Answer = $answer.Trim() }
        }
    }
    return @($duplicates.ToArray())
}

function Get-ActiveLatexText {
    param([Parameter(Mandatory)][string]$Text)
    $lines = New-Object System.Collections.Generic.List[string]
    foreach ($line in ($Text -split "`r?`n")) {
        if ($line.TrimStart().StartsWith('%')) { continue }
        $lines.Add($line)
    }
    return ($lines -join "`n")
}

function Get-LatexSectionText {
    param(
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][string]$SectionPattern
    )
    $pattern = "(?s)\\section\{[^}]*$SectionPattern[^}]*\}(.*?)(?=\\section\{|\\bibliography\{|\\end\{document\}|$)"
    $match = [regex]::Match($Text, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($match.Success) { return $match.Groups[1].Value }
    return ''
}

function Get-PlainLatexWordCount {
    param([AllowNull()][string]$Text)
    $plain = Get-NormalizedLatexText $Text
    if ([string]::IsNullOrWhiteSpace($plain)) { return 0 }
    return @($plain -split '\s+' | Where-Object { $_.Length -gt 1 }).Count
}

function Get-EditorialQualityFlags {
    param(
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][string[]]$Sections
    )
    $flags = New-Object System.Collections.Generic.List[string]
    $active = Get-ActiveLatexText $Text
    $intro = Get-LatexSectionText -Text $active -SectionPattern 'Introducci[oó]n'
    $analysis = Get-LatexSectionText -Text $active -SectionPattern 'An[aá]lisis|Desarrollo'
    $ownAnalysis = Get-LatexSectionText -Text $active -SectionPattern 'An[aá]lisis propio'
    $posture = Get-LatexSectionText -Text $active -SectionPattern 'Postura personal'
    $conclusion = Get-LatexSectionText -Text $active -SectionPattern 'Conclusi[oó]n'
    $citeCount = [regex]::Matches($active, '\\cite[t|p]?\*?(?:\[[^\]]*\])*\{[^}]+\}').Count
    $wordCount = Get-PlainLatexWordCount $active

    if ((Get-PlainLatexWordCount $intro) -lt 55) { $flags.Add('reporte-introduccion-debil') }
    if ($intro -notmatch 'problema|tesis|objetivo|enfoque|perspectiva|prop[oó]sito') { $flags.Add('reporte-sin-enfoque-explicito') }
    if ((Get-PlainLatexWordCount $ownAnalysis) -lt 60 -and (Get-PlainLatexWordCount $analysis) -lt 180) { $flags.Add('reporte-analisis-propio-insuficiente') }
    if ((Get-PlainLatexWordCount $posture) -gt 0 -and $posture -notmatch 'considero|sostengo|desde esta perspectiva|la posici[oó]n|porque|por ello|consecuencia') { $flags.Add('reporte-postura-poco-argumentada') }
    if ((Get-PlainLatexWordCount $conclusion) -lt 55) { $flags.Add('reporte-conclusion-debil') }
    if ($conclusion -match 'en conclusi[oó]n,?\s+este trabajo|se realiz[oó]|se hizo|aprend[ií] mucho') { $flags.Add('reporte-cierre-generico') }
    if ($citeCount -lt 1) { $flags.Add('reporte-sin-citas') }
    elseif ($wordCount -gt 900 -and $citeCount -lt 2) { $flags.Add('reporte-citas-insuficientes') }
    if ($active -match 'muy importante|gran importancia|hoy en d[ií]a|desde siempre|es importante porque si') { $flags.Add('reporte-redaccion-generica') }
    return @($flags.ToArray() | Select-Object -Unique)
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
    $duplicateQuestionRows = @(Get-DuplicateQuestionRows $text)
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
        if ($text -match '\\pendiente\{|\[PENDIENTE|clave1|clave2|TODO|Nombre \\\\ Apellido') { $qualityFlags.Add('reporte-con-pendientes-o-placeholders') }
        if ($text -notmatch '\\bibliography\{') { $qualityFlags.Add('reporte-sin-bibliografia') }
        if ($sections.Count -lt 4) { $qualityFlags.Add('reporte-estructura-minima-debil') }
        if ($text -notmatch 'Criterios de entrega|evaluaci[oó]n|Producto solicitado|Tecnica didactica|T[eé]cnica did[aá]ctica') { $qualityFlags.Add('reporte-sin-criterios-o-tecnica-explicita') }
        if ($duplicateQuestionRows.Count -gt 0) { $qualityFlags.Add('reporte-preguntas-duplicadas') }
        foreach ($editorialFlag in @(Get-EditorialQualityFlags -Text $text -Sections @($sections))) {
            $qualityFlags.Add($editorialFlag)
        }
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
        DuplicateQuestionRows = @($duplicateQuestionRows)
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
            $detail = 'Bandera editorial detectada por heuristica local.'
            if ($flag -eq 'reporte-preguntas-duplicadas') {
                $pairs = @($tex.DuplicateQuestionRows | ForEach-Object { "preguntas $($_.FirstNumber) y $($_.DuplicateNumber)" })
                $detail = 'Reactivos duplicados detectados: ' + ($pairs -join '; ')
            }
            $issues.Add([pscustomobject]@{ Severity=$severity; Kind=$flag; Target=$tex.Path; Detail=$detail })
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
    $targets = @($Audit.Issues | Where-Object { $_.Kind -like $KindPattern } | Select-Object -ExpandProperty Target -Unique)
    if ($AllTex -or $Limit -le 0) { return $targets }
    return @($targets | Select-Object -First $Limit)
}

function Invoke-MemoryCycle {
    param([Parameter(Mandatory)][string]$CycleDir)
    $result = New-Object System.Collections.Generic.List[object]
    if (-not $RunMemory) { return @() }
    $memoryOutputLimit = ($Engine | ForEach-Object { Get-OutputTokenLimit $_ } | Measure-Object -Minimum).Minimum
    if ($null -eq $memoryOutputLimit) { $memoryOutputLimit = [Math]::Min($MaxTokens, 128000) }
    $args = @(
        '-Execute',
        '-Root', $Root,
        '-Levels', 'all',
        '-PropagationMode', 'local',
        '-Iterations', ([string]$Iterations),
        '-BatchSize', ([string]$EditorialBatchSize),
        '-MaxBatches', ([string]$EditorialMaxBatches),
        '-MaxTokens', ([string]$memoryOutputLimit),
        '-TimeoutSeconds', ([string]$TimeoutSeconds),
        '-CheckpointName', ('ucnl-cycle-' + (Get-Date -Format 'yyyyMMddHHmmss')),
        '-Engine'
    )
    $args += @($Engine)
    $result.Add((Invoke-LoggedCommand -Name 'memory-cycle' -FilePath $BatchMemoryScript -Arguments $args))
    return @($result.ToArray())
}

function Get-ReportEditorialTargets {
    param(
        [Parameter(Mandatory)]$Audit,
        [int]$Limit = 10
    )
    $editorialKinds = @(
        'reporte-introduccion-debil',
        'reporte-sin-enfoque-explicito',
        'reporte-analisis-propio-insuficiente',
        'reporte-postura-poco-argumentada',
        'reporte-conclusion-debil',
        'reporte-cierre-generico',
        'reporte-citas-insuficientes',
        'reporte-redaccion-generica',
        'reporte-preguntas-duplicadas',
        'reporte-con-pendientes-o-placeholders'
    )
    $targets = @($Audit.Issues | Where-Object { $_.Kind -in $editorialKinds } | Select-Object -ExpandProperty Target -Unique)
    if ($AllTex -or $Limit -le 0) { return $targets }
    return @($targets | Select-Object -First $Limit)
}

function New-ReportEditorialImprovementPrompt {
    param(
        [Parameter(Mandatory)][string]$Target,
        [Parameter(Mandatory)][string]$EngineName,
        [Parameter(Mandatory)]$Audit
    )
    $budget = Get-PromptCharBudget $EngineName
    $targetPath = Join-Path $RepoRoot $Target
    $targetText = Get-Content -Raw -Encoding UTF8 $targetPath
    $targetBudget = [Math]::Min([int]($budget * 0.78), $targetText.Length)
    $targetText = $targetText.Substring(0, $targetBudget)
    $flags = @($Audit.Issues | Where-Object { $_.Target -eq $Target -and $_.Kind -like 'reporte-*' } | Select-Object Kind,Detail)
    $flagsJson = ($flags | ConvertTo-Json -Depth 4)
    $limit = Get-EngineLimit $EngineName
    return @"
Actua como editor academico LaTeX de AulaTeX para UCNL.
Motor: $EngineName / deployment real: $($limit.Deployment) / contexto oficial: $($limit.Context) / salida maxima oficial: $($limit.Output).

Objetivo: mejorar redaccion, enfoque, analisis propio y cierre argumentativo del reporte, sin romper LaTeX ni inventar fuentes.

Criterios obligatorios:
- Mantener identidad UCNL, metadatos, bibliografia, citas y estructura LaTeX.
- No cambiar preguntas/respuestas factuales salvo detectar duplicados literales o placeholders.
- Mejorar la introduccion para que plantee problema, objetivo y enfoque.
- Mejorar analisis propio para que no sea resumen: debe incluir criterio, funcion, consecuencia y postura tecnica.
- Mejorar conclusion para responder que se comprendio y que postura final se sostiene.
- Evitar frases genericas como "es importante" sin causa/consecuencia.
- No inventar autores ni referencias. Si faltan citas, reutiliza solo claves ya presentes en el TEX.
- Devuelve SOLO JSON valido, sin Markdown, con esta forma:
{
  "summary": "breve resumen editorial",
  "introduccion": "nuevo contenido de la seccion Introduccion, sin encabezado \\section",
  "analisis_propio": "nuevo contenido de la subseccion Analisis propio, sin encabezado \\subsection",
  "postura_personal": "nuevo contenido opcional de la seccion Postura personal, sin encabezado \\section",
  "conclusion": "nuevo contenido de la seccion Conclusion, sin encabezado \\section"
}

Banderas detectadas:
$flagsJson

TEX objetivo: $Target

TEX actual:
$targetText
"@
}

function Get-JsonFromText {
    param([Parameter(Mandatory)][string]$Text)
    $match = [regex]::Match($Text, '(?s)\{.*\}')
    if (-not $match.Success) { return $null }
    try { return $match.Value | ConvertFrom-Json -ErrorAction Stop }
    catch { return $null }
}

function Set-LatexSectionBody {
    param(
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][string]$HeadingCommand,
        [Parameter(Mandatory)][string]$HeadingPattern,
        [Parameter(Mandatory)][string]$Body
    )
    if ([string]::IsNullOrWhiteSpace($Body)) { return $Text }
    if ($Body -match '\\documentclass|\\begin\{document\}|\\end\{document\}|\\bibliography\{') { return $Text }
    $escapedCommand = [regex]::Escape($HeadingCommand)
    $pattern = "(?s)($escapedCommand\{[^}]*$HeadingPattern[^}]*\}\s*)(.*?)(?=\\section\{|\\subsection\{|\\bibliography\{|\\end\{document\}|$)"
    $match = [regex]::Match($Text, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $match.Success) { return $Text }
    $replacement = $match.Groups[1].Value + ($Body.Trim() -replace '\$','$$$$') + "`r`n`r`n"
    return [regex]::Replace($Text, $pattern, $replacement, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
}

function Ensure-CanonicalBibliographyEntries {
    param([Parameter(Mandatory)][string]$Target)
    $targetPath = Join-Path $RepoRoot $Target
    if (-not (Test-Path $targetPath)) { return @() }
    $text = Get-Content -Raw -Encoding UTF8 $targetPath
    $bibMatches = @([regex]::Matches($text, '\\bibliography\{([^}]+)\}'))
    if ($bibMatches.Count -eq 0) { return @() }
    if ($bibMatches.Count -gt 1 -and $Apply) {
        $lastBib = $bibMatches[$bibMatches.Count - 1].Value
        $text = [regex]::Replace($text, '\\bibliography\{[^}]+\}\s*', '')
        $text = $text -replace '(?m)^% FIN DEL DOCUMENTO', ($lastBib + "`r`n`r`n% FIN DEL DOCUMENTO")
        $text | Set-Content -Path $targetPath -Encoding UTF8
    }
    $bibMatch = @([regex]::Matches($text, '\\bibliography\{([^}]+)\}')) | Select-Object -Last 1
    if ($null -eq $bibMatch) { return @() }
    $bibName = ($bibMatch.Groups[1].Value -split ',')[0].Trim()
    if ([string]::IsNullOrWhiteSpace($bibName)) { return @() }
    $bibPath = Join-Path (Split-Path $targetPath -Parent) ($bibName + '.bib')
    if (-not (Test-Path $bibPath)) { return @() }
    $canonicalBib = Join-Path $RepoRoot 'UCNL\bibliografia-ucnl.bib'
    if (-not (Test-Path $canonicalBib)) { return @() }
    $bibText = Get-Content -Raw -Encoding UTF8 $bibPath
    $canonicalText = Get-Content -Raw -Encoding UTF8 $canonicalBib
    $added = New-Object System.Collections.Generic.List[string]
    foreach ($cite in [regex]::Matches($text, '\\cite[t|p]?\*?(?:\[[^\]]*\])*\{([^}]+)\}')) {
        foreach ($key in ($cite.Groups[1].Value -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })) {
            if ($bibText -match ('(?m)^@\w+\s*\{\s*' + [regex]::Escape($key) + '\s*,')) { continue }
            $entryMatch = [regex]::Match($canonicalText, '(?ms)^@\w+\s*\{\s*' + [regex]::Escape($key) + '\s*,.*?^\}')
            if ($entryMatch.Success) {
                $bibText = $bibText.TrimEnd() + "`r`n`r`n" + $entryMatch.Value.Trim() + "`r`n"
                $added.Add($key)
            }
        }
    }
    if ($added.Count -gt 0 -and $Apply) { $bibText | Set-Content -Path $bibPath -Encoding UTF8 }
    return @($added.ToArray())
}

function Apply-ReportEditorialPatch {
    param(
        [Parameter(Mandatory)][string]$Target,
        [Parameter(Mandatory)][string]$LlmOutputPath
    )
    $targetPath = Join-Path $RepoRoot $Target
    if (-not (Test-Path $targetPath)) { return [pscustomobject]@{ Applied=$false; Reason='target-not-found'; Target=$Target } }
    if (-not (Test-Path $LlmOutputPath)) { return [pscustomobject]@{ Applied=$false; Reason='llm-output-not-found'; Target=$Target } }
    $raw = Get-Content -Raw -Encoding UTF8 $LlmOutputPath
    $json = Get-JsonFromText $raw
    if ($null -eq $json) { return [pscustomobject]@{ Applied=$false; Reason='json-not-found'; Target=$Target } }
    $original = Get-Content -Raw -Encoding UTF8 $targetPath
    $patched = $original
    if ($json.PSObject.Properties.Name -contains 'introduccion') { $patched = Set-LatexSectionBody -Text $patched -HeadingCommand '\section' -HeadingPattern 'Introducci[oó]n' -Body ([string]$json.introduccion) }
    if ($json.PSObject.Properties.Name -contains 'analisis_propio') { $patched = Set-LatexSectionBody -Text $patched -HeadingCommand '\subsection' -HeadingPattern 'An[aá]lisis propio' -Body ([string]$json.analisis_propio) }
    if ($json.PSObject.Properties.Name -contains 'postura_personal') { $patched = Set-LatexSectionBody -Text $patched -HeadingCommand '\section' -HeadingPattern 'Postura personal' -Body ([string]$json.postura_personal) }
    if ($json.PSObject.Properties.Name -contains 'conclusion') { $patched = Set-LatexSectionBody -Text $patched -HeadingCommand '\section' -HeadingPattern 'Conclusi[oó]n' -Body ([string]$json.conclusion) }
    if ($patched -eq $original) { return [pscustomobject]@{ Applied=$false; Reason='no-safe-change'; Target=$Target } }
    if ($Apply) {
        $backup = "$targetPath.editorial-llm.bak"
        if (-not (Test-Path $backup)) { $original | Set-Content -Path $backup -Encoding UTF8 }
        $patched | Set-Content -Path $targetPath -Encoding UTF8
    }
    return [pscustomobject]@{ Applied=[bool]$Apply; Reason=if($Apply){'applied'}else{'preview-only'}; Target=$Target }
}

function Invoke-ReportCycle {
    param(
        [Parameter(Mandatory)]$Audit,
        [Parameter(Mandatory)][string]$CycleDir
    )
    $results = New-Object System.Collections.Generic.List[object]
    if (-not $RunReports) { return @() }
    $targets = Get-TargetsFromAudit -Audit $Audit -KindPattern 'reporte-*' -Limit $MaxReportNodes
    if (-not $SkipActivityMonitor) {
        foreach ($target in $targets) {
            $activity = if ($target -match 'Actividad[-_ ]?(\d+)') { [int]$Matches[1] } else { 1 }
            $args = @('activity-monitor','--target',$target,'--activity',([string]$activity),'--max-cycles',([string]$Iterations),'--compile-check','--apply-bibliography-repair','--keep-going')
            if (-not $Apply) { $args += '--no-apply-revision-patches' }
            $results.Add((Invoke-AulaTeX -Name ('report-' + ($target -replace '[^A-Za-z0-9_.-]', '_')) -Arguments $args))
        }
    }
    if ($RunReportLlmRevision) {
        $llmTargets = @(Get-ReportEditorialTargets -Audit $Audit -Limit $MaxReportNodes)
        foreach ($target in $llmTargets) {
            foreach ($engineName in $Engine) {
                $safe = Get-SafeLogName ("report-llm-$engineName-$target")
                $promptPath = Join-Path $PatchDir "$safe.prompt.md"
                $prompt = New-ReportEditorialImprovementPrompt -Target $target -EngineName $engineName -Audit $Audit
                $prompt | Set-Content -Path $promptPath -Encoding UTF8
                $llmResult = Invoke-AulaTeXPromptFile -Name "report-llm-$engineName-$target" -PromptPath $promptPath -EngineName $engineName -PromptMaxTokens (Get-OutputTokenLimit $engineName)
                $results.Add($llmResult)
                if ($llmResult.ExitCode -eq 0) {
                    $llmOut = Join-Path $RepoRoot $llmResult.Stdout
                    $patchResult = Apply-ReportEditorialPatch -Target $target -LlmOutputPath $llmOut
                    $addedBibKeys = @(Ensure-CanonicalBibliographyEntries -Target $target)
                    $patchEnvelope = [pscustomobject]@{ patch = $patchResult; added_bib_keys = @($addedBibKeys) }
                    $patchLog = Join-Path $PatchDir "$safe.apply.json"
                    $patchEnvelope | ConvertTo-Json -Depth 6 | Set-Content -Path $patchLog -Encoding UTF8
                    $results.Add([pscustomobject]@{
                        Name = "apply-report-editorial-$safe"
                        ExitCode = if ($patchResult.Applied -or $patchResult.Reason -eq 'preview-only') { 0 } else { 1 }
                        Stdout = Get-RelativePath $patchLog
                        Stderr = $patchResult.Reason
                    })
                    if ($patchResult.Applied) { break }
                }
            }
        }
    }
    return @($results.ToArray())
}

function New-PresentationImprovementPrompt {
    param(
        [Parameter(Mandatory)][string]$Target,
        [Parameter(Mandatory)][string]$EngineName
    )
    $budget = Get-PromptCharBudget $EngineName
    $targetText = Get-Content -Raw -Encoding UTF8 (Join-Path $RepoRoot $Target)
    $iiiepeText = if (Test-Path (Join-Path $RepoRoot $ReferencePresentationIIIEPE)) { Get-Content -Raw -Encoding UTF8 (Join-Path $RepoRoot $ReferencePresentationIIIEPE) } else { '' }
    $unadmText = if (Test-Path (Join-Path $RepoRoot $ReferencePresentationUnADM)) { Get-Content -Raw -Encoding UTF8 (Join-Path $RepoRoot $ReferencePresentationUnADM) } else { '' }
    $targetBudget = [Math]::Min([int]($budget * 0.42), $targetText.Length)
    $iiiepeBudget = [Math]::Min([int]($budget * 0.34), $iiiepeText.Length)
    $unadmBudget = [Math]::Min([int]($budget * 0.20), $unadmText.Length)
    $targetText = $targetText.Substring(0, $targetBudget)
    $iiiepeText = $iiiepeText.Substring(0, $iiiepeBudget)
    $unadmText = $unadmText.Substring(0, $unadmBudget)
    $limit = Get-EngineLimit $EngineName
    return @"
Actua como editor LaTeX Beamer experto de AulaTeX.
Motor: $EngineName / deployment real: $($limit.Deployment) / contexto oficial: $($limit.Context) / salida maxima oficial: $($limit.Output).
Presupuesto de prompt aplicado por el orquestador: $budget caracteres.

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

function Apply-UcnlPresentationTheme {
    param([Parameter(Mandatory)][string]$Target)
    $path = Join-Path $RepoRoot $Target
    if (-not (Test-Path $path)) { return [pscustomobject]@{ Target=$Target; Applied=$false; Reason='missing-file' } }
    $text = Get-Content -Raw -Encoding UTF8 $path
    $original = $text
    if ($text -notmatch '\\documentclass.*\{beamer\}') { return [pscustomobject]@{ Target=$Target; Applied=$false; Reason='not-beamer' } }

    $themeBlock = @'

% ==============================================================================
% TEMA VISUAL UCNL / AULATEX
% Inspirado en el estándar visual de IIIEPE y UnADM: portada institucional,
% navegación limpia, bloques didácticos, pie de página y paleta propia.
% ==============================================================================
\usepackage{booktabs}
\usepackage{ragged2e}
\usepackage{tikz}
\usetikzlibrary{calc,positioning,fit,shadows.blur}

\definecolor{ucnlNavy}{HTML}{143A5A}
\definecolor{ucnlBlue}{HTML}{1E6F9F}
\definecolor{ucnlGold}{HTML}{C6922E}
\definecolor{ucnlAqua}{HTML}{20A99A}
\definecolor{ucnlPaper}{HTML}{F6F8F7}
\definecolor{ucnlInk}{HTML}{1E2A32}

\mode<presentation>{
  \usetheme{default}
  \usefonttheme{professionalfonts}
  \setbeamertemplate{navigation symbols}{}
  \setbeamertemplate{blocks}[rounded][shadow=false]
}
\setbeamersize{text margin left=0.62cm,text margin right=0.62cm}
\setbeamercolor{background canvas}{bg=white}
\setbeamercolor{normal text}{fg=ucnlInk,bg=white}
\setbeamercolor{structure}{fg=ucnlBlue}
\setbeamercolor{frametitle}{fg=white,bg=ucnlNavy}
\setbeamercolor{block title}{fg=white,bg=ucnlBlue}
\setbeamercolor{block body}{fg=ucnlInk,bg=ucnlPaper}
\setbeamercolor{alerted text}{fg=ucnlGold}
\setbeamerfont{title}{size=\LARGE,series=\bfseries}
\setbeamerfont{frametitle}{size=\large,series=\bfseries}
\setbeamertemplate{itemize item}{\textcolor{ucnlAqua}{\large$\blacktriangleright$}}
\setbeamertemplate{itemize subitem}{\textcolor{ucnlGold}{\scriptsize$\blacksquare$}}

\setbeamertemplate{frametitle}{%
  \nointerlineskip
  \begin{beamercolorbox}[wd=\textwidth,ht=1.02cm,dp=0.22cm,leftskip=0.35cm,rightskip=0.25cm]{frametitle}
    \insertframetitle\hfill\includegraphics[height=0.58cm]{\UCNLlogodir/logo-ucnl.png}
  \end{beamercolorbox}
  {\color{ucnlGold}\rule{\textwidth}{1.3pt}}
}

\setbeamertemplate{footline}{%
  \leavevmode
  \hbox{%
    \begin{beamercolorbox}[wd=.34\paperwidth,ht=2.7ex,dp=1ex,leftskip=1em]{author in head/foot}\color{white}\insertshortauthor\end{beamercolorbox}%
    \begin{beamercolorbox}[wd=.40\paperwidth,ht=2.7ex,dp=1ex,center]{title in head/foot}\color{white}\insertshorttitle\end{beamercolorbox}%
    \begin{beamercolorbox}[wd=.26\paperwidth,ht=2.7ex,dp=1ex,rightskip=1em plus 1fil]{date in head/foot}\color{white}UCNL\hfill\insertframenumber/\inserttotalframenumber\end{beamercolorbox}%
  }
}
\setbeamercolor{author in head/foot}{bg=ucnlNavy}
\setbeamercolor{title in head/foot}{bg=ucnlBlue}
\setbeamercolor{date in head/foot}{bg=ucnlNavy}

\AtBeginSection[]{%
  \begin{frame}[plain]
    \begin{tikzpicture}[remember picture,overlay]
      \fill[ucnlNavy] (current page.south west) rectangle (current page.north east);
      \node[opacity=0.10,anchor=east] at ([xshift=0.8cm]current page.east) {\includegraphics[height=7.2cm]{\UCNLlogodir/logo-nuevo-leon.png}};
      \fill[ucnlGold] ([xshift=0.85cm,yshift=1.8cm]current page.south west) rectangle ([xshift=1.05cm,yshift=5.6cm]current page.south west);
    \end{tikzpicture}
    \vspace{1.8cm}
    \hspace{1.25cm}{\color{white}\Huge\bfseries\insertsectionhead}
  \end{frame}
}
'@

    if ($text -notmatch 'TEMA VISUAL UCNL / AULATEX') {
        $text = $text -replace '(?m)^\\usepackage\{lmodern\}\s*', "\usepackage{lmodern}`r`n$themeBlock`r`n"
    }

    $supportFrames = @'

\section{Ruta editorial UCNL}

\begin{frame}{Objetivo y alcance}
  \begin{block}{Propósito académico}
    Presentar el tema de la actividad con identidad institucional UCNL, orden visual y una ruta de comprensión clara.
  \end{block}
  \begin{itemize}
    \item Delimitar el problema o concepto central.
    \item Identificar el producto solicitado y sus criterios de cumplimiento.
    \item Conectar desarrollo, evidencia y postura personal.
  \end{itemize}
\end{frame}

\begin{frame}{Ejes de desarrollo}
  \begin{columns}[T,totalwidth=\textwidth]
    \begin{column}{0.48\textwidth}
      \begin{block}{Contenido}
        Conceptos clave, categorías de análisis y relaciones principales.
      \end{block}
    \end{column}
    \begin{column}{0.48\textwidth}
      \begin{block}{Producto}
        Cuadro, esquema, cuestionario, matriz o síntesis solicitada por la actividad.
      \end{block}
    \end{column}
  \end{columns}
\end{frame}

\begin{frame}{Cierre académico}
  \begin{block}{Postura y aprendizaje}
    La conclusión debe explicar qué se comprendió, por qué importa y cómo se vincula con la formación profesional.
  \end{block}
  \begin{itemize}
    \item Hallazgo central.
    \item Interpretación propia.
    \item Consecuencia o aplicación.
  \end{itemize}
\end{frame}
'@

    if ($text -notmatch 'Ruta editorial UCNL') {
        $text = $text -replace '\\end\{document\}\s*$', "$supportFrames`r`n\end{document}"
    }

    if ($text -ne $original) {
        $backup = "$path.ucnl-theme.bak"
        if (-not (Test-Path $backup)) { $original | Set-Content -Path $backup -Encoding UTF8 }
        $text | Set-Content -Path $path -Encoding UTF8
        return [pscustomobject]@{ Target=$Target; Applied=$true; Reason='ucnl-theme-and-support-frames' }
    }
    return [pscustomobject]@{ Target=$Target; Applied=$false; Reason='already-upgraded' }
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
        $safe = Get-SafeLogName $target
        $patchPath = Join-Path $PatchDir "$safe.deterministic-theme.md"
        if (-not $SkipLlmPresentationPatch) {
            foreach ($engineName in $Engine) {
                $prompt = New-PresentationImprovementPrompt -Target $target -EngineName $engineName
                $engineSafe = ($engineName -replace '[^A-Za-z0-9_.-]', '_')
                $promptPath = Join-Path $PatchDir "$safe.$engineSafe.prompt.md"
                $patchPath = Join-Path $PatchDir "$safe.$engineSafe.llm.md"
                $prompt | Set-Content -Path $promptPath -Encoding UTF8
                $outputLimit = Get-OutputTokenLimit $engineName
                $results.Add((Invoke-AulaTeXPromptFile -Name "presentation-$safe-$engineSafe" -PromptPath $promptPath -EngineName $engineName -PromptMaxTokens $outputLimit))
                $last = $results[$results.Count - 1]
                if ($last.ExitCode -eq 0) {
                    Get-Content -Raw -Encoding UTF8 (Join-Path $RepoRoot $last.Stdout) | Set-Content -Path $patchPath -Encoding UTF8
                    break
                }
            }
        }
        if ($Apply) {
            $themeResult = Apply-UcnlPresentationTheme -Target $target
            ("{0}: {1}" -f $themeResult.Target, $themeResult.Reason) | Set-Content -Path $patchPath -Encoding UTF8
            $results.Add([pscustomobject]@{
                Name = "apply-theme-$safe"
                ExitCode = if ($themeResult.Applied -or $themeResult.Reason -eq 'already-upgraded') { 0 } else { 1 }
                Stdout = (Get-RelativePath $patchPath)
                Stderr = $themeResult.Reason
            })
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
    $targets = @($Audit.Issues | Where-Object { $_.Kind -in @('pdf-faltante','pdf-desactualizado') } | Select-Object -ExpandProperty Target -Unique)
    if ($targets.Count -eq 0) {
        $targets = @($Audit.Issues | Where-Object { $_.Kind -like 'reporte-*' -or $_.Kind -like 'presentacion-*' } | Select-Object -ExpandProperty Target -Unique)
    }
    if (-not $AllTex -and $MaxCompileNodes -gt 0) { $targets = @($targets | Select-Object -First $MaxCompileNodes) }
    foreach ($target in $targets) {
        [void](Ensure-CanonicalBibliographyEntries -Target $target)
        $results.Add((Invoke-LoggedCommand -Name ('compile-' + ($target -replace '[^A-Za-z0-9_.-]', '_')) -FilePath $LatexBuild -Arguments @($target)))
    }
    return @($results.ToArray())
}

function Get-ImprovementScore {
    param(
        [Parameter(Mandatory)]$AuditBefore,
        [Parameter(Mandatory)]$AuditAfter
    )
    $before = [double]($AuditBefore.Summary.issue_total)
    $after = [double]($AuditAfter.Summary.issue_total)
    if ($before -le 0) { return 100.0 }
    return [Math]::Round((($before - $after) / $before) * 100.0, 2)
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
    }

    $auditAfter = if ($Execute) { Invoke-UcnlAudit -CycleDir (Join-Path $cycleDir 'after') } else { $null }
    $improvementScore = if ($null -ne $auditAfter) { Get-ImprovementScore -AuditBefore $auditBefore -AuditAfter $auditAfter } else { 0.0 }

    if ($Execute -and $Compile -and $null -ne $auditAfter -and $improvementScore -ge $MinimumImprovementPercent) {
        foreach ($item in @(Invoke-CompileCycle -Audit $auditAfter -CycleDir $cycleDir)) { $runs.Add($item) }
    }

    $cycleRecords.Add([pscustomobject]@{
        cycle = $cycle
        audit_before = $auditBefore.Json
        audit_after = if ($null -ne $auditAfter) { $auditAfter.Json } else { '' }
        issue_total_before = $auditBefore.Summary.issue_total
        issue_total_after = if ($null -ne $auditAfter) { $auditAfter.Summary.issue_total } else { $null }
        improvement_percent = $improvementScore
        compile_gate_threshold = $MinimumImprovementPercent
        compile_gate_passed = ($improvementScore -ge $MinimumImprovementPercent)
        runs = @($runs.ToArray())
    })
}

$manifestPath = Join-Path $CycleRoot 'manifest.json'
$reportPath = Join-Path $CycleRoot 'reporte-ciclo-ucnl.md'
$baselinePath = Join-Path $OutputPath 'quality-baseline.json'
$engineLimitManifest = @{}
foreach ($engineName in $Engine) {
    $engineLimitManifest[$engineName] = Get-EngineLimit $engineName
}

$manifest = [pscustomobject]@{
    timestamp = (Get-Date).ToString('s')
    root = Get-RelativePath $RootPath
    execute = [bool]$Execute
    apply = [bool]$Apply
    engines = @($Engine)
    engine_limits = $engineLimitManifest
    max_tokens_requested = $MaxTokens
    cycles = @($cycleRecords.ToArray())
}

if ($cycleRecords.Count -gt 0) {
    $last = $cycleRecords[$cycleRecords.Count - 1]
    $baseline = [pscustomobject]@{
        timestamp = (Get-Date).ToString('s')
        issue_total_before = $last.issue_total_before
        issue_total_after = $last.issue_total_after
        improvement_percent = $last.improvement_percent
    }
    $baseline | ConvertTo-Json -Depth 4 | Set-Content -Path $baselinePath -Encoding UTF8
}
$manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $manifestPath -Encoding UTF8

$md = New-Object System.Collections.Generic.List[string]
$md.Add('# Ciclo editorial UCNL')
$md.Add('')
$md.Add("- Fecha: $($manifest.timestamp)")
$md.Add("- Raiz: $($manifest.root)")
$md.Add("- Execute: $Execute")
$md.Add("- Apply: $Apply")
$md.Add("- RunReportLlmRevision: $RunReportLlmRevision")
$md.Add("- SkipActivityMonitor: $SkipActivityMonitor")
$md.Add("- Motores: $($Engine -join ', ')")
$md.Add("- MaxTokens solicitado: $MaxTokens; salida efectiva por motor: max 128000 salvo motor desconocido")
$md.Add('')
$md.Add('## Límites LLM aplicados')
foreach ($engineName in $Engine) {
    $limit = Get-EngineLimit $engineName
    $md.Add("- $engineName / $($limit.Deployment): contexto=$($limit.Context), input=$($limit.Input), output=$($limit.Output), promptBudget=$($limit.PromptBudget)")
}
$md.Add('')
foreach ($record in $cycleRecords) {
    $md.Add("## Ciclo $($record.cycle)")
    $md.Add("- Auditoria inicial: $($record.audit_before)")
    if ($record.audit_after) { $md.Add("- Auditoria posterior: $($record.audit_after)") }
    $md.Add("- Issues antes: $($record.issue_total_before)")
    if ($null -ne $record.issue_total_after) { $md.Add("- Issues despues: $($record.issue_total_after)") }
    $md.Add("- Mejora porcentual: $($record.improvement_percent)%")
    $md.Add("- Compile gate: $($record.compile_gate_passed) (umbral=$($record.compile_gate_threshold)%)")
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
Write-Host "engines=$($Engine -join ', ')"
Write-Host "effective_output_cap=128000"
