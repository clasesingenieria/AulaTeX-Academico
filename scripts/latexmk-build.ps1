param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$TexFile,

    [ValidateSet('none', 'safe', 'full')]
    [string]$CleanMode = 'safe',

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$LatexmkArgs
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Initialize-PerlForLatexmk {
    <#
    .SYNOPSIS
        Antepone un Perl COMPLETO al PATH para que latexmk pueda arrancar.
    .DESCRIPTION
        latexmk es un script Perl y necesita la biblioteca estandar
        (File::Spec::Functions entre otros). Si en el PATH gana un Perl
        embebido -- el de exiftool de Chocolatey es el caso tipico -- su @INC
        no incluye la stdlib y latexmk aborta en el 'use' inicial con
        "Can't locate File/Spec/Functions.pm in @INC", antes de leer el .tex.
        Se prueban las distribuciones completas habituales y se usa la primera
        que resuelva el modulo.
    #>
    $candidates = @(
        'C:\Strawberry\perl\bin',
        "$env:ProgramFiles\Git\usr\bin",
        "$env:SystemDrive\Perl64\bin"
    )

    # Un Perl incompleto escribe el fallo del 'use' en stderr. Con
    # $ErrorActionPreference='Stop' eso se convierte en NativeCommandError
    # terminante y abortaria el script justo cuando la sonda hace su trabajo.
    # La sonda debe poder fallar en silencio, que es su unico proposito.
    function Test-PerlHasStdlib {
        param([string]$Exe)
        $previous = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & $Exe -e 'use File::Spec::Functions; exit 0' 2>&1 | Out-Null
            return ($LASTEXITCODE -eq 0)
        } catch {
            return $false
        } finally {
            $ErrorActionPreference = $previous
        }
    }

    $current = (Get-Command perl -ErrorAction SilentlyContinue).Source
    if ($current -and (Test-PerlHasStdlib -Exe $current)) { return }

    foreach ($dir in $candidates) {
        $exe = Join-Path $dir 'perl.exe'
        if (-not (Test-Path -LiteralPath $exe)) { continue }
        if (Test-PerlHasStdlib -Exe $exe) {
            $env:PATH = "$dir;$env:PATH"
            Write-Host "Perl para latexmk: $exe"
            return
        }
    }

    Write-Warning "No se encontro un Perl con biblioteca estandar; latexmk puede fallar al arrancar."
}

function Resolve-LatexmkExecutable {
    $executable = 'C:\texlive\2026\bin\windows\latexmk.exe'
    if (Test-Path -LiteralPath $executable -PathType Leaf) {
        return $executable
    }
    throw "Bloqueador de entorno: el proyecto requiere TeX Live 2026 con latexmk en $executable."
}

function Resolve-TexFile {
    param([string]$Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return (Resolve-Path -LiteralPath $Path).Path
    }

    $fromCurrent = Join-Path (Get-Location) $Path
    if (Test-Path -LiteralPath $fromCurrent) {
        return (Resolve-Path -LiteralPath $fromCurrent).Path
    }

    $fromRoot = Join-Path $ProjectRoot $Path
    if (Test-Path -LiteralPath $fromRoot) {
        return (Resolve-Path -LiteralPath $fromRoot).Path
    }

    if ([System.IO.Path]::GetFileName($Path) -eq $Path) {
        $matches = @(Get-ChildItem -LiteralPath $ProjectRoot -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ieq $Path } |
            Sort-Object FullName)

        if ($matches.Count -eq 1) {
            return $matches[0].FullName
        }

        if ($matches.Count -gt 1) {
            $matchList = ($matches | ForEach-Object { $_.FullName }) -join ', '
            throw "Se encontraron varios archivos con el nombre '$Path': $matchList. Usa una ruta mas especifica."
        }
    }

    throw "No se encontro el archivo TeX '$Path'. Se intento desde la carpeta actual y desde la raiz del proyecto."
}

function Invoke-BuildCleanup {
    param(
        [string]$Mode,
        [string]$Root
    )

    if ($Mode -eq 'none') {
        return
    }

    $buildRoot = Join-Path $Root '.build/latex'
    if (-not (Test-Path -LiteralPath $buildRoot -PathType Container)) {
        return
    }

    if ($Mode -eq 'full') {
        Get-ChildItem -LiteralPath $buildRoot -Recurse -File -Force -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
        return
    }

    # Limpieza segura: elimina auxiliares temporales y conserva .log para diagnostico.
    $ephemeralExtensions = @(
        '.aux', '.bbl', '.blg', '.fdb_latexmk', '.fls',
        '.lof', '.lot', '.nav', '.out', '.run.xml', '.snm',
        '.synctex.gz', '.toc', '.vrb', '.xdv'
    )

    Get-ChildItem -LiteralPath $buildRoot -Recurse -File -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $ext = $_.Extension.ToLowerInvariant()
            if ($ext -eq '.gz' -and $_.Name.ToLowerInvariant().EndsWith('.synctex.gz')) {
                return $true
            }
            return $ephemeralExtensions -contains $ext
        } |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

function Remove-SourceDirResidues {
    # Barre residuos de compilacion HUERFANOS que quedaron JUNTO al .tex (fruto de
    # compilaciones manuales pdflatex/bibtex antiguas). El flujo canonico con
    # latexmk aisla todo en .build/latex, asi que la carpeta de la materia debe
    # contener SOLO fuentes (.tex/.bib/.md/.json) + el PDF final. Contractualizado
    # en activity_contract.compilation_rules.no_build_residues.
    param(
        [string]$SourceDir,
        [string]$BaseName
    )

    $residueExtensions = @(
        '.aux', '.bbl', '.blg', '.fdb_latexmk', '.fls', '.lof', '.lot',
        '.nav', '.out', '.run.xml', '.snm', '.toc', '.vrb', '.xdv', '.log'
    )
    Get-ChildItem -LiteralPath $SourceDir -File -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $name = $_.Name.ToLowerInvariant()
            $ext = $_.Extension.ToLowerInvariant()
            # Respaldo del optimizador ya aplicado (obsoleto) y auxiliares del jobname.
            ($name.EndsWith('.synctex.gz')) -or
            ($name.EndsWith('.tex.activity-optimize.bak')) -or
            ($residueExtensions -contains $ext)
        } |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

Initialize-PerlForLatexmk

$LatexmkExe = Resolve-LatexmkExecutable
$LatexmkBin = Split-Path -Parent $LatexmkExe
if ($LatexmkBin) {
    # latexmk debe resolver pdflatex/bibtex desde la misma distribución. Aunque
    # MiKTeX ya aparezca más tarde en PATH, TeX Live o Strawberry pueden ganar y
    # producir una instalación híbrida sin los paquetes de MiKTeX.
    $pathParts = @($env:PATH -split ';' | Where-Object { $_ -and $_ -ine $LatexmkBin })
    $env:PATH = (@($LatexmkBin) + $pathParts) -join ';'
}
$ResolvedTex = Resolve-TexFile $TexFile
$BuildRoot = Join-Path $ProjectRoot '.build'
$LatexRoot = Join-Path $BuildRoot 'latex'
# AUX es un nombre de dispositivo reservado en Windows, incluso como segmento.
# Un nombre descriptivo evita WinError 267 y funciona también en Linux/macOS.
$AuxRoot = Join-Path $LatexRoot 'aux-files'
foreach ($directory in @($BuildRoot, $LatexRoot, $AuxRoot)) {
    if ((Test-Path -LiteralPath $directory) -and -not (Test-Path -LiteralPath $directory -PathType Container)) {
        throw "Bloqueador de entorno: la ruta de compilación existe pero no es un directorio: $directory"
    }
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
        throw "Bloqueador de entorno: no fue posible crear el directorio de compilación: $directory"
    }
}
Invoke-BuildCleanup -Mode $CleanMode -Root $ProjectRoot

Push-Location $ProjectRoot
try {
    # Force mode allows latexmk to complete bibliography passes even when
    # the first pdflatex run reports temporary undefined citations.
    # latexmk writes non-fatal notices to stderr (e.g. "Missing input file
    # '<jobname>.toc'" right after aux files were cleaned; latexmk regenerates the
    # .toc on the next pass). Under $ErrorActionPreference='Stop' any native stderr
    # is promoted to a terminating NativeCommandError, so we relax the preference
    # ONLY around the native latexmk call and rely on $LASTEXITCODE for success.
    $PreviousEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $LatexmkExe -f -pdf -interaction=nonstopmode -file-line-error "-outdir=$LatexRoot" "-auxdir=$AuxRoot" @LatexmkArgs $ResolvedTex 2>&1 |
        ForEach-Object { Write-Host ($_ | Out-String).TrimEnd() }
    $LatexmkExitCode = $LASTEXITCODE
    $ErrorActionPreference = $PreviousEAP
    if ($LatexmkExitCode -ne 0) {
        exit $LatexmkExitCode
    }

    $BaseName = [System.IO.Path]::GetFileNameWithoutExtension($ResolvedTex)
    $GeneratedPdfCandidates = @(
        (Join-Path $LatexRoot ("{0}.pdf" -f $BaseName)),
        (Join-Path $AuxRoot ("{0}.pdf" -f $BaseName))
    )
    $GeneratedPdf = $GeneratedPdfCandidates | Where-Object {
        Test-Path -LiteralPath $_ -PathType Leaf
    } | Select-Object -First 1
    $FinalPdf = Join-Path (Split-Path -Parent $ResolvedTex) ("{0}.pdf" -f $BaseName)

    if (-not $GeneratedPdf) {
        Write-Error "No se encontro el PDF generado en las rutas esperadas: $($GeneratedPdfCandidates -join ', ')"
        exit 1
    }

    Copy-Item -LiteralPath $GeneratedPdf -Destination $FinalPdf -Force
    Invoke-BuildCleanup -Mode $CleanMode -Root $ProjectRoot
    if ($CleanMode -ne 'none') {
        # Barrer residuos huerfanos junto al .tex (compilaciones manuales antiguas)
        # para garantizar que la carpeta de la materia quede limpia. latexmk por si
        # mismo NO deja residuos ahi (usa .build/latex), esto solo limpia herencia.
        Remove-SourceDirResidues -SourceDir (Split-Path -Parent $ResolvedTex) -BaseName $BaseName
    }
    Write-Host "PDF final: $FinalPdf"
    exit 0
}
finally {
    Pop-Location
}
