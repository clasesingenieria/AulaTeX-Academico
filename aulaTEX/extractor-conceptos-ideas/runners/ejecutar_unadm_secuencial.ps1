param(
    [ValidateSet('filosofia-del-derecho', 'redaccion-en-contextos-virtuales', 'etica-y-moral-juridica')]
    [string[]]$Materias = @(
        'filosofia-del-derecho',
        'redaccion-en-contextos-virtuales',
        'etica-y-moral-juridica'
    ),

    [Parameter(Mandatory = $true)]
    [int[]]$Semanas,

    [string]$Motor = 'anthropicfoundry',
    [bool]$Recursivo = $true,
    [switch]$SoloValidar,
    [int]$PlaneacionConceptos = 20,
    [int]$TopK = 12,
    [int]$MaxCitas = 8
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$extractorRoot = Split-Path -Parent $PSScriptRoot
$scriptsRoot = Split-Path -Parent $extractorRoot
$repoRoot = Split-Path -Parent $scriptsRoot
$runnerPath = Join-Path $PSScriptRoot 'ejecutar_planeacion.ps1'

function Get-FullPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return [System.IO.Path]::GetFullPath($Path)
}

function Get-MateriaConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Materia
    )

    $materiaRoot = Get-FullPath (Join-Path $repoRoot (Join-Path 'UnADM' $Materia))

    return [pscustomobject]@{
        Materia = $Materia
        MateriaRoot = $materiaRoot
        PlaneacionesDir = Get-FullPath (Join-Path $materiaRoot ("planeaciones-{0}" -f $Materia))
        FuentesDir = Get-FullPath (Join-Path $materiaRoot (Join-Path ("referencias-{0}" -f $Materia) ("libros-{0}" -f $Materia)))
        SalidaBase = Get-FullPath (Join-Path $materiaRoot ("referencias-{0}" -f $Materia))
    }
}

function Find-PlaneacionFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PlaneacionesDir,

        [Parameter(Mandatory = $true)]
        [int]$Semana
    )

    if (!(Test-Path $PlaneacionesDir)) {
        return $null
    }

    $weekPattern = '(?i)(^|[^0-9])S0?{0}(?!\d)' -f $Semana

    $matches = Get-ChildItem -Path $PlaneacionesDir -File | Where-Object {
        $_.Name -match $weekPattern
    }

    if (!($matches)) {
        return $null
    }

    return $matches |
        Sort-Object @(
            @{ Expression = {
                    switch ($_.Extension.ToLowerInvariant()) {
                        '.pdf' { 0 }
                        '.txt' { 1 }
                        '.md' { 2 }
                        default { 3 }
                    }
                }
            },
            @{ Expression = { $_.Name } }
        ) |
        Select-Object -First 1
}

$jobs = New-Object System.Collections.Generic.List[object]
$skipped = New-Object System.Collections.Generic.List[string]

foreach ($materia in $Materias) {
    $config = Get-MateriaConfig -Materia $materia

    if (!(Test-Path $config.FuentesDir)) {
        $skipped.Add(("{0}: no existe la carpeta de fuentes {1}" -f $materia, $config.FuentesDir))
        continue
    }

    foreach ($semana in ($Semanas | Sort-Object)) {
        $planeacion = Find-PlaneacionFile -PlaneacionesDir $config.PlaneacionesDir -Semana $semana

        if ($null -eq $planeacion) {
            $skipped.Add(("{0} S{1:D2}: no se encontró planeación" -f $materia, $semana))
            continue
        }

        $jobs.Add([pscustomobject]@{
            Materia = $materia
            Semana = $semana
            Fuentes = $config.FuentesDir
            Planeacion = $planeacion.FullName
            Salida = Join-Path $config.SalidaBase ("conceptos-{0}-S{1:D2}" -f $materia, $semana)
        })
    }
}

if ($jobs.Count -eq 0) {
    throw 'No se programó ninguna ejecución. Revisa materias, semanas y carpetas de planeación.'
}

Write-Host ("Se programaron {0} ejecuciones secuenciales." -f $jobs.Count)

if ($skipped.Count -gt 0) {
    Write-Warning 'Se omitieron algunos casos antes de ejecutar:'
    foreach ($item in $skipped) {
        Write-Warning ("- {0}" -f $item)
    }
}

$completed = New-Object System.Collections.Generic.List[string]
$failed = New-Object System.Collections.Generic.List[string]

foreach ($job in $jobs) {
    Write-Host ''
    Write-Host ("==> {0} | semana {1:D2}" -f $job.Materia, $job.Semana)
    Write-Host ("    Planeación: {0}" -f $job.Planeacion)
    Write-Host ("    Salida: {0}" -f $job.Salida)

    try {
        & $runnerPath `
            -Fuentes $job.Fuentes `
            -Planeacion $job.Planeacion `
            -Salida $job.Salida `
            -Motor $Motor `
            -Recursivo:$Recursivo `
            -ProbarConfig:$SoloValidar `
            -PlaneacionConceptos $PlaneacionConceptos `
            -TopK $TopK `
            -MaxCitas $MaxCitas

        $completed.Add(("{0} S{1:D2}" -f $job.Materia, $job.Semana))
    }
    catch {
        $failed.Add(("{0} S{1:D2}: {2}" -f $job.Materia, $job.Semana, $_.Exception.Message))
    }
}

Write-Host ''
Write-Host 'Resumen:'
Write-Host ("- Completadas: {0}" -f $completed.Count)
Write-Host ("- Fallidas: {0}" -f $failed.Count)
Write-Host ("- Omitidas: {0}" -f $skipped.Count)

if ($failed.Count -gt 0) {
    foreach ($item in $failed) {
        Write-Error $item
    }

    throw 'Una o más ejecuciones secuenciales fallaron.'
}