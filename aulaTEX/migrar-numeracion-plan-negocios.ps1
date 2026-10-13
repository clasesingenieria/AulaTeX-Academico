param(
    [string]$Subject = (Join-Path $PSScriptRoot '../ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'),
    [ValidateSet('files', 'metadata')]
    [string]$Phase = 'files'
)

$ErrorActionPreference = 'Stop'
$Subject = (Resolve-Path -LiteralPath $Subject).Path
$registry = Join-Path $Subject 'NUMERACION-ACTIVIDADES.json'
$model = Get-Content -LiteralPath $registry -Raw | ConvertFrom-Json -AsHashtable

function Get-SharedHash([string]$Path) {
    $stream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read,
        ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '')
    } finally {
        $algorithm.Dispose()
        $stream.Dispose()
    }
}

if ($Phase -eq 'files') {
foreach ($move in $model.file_migration) {
    $source = [IO.Path]::GetFullPath((Join-Path $Subject $move.old))
    $destination = [IO.Path]::GetFullPath((Join-Path $Subject $move.new))
    foreach ($path in @($source, $destination)) {
        if (-not $path.StartsWith($Subject + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Ruta fuera de la materia.'
        }
    }
    if (-not $move.sha256_before) {
        if ($move.mode -ne 'copy_locked_original') { throw 'Huella inicial ausente.' }
        $move.sha256_before = Get-SharedHash $source
    }
    if (Test-Path -LiteralPath $destination) {
        if ((Get-SharedHash $destination) -ne $move.sha256_before) { throw "Destino distinto: $($move.new)" }
        continue
    }
    if ((Get-SharedHash $source) -ne $move.sha256_before) { throw "Origen modificado: $($move.old)" }
    if ($move.mode -eq 'copy_locked_original') {
        Copy-Item -LiteralPath $source -Destination $destination
    } elseif ($move.mode -eq 'rename') {
        Move-Item -LiteralPath $source -Destination $destination
    } else {
        throw 'Modo de migracion desconocido.'
    }
    if ((Get-SharedHash $destination) -ne $move.sha256_before) { throw "Integridad incorrecta: $($move.new)" }
}
[IO.File]::WriteAllText($registry, ($model | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
Write-Output "$($model.file_migration.Count) archivos verificados; migracion completada."
return
}

$replacements = @($model.file_migration | Sort-Object { $_.old.Length } -Descending)
$texts = Get-ChildItem -LiteralPath $Subject -Recurse -File | Where-Object {
    $_.Extension -in '.md', '.tex', '.json', '.txt' -and
    $_.FullName -ne $registry -and $_.FullName -notmatch '[\\/]\.memoria-aulatex[\\/]'
}
foreach ($file in $texts) {
    $text = [IO.File]::ReadAllText($file.FullName)
    $updated = $text
    foreach ($move in $replacements) {
        $pattern = '(?<![A-Za-z0-9_.-])' + [regex]::Escape($move.old) + '(?![A-Za-z0-9_.-])'
        $updated = [regex]::Replace($updated, $pattern, $move.new)
        if ($file.Directory.Name -eq 'planeaciones-plan-de-negocios' -and $move.old.StartsWith('planeaciones-plan-de-negocios/')) {
            $pattern = '(?<![A-Za-z0-9_.-])' + [regex]::Escape([IO.Path]::GetFileName($move.old)) + '(?![A-Za-z0-9_.-])'
            $updated = [regex]::Replace($updated, $pattern, [IO.Path]::GetFileName($move.new))
        }
    }
    if ($updated -ne $text) { [IO.File]::WriteAllText($file.FullName, $updated, [Text.UTF8Encoding]::new($false)) }
}

foreach ($activity in $model.activities) {
    $deadline = if ($activity.deadline -is [datetime]) {
        $activity.deadline
    } else {
        [datetime]::ParseExact($activity.deadline, 'yyyy-MM-ddTHH:mm:ss', [Globalization.CultureInfo]::InvariantCulture)
    }
    $label = $deadline.ToString('dd/MM/yyyy HH:mm', [Globalization.CultureInfo]::InvariantCulture)
    foreach ($move in $model.file_migration | Where-Object { $_.module_id -eq $activity.module_id }) {
        $path = Join-Path $Subject $move.new
        if ($move.new -match '^reporte-.*\.tex$') {
            $text = [IO.File]::ReadAllText($path)
            if ($text -notmatch '\\def\\actividadnumero\{') {
                $text = "\def\actividadnumero{$($activity.number)}`n\def\actividadvencimiento{$label}`n" + $text
                [IO.File]::WriteAllText($path, $text, [Text.UTF8Encoding]::new($false))
            }
            if ($text -notmatch ('\\def\\actividadmodulo\{' + $activity.module_id + '\}')) {
                throw "ID Moodle inconsistente: $($move.new)"
            }
        }
    }
    $planPath = Join-Path $Subject "planeaciones-plan-de-negocios/planeacion-actividad-$($activity.number).json"
    if (Test-Path -LiteralPath $planPath) {
        $plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json -AsHashtable
        $plan['chronological_numbering'] = [ordered]@{
            local_number = $activity.number
            moodle_module_id = $activity.module_id
            deadline = $activity.deadline
            deadline_label = $activity.deadline_label
            deadline_literal = $activity.deadline_literal
            timezone = $null
            source = "https://cursos3.e-itesca.edu.mx/mod/$($activity.type)/view.php?id=$($activity.module_id)"
            consulted_on = $model.consulted_on
        }
        [IO.File]::WriteAllText($planPath, ($plan | ConvertTo-Json -Depth 100), [Text.UTF8Encoding]::new($false))
        $markdownPath = [IO.Path]::ChangeExtension($planPath, '.md')
        $markdown = [IO.File]::ReadAllText($markdownPath)
        if ($markdown -notmatch '\*\*Actividad local:\*\*') {
            $markdown += "`n**Actividad local:** $($activity.number). **Modulo Moodle:** $($activity.module_id). **Vencimiento publicado:** $label. Consulta: $($model.consulted_on); zona horaria no verificada.`n"
            [IO.File]::WriteAllText($markdownPath, $markdown, [Text.UTF8Encoding]::new($false))
        }
    }
}
$indexLines = @('# Planeaciones de Plan de Negocios por vencimiento', '',
    'Numeracion local cotejada el 22/09/2026. [Calendario y equivalencias](../ORDEN-ACTIVIDADES.md).', '',
    '| Actividad | Modulo Moodle | Planeacion | Modelo |', '| --- | --- | --- | --- |')
$stateLines = @('# Plan de Negocios - Entregables por vencimiento', '',
    'Preparacion local no equivale a entrega ni aprobacion. [Calendario verificado](ORDEN-ACTIVIDADES.md).', '',
    '| Actividad | Modulo Moodle | Producto disponible | Estado |', '| --- | --- | --- | --- |')
foreach ($activity in $model.activities | Sort-Object number) {
    $number = $activity.number
    $indexLines += "| $number | $($activity.module_id) | [$($activity.title)](planeacion-actividad-$number.md) | [JSON](planeacion-actividad-$number.json) |"
    $baseName = "reporte-plan-de-negocios-Actividad-$number-$($activity.slug)"
    $links = @()
    foreach ($extension in 'tex', 'pdf', 'docx') {
        if (Test-Path -LiteralPath (Join-Path $Subject "$baseName.$extension")) {
            $links += "[$($extension.ToUpper())]($baseName.$extension)"
        }
    }
    if ($number -eq 4) { $links += '[Desarrollo Markdown](realizar-actividad-4-descripcion-empresa.md)' }
    if ($number -eq 1) { $links += '[Guion del foro](foro-participacion-Actividad-1.md)' }
    if ($links.Count) {
        $product = $links -join ' / '
        $state = 'Documento local; revisar contenido y requisitos antes de usarlo.'
    } else {
        $product = "[Planeacion](planeaciones-plan-de-negocios/planeacion-actividad-$number.md)"
        $state = 'Sin reporte local; no se genero un producto nuevo en esta revision.'
    }
    $stateLines += "| $number | $($activity.module_id) | $product | $state |"
}
$stateLines += @('', '## Variantes y documentos abiertos', '',
    'La Actividad 6 conserva alternativas NexoTeX e Industrial Revolucionaria con sufijos distintos. El reporte Imagen-Empresa corresponde a AM Taller Autocentro.', '',
    'El Word original del modulo 6545 estaba abierto: se conservo intacto y se genero una copia renumerada. No descartar el original hasta reconciliar cambios posteriores.', '',
    'Los reportes usan [la plantilla de materia](reporte-plan-de-negocios-plantilla-actividad.tex), que conserva el ID Moodle y muestra el numero local. [Compilacion](COMPILACION.md).')
[IO.File]::WriteAllText((Join-Path $Subject 'planeaciones-plan-de-negocios/README.md'), ($indexLines -join "`n") + "`n", [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $Subject 'ESTADO-ENTREGABLES.md'), ($stateLines -join "`n") + "`n", [Text.UTF8Encoding]::new($false))
Write-Output 'Referencias, metadatos e indices actualizados; IDs Moodle conservados.'