param(
    [string[]]$Engine = @(),
    [int[]]$InputCharTargets = @(4096, 16384, 65536),
    [int[]]$OutputTokenTargets = @(256, 1024, 4096, 8192),
    [int]$TimeoutSeconds = 240,
    [string]$Target = '.',
    [ValidateSet('langgraph', 'classic')]
    [string]$Backend = 'langgraph',
    [switch]$UseIntelligentEngine,
    [string]$OutputRoot = '.aulatex-temp/llm-limit-probe',
    [switch]$ContinueAfterFailure
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$aulatexScript = Join-Path $repoRoot 'aulaTEX\aulatex.ps1'
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runDir = Join-Path $repoRoot (Join-Path $OutputRoot (Join-Path 'runs' $timestamp))
$promptsDir = Join-Path $runDir 'prompts'
$rawDir = Join-Path $runDir 'raw'

New-Item -ItemType Directory -Path $promptsDir -Force | Out-Null
New-Item -ItemType Directory -Path $rawDir -Force | Out-Null

$referenceLimits = [ordered]@{
    'Codex' = [ordered]@{
        deployment = 'gpt-5.3-codex'
        official_context_tokens = 400000
        official_input_tokens = 272000
        official_output_tokens = 128000
    }
    'Auto (model-router)' = [ordered]@{
        deployment = 'model-router'
        official_context_tokens = 200000
        official_input_tokens = 200000
        official_output_tokens = 128000
        note = 'El limite de salida real depende del modelo que el router seleccione.'
    }
    'GPT-Pro' = [ordered]@{
        deployment = 'gpt-5.4-pro'
        official_context_tokens = 1050000
        official_input_tokens = 922000
        official_output_tokens = 128000
    }
    'Claude Foundry' = [ordered]@{
        deployment = 'claude-opus-4-8'
        official_context_tokens = 1000000
        official_input_tokens = 1000000
        official_output_tokens = 128000
    }
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $directory = Split-Path -Parent $Path
    if ($directory) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Invoke-AulaTeX {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [string]$RawOutputPath = ''
    )

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $savedErrorActionPreference = $ErrorActionPreference
    $savedNativePreference = $null
    $hasNativePreference = $false
    $output = ''

    try {
        $ErrorActionPreference = 'Continue'
        if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
            $hasNativePreference = $true
            $savedNativePreference = $PSNativeCommandUseErrorActionPreference
            $PSNativeCommandUseErrorActionPreference = $false
        }

        $output = & $aulatexScript @Arguments 2>&1 | Out-String
    }
    catch {
        $output = $_ | Out-String
    }
    finally {
        if ($hasNativePreference) {
            $PSNativeCommandUseErrorActionPreference = $savedNativePreference
        }
        $ErrorActionPreference = $savedErrorActionPreference
        $stopwatch.Stop()
    }

    $exitCode = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }

    if ($RawOutputPath) {
        Write-Utf8NoBom -Path $RawOutputPath -Content $output
    }

    [pscustomobject]@{
        ExitCode = $exitCode
        Output = $output.Trim()
        DurationMs = [int]$stopwatch.ElapsedMilliseconds
        Ok = ($exitCode -eq 0)
    }
}

function New-RepeatedBody {
    param(
        [Parameter(Mandatory = $true)]
        [int]$TargetChars,
        [Parameter(Mandatory = $true)]
        [string]$Seed
    )

    if ($TargetChars -le 0) {
        return ''
    }

    $builder = New-Object System.Text.StringBuilder
    while ($builder.Length -lt $TargetChars) {
        [void]$builder.Append($Seed)
    }
    return $builder.ToString(0, [Math]::Min($TargetChars, $builder.Length))
}

function New-InputPrompt {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ApproxChars
    )

    $header = @(
        'Prueba de limite de entrada para AulaTeX.',
        'Responde exactamente con OK.',
        'No agregues explicacion.',
        ''
    ) -join [Environment]::NewLine
    $seed = 'Bloque de relleno AulaTeX para validar contexto. 0123456789 abcdefghijklmnopqrstuvwxyz. '
    $remaining = [Math]::Max(0, $ApproxChars - $header.Length)
    return $header + (New-RepeatedBody -TargetChars $remaining -Seed $seed)
}

function New-OutputPrompt {
    param(
        [Parameter(Mandatory = $true)]
        [int]$RequestedMaxTokens
    )

    return @(
        'Prueba de limite de salida para AulaTeX.',
        "Intenta usar una respuesta extensa cercana a $RequestedMaxTokens tokens.",
        'Produce lineas numeradas consecutivas con texto breve y sin markdown.',
        'Deten la salida solo cuando ya no puedas continuar.'
    ) -join [Environment]::NewLine
}

function Get-TokenCountResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EngineName,
        [Parameter(Mandatory = $true)]
        [string]$PromptFile
    )

    $tokenize = Invoke-AulaTeX -Arguments @(
        'llm-tokenize',
        '--engine', $EngineName,
        '--prompt-file', $PromptFile
    )

    if (-not $tokenize.Ok) {
        throw ("No se pudo tokenizar el prompt para {0}: {1}" -f $EngineName, $tokenize.Output)
    }

    return $tokenize.Output | ConvertFrom-Json -ErrorAction Stop
}

$defaultEngines = @('Codex', 'Auto (model-router)', 'GPT-Pro', 'Claude Foundry')
$selectedEngines = if ($Engine.Count -gt 0) { $Engine } else { $defaultEngines }

$envStatus = Invoke-AulaTeX -Arguments @('llm-env') -RawOutputPath (Join-Path $rawDir 'llm-env.txt')
$checkStatus = Invoke-AulaTeX -Arguments @('llm-check') -RawOutputPath (Join-Path $rawDir 'llm-check.txt')

$availableEngines = @()
foreach ($line in ($checkStatus.Output -split "`r?`n")) {
    if ($line -match '^(?<engine>.+?):\s+OK\b') {
        $availableEngines += $Matches['engine'].Trim()
    }
}

if ($availableEngines.Count -eq 0) {
    throw 'No se detectaron motores LLM disponibles despues de llm-check.'
}

$selectedEngines = @($selectedEngines | Where-Object { $_ -in $availableEngines })
if ($selectedEngines.Count -eq 0) {
    throw 'Los motores solicitados no estan disponibles segun llm-check.'
}

$intelligentEngineInfo = $null
if ($UseIntelligentEngine) {
    $intelligentRawPath = Join-Path $rawDir 'intelligent-engine.txt'
    $intelligentArgs = @(
        'intelligent-engine',
        '--target', $Target,
        '--backend', $Backend,
        '--max-targets', '1',
        '--output', (Join-Path $runDir 'intelligent-engine')
    )
    foreach ($engineName in $selectedEngines) {
        $intelligentArgs += @('--engine', $engineName)
    }
    $intelligentInvoke = Invoke-AulaTeX -Arguments $intelligentArgs -RawOutputPath $intelligentRawPath
    $intelligentParsed = $null
    if ($intelligentInvoke.Ok -and $intelligentInvoke.Output) {
        try {
            $intelligentParsed = $intelligentInvoke.Output | ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            $intelligentParsed = $null
        }
    }
    $intelligentEngineInfo = [pscustomobject]@{
        ok = $intelligentInvoke.Ok
        exit_code = $intelligentInvoke.ExitCode
        duration_ms = $intelligentInvoke.DurationMs
        output = $intelligentInvoke.Output
        parsed = $intelligentParsed
    }
}

$results = New-Object System.Collections.Generic.List[object]

foreach ($engineName in $selectedEngines) {
    $engineSlug = ($engineName -replace '[^a-zA-Z0-9]+', '-').Trim('-').ToLowerInvariant()

    foreach ($inputChars in $InputCharTargets) {
        $prompt = New-InputPrompt -ApproxChars $inputChars
        $promptPath = Join-Path $promptsDir ("{0}-input-{1}.txt" -f $engineSlug, $inputChars)
        $rawPath = Join-Path $rawDir ("{0}-input-{1}.txt" -f $engineSlug, $inputChars)
        Write-Utf8NoBom -Path $promptPath -Content $prompt
        $promptTokenInfo = Get-TokenCountResult -EngineName $engineName -PromptFile $promptPath

        $invoke = Invoke-AulaTeX -Arguments @(
            'llm-prompt',
            '--engine', $engineName,
            '--max-tokens', '32',
            '--timeout-seconds', [string]$TimeoutSeconds,
            '--prompt-file', $promptPath
        ) -RawOutputPath $rawPath

        $result = [pscustomobject]@{
            engine = $engineName
            phase = 'input'
            ok = $invoke.Ok
            exit_code = $invoke.ExitCode
            duration_ms = $invoke.DurationMs
            prompt_file = $promptPath
            raw_output_file = $rawPath
            requested_prompt_chars = $inputChars
            actual_prompt_chars = $prompt.Length
            prompt_token_count = $promptTokenInfo.token_count
            prompt_tokenizer_source = $promptTokenInfo.tokenizer_source
            prompt_tokenizer_name = $promptTokenInfo.tokenizer_name
            prompt_tokenizer_approximate = $promptTokenInfo.approximate
            prompt_tokenizer_note = $promptTokenInfo.note
            requested_max_tokens = 32
            observed_response_chars = $invoke.Output.Length
            observed_response_tokens = if ($invoke.Ok -and $invoke.Output.Length -gt 0) {
                $responsePromptPath = Join-Path $promptsDir ("{0}-input-{1}-response.txt" -f $engineSlug, $inputChars)
                Write-Utf8NoBom -Path $responsePromptPath -Content $invoke.Output
                (Get-TokenCountResult -EngineName $engineName -PromptFile $responsePromptPath).token_count
            }
            else { 0 }
            output_preview = if ($invoke.Output.Length -gt 240) { $invoke.Output.Substring(0, 240) } else { $invoke.Output }
        }
        $results.Add($result) | Out-Null

        if ((-not $invoke.Ok) -and (-not $ContinueAfterFailure)) {
            break
        }
    }

    foreach ($outputTokens in $OutputTokenTargets) {
        $prompt = New-OutputPrompt -RequestedMaxTokens $outputTokens
        $promptPath = Join-Path $promptsDir ("{0}-output-{1}.txt" -f $engineSlug, $outputTokens)
        $rawPath = Join-Path $rawDir ("{0}-output-{1}.txt" -f $engineSlug, $outputTokens)
        Write-Utf8NoBom -Path $promptPath -Content $prompt
        $promptTokenInfo = Get-TokenCountResult -EngineName $engineName -PromptFile $promptPath

        $invoke = Invoke-AulaTeX -Arguments @(
            'llm-prompt',
            '--engine', $engineName,
            '--max-tokens', [string]$outputTokens,
            '--timeout-seconds', [string]$TimeoutSeconds,
            '--prompt-file', $promptPath
        ) -RawOutputPath $rawPath

        $result = [pscustomobject]@{
            engine = $engineName
            phase = 'output'
            ok = $invoke.Ok
            exit_code = $invoke.ExitCode
            duration_ms = $invoke.DurationMs
            prompt_file = $promptPath
            raw_output_file = $rawPath
            requested_prompt_chars = $prompt.Length
            actual_prompt_chars = $prompt.Length
            prompt_token_count = $promptTokenInfo.token_count
            prompt_tokenizer_source = $promptTokenInfo.tokenizer_source
            prompt_tokenizer_name = $promptTokenInfo.tokenizer_name
            prompt_tokenizer_approximate = $promptTokenInfo.approximate
            prompt_tokenizer_note = $promptTokenInfo.note
            requested_max_tokens = $outputTokens
            observed_response_chars = $invoke.Output.Length
            observed_response_tokens = if ($invoke.Ok -and $invoke.Output.Length -gt 0) {
                $responsePromptPath = Join-Path $promptsDir ("{0}-output-{1}-response.txt" -f $engineSlug, $outputTokens)
                Write-Utf8NoBom -Path $responsePromptPath -Content $invoke.Output
                (Get-TokenCountResult -EngineName $engineName -PromptFile $responsePromptPath).token_count
            }
            else { 0 }
            output_preview = if ($invoke.Output.Length -gt 240) { $invoke.Output.Substring(0, 240) } else { $invoke.Output }
        }
        $results.Add($result) | Out-Null

        if ((-not $invoke.Ok) -and (-not $ContinueAfterFailure)) {
            break
        }
    }
}

$summary = foreach ($engineName in $selectedEngines) {
    $engineResults = @($results | Where-Object { $_.engine -eq $engineName })
    $inputSuccess = @($engineResults | Where-Object { $_.phase -eq 'input' -and $_.ok } | Sort-Object requested_prompt_chars)
    $outputSuccess = @($engineResults | Where-Object { $_.phase -eq 'output' -and $_.ok } | Sort-Object requested_max_tokens)
    $inputFailure = @($engineResults | Where-Object { $_.phase -eq 'input' -and -not $_.ok } | Sort-Object requested_prompt_chars | Select-Object -First 1)
    $outputFailure = @($engineResults | Where-Object { $_.phase -eq 'output' -and -not $_.ok } | Sort-Object requested_max_tokens | Select-Object -First 1)
    $largestOutputObserved = @($outputSuccess | Sort-Object observed_response_tokens)

    [pscustomobject]@{
        engine = $engineName
        deployment = if ($referenceLimits.Contains($engineName)) { $referenceLimits[$engineName].deployment } else { '' }
        largest_successful_input_chars = if ($inputSuccess.Count -gt 0) { ($inputSuccess[-1]).actual_prompt_chars } else { 0 }
        largest_successful_input_tokens = if ($inputSuccess.Count -gt 0) { ($inputSuccess[-1]).prompt_token_count } else { 0 }
        input_tokenizer = if ($inputSuccess.Count -gt 0) { ($inputSuccess[-1]).prompt_tokenizer_name } else { '' }
        input_tokenizer_approximate = if ($inputSuccess.Count -gt 0) { ($inputSuccess[-1]).prompt_tokenizer_approximate } else { $true }
        first_failed_input_chars = if ($inputFailure.Count -gt 0) { ($inputFailure[0]).actual_prompt_chars } else { 0 }
        largest_accepted_max_tokens = if ($outputSuccess.Count -gt 0) { ($outputSuccess[-1]).requested_max_tokens } else { 0 }
        largest_observed_output_tokens = if ($largestOutputObserved.Count -gt 0) { ($largestOutputObserved[-1]).observed_response_tokens } else { 0 }
        first_rejected_max_tokens = if ($outputFailure.Count -gt 0) { ($outputFailure[0]).requested_max_tokens } else { 0 }
    }
}

$payload = [ordered]@{
    kind = 'llm-limit-probe'
    version = 1
    generated_at = (Get-Date).ToString('o')
    repo_root = [string]$repoRoot
    run_dir = $runDir
    target = $Target
    backend = $Backend
    selected_engines = $selectedEngines
    preflight = [ordered]@{
        env = [ordered]@{
            ok = $envStatus.Ok
            exit_code = $envStatus.ExitCode
            duration_ms = $envStatus.DurationMs
            output = $envStatus.Output
        }
        check = [ordered]@{
            ok = $checkStatus.Ok
            exit_code = $checkStatus.ExitCode
            duration_ms = $checkStatus.DurationMs
            output = $checkStatus.Output
        }
    }
    intelligent_engine = $intelligentEngineInfo
    references = [ordered]@{
        limits = $referenceLimits
        note = 'Las pruebas siguen generando prompts por caracteres objetivo, pero el conteo reportado usa tokenizacion Python local por motor con notas de aproximacion cuando aplica.'
    }
    probes = [ordered]@{
        input_char_targets = $InputCharTargets
        output_token_targets = $OutputTokenTargets
        timeout_seconds = $TimeoutSeconds
    }
    summary = $summary
    results = $results
}

$jsonPath = Join-Path $runDir 'results.json'
$mdPath = Join-Path $runDir 'summary.md'
$payloadJson = $payload | ConvertTo-Json -Depth 8
Write-Utf8NoBom -Path $jsonPath -Content $payloadJson

$markdown = New-Object System.Text.StringBuilder
[void]$markdown.AppendLine('# Limites LLM AulaTeX')
[void]$markdown.AppendLine()
[void]$markdown.AppendLine("Run dir: $runDir")
[void]$markdown.AppendLine()
[void]$markdown.AppendLine('## Resumen')
[void]$markdown.AppendLine()
[void]$markdown.AppendLine('| Motor | Deployment | Mayor entrada exitosa (chars) | Entrada tokenizada | Tokenizador | Mayor max_tokens aceptado | Mayor salida observada | Primer rechazo input | Primer rechazo output |')
[void]$markdown.AppendLine('| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |')
foreach ($row in $summary) {
    $tokenizerLabel = if ($row.input_tokenizer_approximate) { "$($row.input_tokenizer) (aprox.)" } else { [string]$row.input_tokenizer }
    [void]$markdown.AppendLine(("| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8} |" -f $row.engine, $row.deployment, $row.largest_successful_input_chars, $row.largest_successful_input_tokens, $tokenizerLabel, $row.largest_accepted_max_tokens, $row.largest_observed_output_tokens, $row.first_failed_input_chars, $row.first_rejected_max_tokens))
}
[void]$markdown.AppendLine()
[void]$markdown.AppendLine('## Notas')
[void]$markdown.AppendLine()
[void]$markdown.AppendLine('- Las pruebas de entrada usan prompts por archivo para evitar el limite de longitud de linea de comandos en Windows.')
[void]$markdown.AppendLine('- El conteo de tokens reportado usa `aulatex llm-tokenize`, respaldado por `tiktoken` con el perfil `o200k_base`.')
[void]$markdown.AppendLine('- `Codex` y `GPT-Pro` usan conteo local de la familia GPT; `Auto (model-router)` y `Claude Foundry` quedan marcados como aproximacion porque su backend efectivo puede variar o no expone un tokenizer local equivalente en el repo.')
[void]$markdown.AppendLine('- `intelligent-engine` se usa solo como apoyo de inventario/contexto; no ejecuta prompts LLM por si mismo en esta ruta.')
Write-Utf8NoBom -Path $mdPath -Content $markdown.ToString()

Write-Host "Run dir: $runDir"
Write-Host "JSON:    $jsonPath"
Write-Host "Summary: $mdPath"
$summary | Format-Table -AutoSize | Out-String | Write-Host