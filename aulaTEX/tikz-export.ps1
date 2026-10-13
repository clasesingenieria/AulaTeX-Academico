param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$TexFile,

    [ValidateSet('all', 'pdf', 'svg', 'png')]
    [string]$Format = 'all',

    [int]$Dpi = 300
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$BuildScript = Join-Path $PSScriptRoot 'latexmk-build.ps1'

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $BuildScript $TexFile
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$ResolvedTex = if ([System.IO.Path]::IsPathRooted($TexFile)) {
    Resolve-Path -LiteralPath $TexFile
}
else {
    Resolve-Path -LiteralPath (Join-Path (Get-Location) $TexFile) -ErrorAction SilentlyContinue
}
if (-not $ResolvedTex) {
    $ResolvedTex = Resolve-Path -LiteralPath (Join-Path $ProjectRoot $TexFile)
}

$BaseName = [System.IO.Path]::GetFileNameWithoutExtension($ResolvedTex.Path)
$OutputDir = Split-Path -Parent $ResolvedTex.Path
$PdfSource = Join-Path $OutputDir "$BaseName.pdf"
if (-not (Test-Path -LiteralPath $PdfSource)) {
    throw "No se encontro el PDF esperado: $PdfSource"
}

if ($Format -in @('all', 'svg')) {
    $SvgTarget = Join-Path $OutputDir "$BaseName.svg"
    if (Get-Command inkscape -ErrorAction SilentlyContinue) {
        & inkscape $PdfSource --export-type=svg --export-filename=$SvgTarget
    }
    else {
        throw 'Inkscape no esta disponible para exportar SVG.'
    }
}

if ($Format -in @('all', 'png')) {
    $PngTarget = Join-Path $OutputDir "$BaseName.png"
    if (Get-Command inkscape -ErrorAction SilentlyContinue) {
        & inkscape $PdfSource --export-type=png --export-dpi=$Dpi --export-filename=$PngTarget
    }
    else {
        throw 'Inkscape no esta disponible para exportar PNG.'
    }
}
