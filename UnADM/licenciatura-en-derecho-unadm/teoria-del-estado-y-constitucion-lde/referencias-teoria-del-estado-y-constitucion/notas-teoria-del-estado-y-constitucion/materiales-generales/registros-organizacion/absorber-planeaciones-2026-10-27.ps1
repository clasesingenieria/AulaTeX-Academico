param([switch]$RemoveAbsorbedSources)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../../')).Path
$planning = 'planeaciones-teoria-del-estado-y-constitucion'
$archiveRelative = 'referencias-teoria-del-estado-y-constitucion/notas-teoria-del-estado-y-constitucion/materiales-generales/registros-organizacion/planeaciones-absorbidas-2026-10-27.json'
$archivePath = Join-Path $root $archiveRelative
$utf8 = [Text.UTF8Encoding]::new($false, $true)
$targets = @('importaciones', 'revisiones-organizacion', 'planeacion-S2.md', 'planeacion-S3-normalizada.md')

function Get-TextHash([string]$Text) {
    [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($utf8.GetBytes($Text))).ToLowerInvariant()
}

function Write-Json([string]$Path, $Value) {
    [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 100) + "`n", $utf8)
}

if (-not (Test-Path -LiteralPath $archivePath)) {
    if ($RemoveAbsorbedSources) { throw 'Primero ejecutar la preparacion sin eliminacion.' }
    $entries = [Collections.Generic.List[object]]::new()
    $contents = [ordered]@{}
    foreach ($target in $targets) {
        $source = Get-Item -LiteralPath (Join-Path $root "$planning/$target") -Force
        $items = if ($source.PSIsContainer) { @(Get-ChildItem -LiteralPath $source.FullName -Recurse -Force) } else { @($source) }
        foreach ($item in @($source) + $items) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Enlace no permitido: $($item.FullName)" }
        }
        foreach ($file in $items | Where-Object { -not $_.PSIsContainer } | Sort-Object FullName) {
            if ($file.Extension -notin @('.json', '.md')) { throw "Tipo inesperado: $($file.FullName)" }
            $bytes = [IO.File]::ReadAllBytes($file.FullName)
            $text = $utf8.GetString($bytes)
            $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            if ((Get-TextHash $text) -ne $hash) { throw "Codificacion no reversible: $($file.FullName)" }
            if ($file.Extension -eq '.json') { $null = $text.TrimStart([char]0xfeff) | ConvertFrom-Json -Depth 100 }
            $entries.Add([ordered]@{
                original_path = [IO.Path]::GetRelativePath($root, $file.FullName).Replace('\', '/')
                sha256 = $hash
                bytes = $bytes.Length
            })
            if (-not $contents.Contains($hash)) { $contents[$hash] = $text }
        }
    }
    $archive = [ordered]@{
        kind = 'lossless-planning-absorption'
        documentary_date = '2026-10-27'
        authority = 'historical-editorial-only'
        note = 'Contenido UTF-8 completo, incluidos BOM y saltos de linea, deduplicado por SHA256. Las rutas originales son identificadores historicos, no enlaces activos. No constituye aprobacion academica ni autoriza operaciones de plataforma.'
        entries = @($entries.ToArray())
        contents = $contents
    }
    Write-Json $archivePath $archive
}

$archive = Get-Content -LiteralPath $archivePath -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable -Depth 100
$entriesByPath = @{}
foreach ($entry in $archive.entries) {
    $text = $archive.contents[$entry.sha256]
    if ((Get-TextHash $text) -ne $entry.sha256 -or $utf8.GetByteCount($text) -ne $entry.bytes) { throw "Contenido alterado: $($entry.original_path)" }
    if ($entriesByPath.ContainsKey($entry.original_path)) { throw 'Ruta duplicada.' }
    $entriesByPath[$entry.original_path] = $entry
    $sourcePath = Join-Path $root $entry.original_path
    if (Test-Path -LiteralPath $sourcePath) {
        if ((Get-FileHash -LiteralPath $sourcePath).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Origen modificado: $sourcePath" }
    }
}

$catalogPath = Join-Path $root "$planning/catalogo-editorial.json"
$catalog = Get-Content -LiteralPath $catalogPath -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable -Depth 100
if (-not $RemoveAbsorbedSources) {
    foreach ($activity in $catalog.activities) {
        $modelPath = Join-Path $root $activity.json
        $model = Get-Content -LiteralPath $modelPath -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable -Depth 100
        $previous = $model.extensions.organizacion_interna.previous_revision
        if ($previous.path -ne $archiveRelative) {
            $entry = $entriesByPath[$previous.path]
            if (-not $entry -or $entry.sha256 -ne $previous.sha256) { throw 'Revision anterior no respaldada.' }
            $previous.original_path = $previous.path
            $previous.path = $archiveRelative
            $previous.content_pointer = '/contents/' + $entry.sha256
        }
        $snapshotPath = "$planning/revisiones-organizacion/r0004/" + [IO.Path]::GetFileName($activity.json)
        $snapshot = $entriesByPath[$snapshotPath]
        if (-not $snapshot) { throw 'Falta instantanea r0004.' }
        $model.extensions.documentary_absorption = [ordered]@{
            documentary_date = '2026-10-27'
            archive_path = $archiveRelative
            original_revision_sha256 = $snapshot.sha256
            authority = 'editorial'
            academic_approval = $false
        }
        $viewPath = Join-Path $root $activity.md
        $view = [IO.File]::ReadAllText($viewPath)
        $heading = '### Precisiones absorbidas'
        if ($view.Contains($heading)) {
            $model.extensions.documentary_absorption.editorial_notes = $view.Substring($view.IndexOf($heading) + $heading.Length).Trim()
        }
        Write-Json $modelPath $model
        $activity.sha256 = (Get-FileHash -LiteralPath $modelPath).Hash.ToLowerInvariant()
        $activity.immutable_revision = $archiveRelative
        $activity.immutable_revision_content_pointer = '/contents/' + $snapshot.sha256
        $activity.immutable_revision_sha256 = $snapshot.sha256
    }
    Write-Json $catalogPath $catalog
    $registryPath = Join-Path $root "$planning/reubicaciones-documentales.json"
    $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable -Depth 100
    $registry.absorption = [ordered]@{
        documentary_date = '2026-10-27'
        archive_path = $archiveRelative
        archive_sha256 = (Get-FileHash -LiteralPath $archivePath).Hash.ToLowerInvariant()
        absorbed_files = $archive.entries.Count
        unique_contents = $archive.contents.Count
        original_paths_are_historical = $true
    }
    Write-Json $registryPath $registry
}

foreach ($activity in $catalog.activities) {
    $modelPath = Join-Path $root $activity.json
    $model = Get-Content -LiteralPath $modelPath -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable -Depth 100
    if ((Get-FileHash -LiteralPath $modelPath).Hash.ToLowerInvariant() -ne $activity.sha256) { throw 'Hash de catalogo incorrecto.' }
    if ($activity.immutable_revision -ne $archiveRelative -or -not $archive.contents.Contains($activity.immutable_revision_sha256)) { throw 'Instantanea no localizable.' }
    if ($model.extensions.organizacion_interna.previous_revision.path -ne $archiveRelative) { throw 'Referencia anterior no actualizada.' }
    if ($model.review.state -ne 'needs_review' -or $model.extensions.organizacion_interna.platform_operations.Count -ne 0) { throw 'Estado academico u operaciones alterados.' }
}

if ($RemoveAbsorbedSources) {
    foreach ($target in $targets) {
        $targetPath = Join-Path $root "$planning/$target"
        if (-not (Test-Path -LiteralPath $targetPath)) { continue }
        $source = Get-Item -LiteralPath $targetPath -Force
        $items = if ($source.PSIsContainer) { @(Get-ChildItem -LiteralPath $targetPath -Recurse -Force) } else { @($source) }
        foreach ($item in @($source) + $items) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Enlace no permitido durante eliminacion.' }
        }
        foreach ($file in $items | Where-Object { -not $_.PSIsContainer }) {
            $relative = [IO.Path]::GetRelativePath($root, $file.FullName).Replace('\', '/')
            if (-not $entriesByPath.ContainsKey($relative)) { throw "Archivo nuevo sin absorber: $relative" }
        }
    }
    foreach ($entry in $archive.entries) {
        $sourcePath = Join-Path $root $entry.original_path
        if (Test-Path -LiteralPath $sourcePath) { Remove-Item -LiteralPath $sourcePath }
    }
    foreach ($target in @('importaciones', 'revisiones-organizacion')) {
        $targetPath = Join-Path $root "$planning/$target"
        if (Test-Path -LiteralPath $targetPath) {
            Get-ChildItem -LiteralPath $targetPath -Directory -Recurse -Force | Sort-Object { $_.FullName.Length } -Descending | ForEach-Object { [IO.Directory]::Delete($_.FullName) }
            [IO.Directory]::Delete($targetPath)
        }
    }
    foreach ($target in $targets) {
        if (Test-Path -LiteralPath (Join-Path $root "$planning/$target")) { throw "Origen restante: $target" }
    }
}

"Integridad verificada: $($archive.entries.Count) archivos, $($archive.contents.Count) contenidos unicos; cuatro modelos y hashes de catalogo correctos. Eliminacion: $RemoveAbsorbedSources"
foreach ($entry in $archive.entries | Where-Object original_path -like '*/importaciones/*/planeacion.json') {
    $imported = $archive.contents[$entry.sha256].TrimStart([char]0xfeff) | ConvertFrom-Json -Depth 100
    [pscustomobject]@{ Importacion = $imported.plan_id; Actividades = ($imported.activities.title -join ', '); Semanas = ($imported.activities.weeks -join ', ') }
}