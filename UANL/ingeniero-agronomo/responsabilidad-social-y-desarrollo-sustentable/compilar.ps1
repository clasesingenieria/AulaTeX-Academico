[CmdletBinding()]
param(
    [ValidateSet('reporte', 'presentacion', 'todos')]
    [string]$Documento = 'todos'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$relativeSubject = 'UANL/ingeniero-agronomo/responsabilidad-social-y-desarrollo-sustentable'
$suffix = 'responsabilidad-social-y-desarrollo-sustentable-Actividad-1'
$output = '.build/latex/uanl-rsds'
$latexmk = (Get-Command latexmk -ErrorAction Stop).Source
$texBin = Split-Path -Parent $latexmk
$texRoot = Split-Path -Parent (Split-Path -Parent $texBin)
$perlBin = Join-Path $texRoot 'tlpkg/tlperl/bin'
$previous = @{}
foreach ($name in @('PATH', 'TEXINPUTS', 'BIBINPUTS', 'BSTINPUTS')) {
    $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

Push-Location $repoRoot
try {
    $env:PATH = "$texBin;$perlBin;$env:PATH"
    foreach ($name in @('TEXINPUTS', 'BIBINPUTS', 'BSTINPUTS')) {
        [Environment]::SetEnvironmentVariable($name, $null, 'Process')
    }
    $subjectInputs = $PSScriptRoot.Replace('\', '/')
    $templateInputs = (Join-Path $repoRoot 'base/Plantilla-Informe').Replace('\', '/')
    $env:TEXINPUTS = ".;$subjectInputs;$templateInputs;"
    $documents = if ($Documento -eq 'todos') { @('reporte', 'presentacion') } else { @($Documento) }
    foreach ($kind in $documents) {
        $stem = "$kind-$suffix"
        & $latexmk -norc -xelatex -g -interaction=nonstopmode -halt-on-error "-outdir=$output" "$relativeSubject/$stem.tex"
        if ($LASTEXITCODE -ne 0) { throw "latexmk fallo para $kind con codigo $LASTEXITCODE" }
        $pdf = Get-Item -LiteralPath (Join-Path $output "$stem.pdf")
        $source = Get-Item -LiteralPath (Join-Path $PSScriptRoot "$stem.tex")
        if ($pdf.Length -eq 0 -or $pdf.LastWriteTimeUtc -lt $source.LastWriteTimeUtc) {
            throw "El PDF no es valido o no esta actualizado: $stem"
        }
        Copy-Item -LiteralPath $pdf.FullName -Destination (Join-Path $PSScriptRoot "$stem.pdf") -Force
        Write-Output "PDF verificado: $relativeSubject/$stem.pdf"
    }
}
finally {
    foreach ($name in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
    }
    Pop-Location
}
