param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$entry = Join-Path $PSScriptRoot 'aulatex_agent.py'
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'

$pythonCmd = if (Test-Path $venvPython) {
    $venvPython
}
else {
    'python'
}

if (($null -eq $CommandArgs) -or ($CommandArgs.Count -eq 0)) {
    & $pythonCmd $entry gui
}
elseif ($CommandArgs[0] -in @('monitor-inteligente', 'motor-inteligente-monitor')) {
    # Atajo al monitor visual del motor inteligente (barra de avance en vivo).
    # El array splatting de PowerShell NO reconoce nombres de parámetro (trata
    # todo como posicional), así que convertimos "-Nombre valor" y "-Switch" en
    # un hashtable de splatting, que sí respeta los nombres del script destino.
    $monitor = Join-Path $PSScriptRoot 'motor-inteligente-monitor.ps1'
    $switchParams = @('Plan', 'Gui', 'Console')
    $params = @{}
    $i = 1
    while ($i -lt $CommandArgs.Count) {
        $token = [string]$CommandArgs[$i]
        if ($token -match '^-{1,2}(.+)$') {
            $name = $matches[1]
            $isSwitch = $switchParams -contains $name
            if ($isSwitch) {
                $params[$name] = $true
                $i++
            }
            elseif (($i + 1) -lt $CommandArgs.Count -and ([string]$CommandArgs[$i + 1]) -notmatch '^-{1,2}[A-Za-z]') {
                $params[$name] = [string]$CommandArgs[$i + 1]
                $i += 2
            }
            else {
                # Bandera sin valor explícito: se trata como switch/booleana.
                $params[$name] = $true
                $i++
            }
        }
        else {
            $i++
        }
    }
    & $monitor @params
    exit $LASTEXITCODE
}
elseif ($CommandArgs[0] -in @('contractualizar-tecnicas', 'contractualize-techniques')) {
    # Contractualiza las 100 Técnicas Didácticas con la fuente oficial UnADM:
    # fascículos PDF (referencias-aulatex) + sitio oficial (printdata.php).
    # Flags: -Refresh (redescargar web), -NoFasciculos, -Cycles N.
    $enricher = Join-Path $PSScriptRoot 'aulatex\didactic_enricher.py'
    $pyArgs = @($enricher)
    $i = 1
    while ($i -lt $CommandArgs.Count) {
        $token = [string]$CommandArgs[$i]
        switch -Regex ($token) {
            '^-{1,2}[Rr]efresh$' { $pyArgs += '--refresh'; $i++ }
            '^-{1,2}[Nn]o[Ff]asciculos$' { $pyArgs += '--no-fasciculos'; $i++ }
            '^-{1,2}[Cc]ycles$' {
                if (($i + 1) -lt $CommandArgs.Count) { $pyArgs += @('--cycles', [string]$CommandArgs[$i + 1]); $i += 2 }
                else { $i++ }
            }
            default { $i++ }
        }
    }
    & $pythonCmd @pyArgs
    exit $LASTEXITCODE
}
elseif ($CommandArgs[0] -in @('consolidar-construccion', 'consolidate-construction')) {
    # Consolida por técnica: patrón TikZ/LaTeX + rúbrica de puntuación + integración
    # con realizar-actividad, en N ciclos con convergencia.
    # Flags: -Cycles N (def 10), -Only id1 id2 ... (piloto), -Llm (refinar con LLM).
    $consolidator = Join-Path $PSScriptRoot 'aulatex\didactic_builder_consolidator.py'
    $pyArgs = @($consolidator)
    $i = 1
    while ($i -lt $CommandArgs.Count) {
        $token = [string]$CommandArgs[$i]
        switch -Regex ($token) {
            '^-{1,2}[Cc]ycles$' {
                if (($i + 1) -lt $CommandArgs.Count) { $pyArgs += @('--cycles', [string]$CommandArgs[$i + 1]); $i += 2 }
                else { $i++ }
            }
            '^-{1,2}[Ll]lm$' { $pyArgs += '--llm'; $i++ }
            '^-{1,2}[Oo]nly$' {
                $pyArgs += '--only'; $i++
                while ($i -lt $CommandArgs.Count -and ([string]$CommandArgs[$i]) -notmatch '^-{1,2}[A-Za-z]') {
                    $pyArgs += [string]$CommandArgs[$i]; $i++
                }
            }
            default { $i++ }
        }
    }
    & $pythonCmd @pyArgs
    exit $LASTEXITCODE
}
elseif ($CommandArgs[0] -in @('escanear-productos', 'scan-products')) {
    # Escanea todos los reporte-*Actividad*.tex y clasifica los PRODUCTOS de
    # actividad completados por técnica didáctica. Escribe
    # aulaTEX/base/.../productos-actividad.json que didactic_catalog adjunta a cada técnica.
    $scanner = Join-Path $PSScriptRoot 'aulatex\productos_actividad.py'
    $pyArgs = @($scanner)
    if (($CommandArgs -contains '-Quiet') -or ($CommandArgs -contains '--quiet')) { $pyArgs += '--quiet' }
    & $pythonCmd @pyArgs
    exit $LASTEXITCODE
}
else {
    & $pythonCmd $entry @CommandArgs
}
