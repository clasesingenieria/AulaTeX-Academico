& {
    $root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
    $old = 'reporte-plan-de-negocios-Actividad-13-Preparacion-Examen-1-4'
    $new = 'reporte-plan-de-negocios-Actividad-13-Examen-1-4'
    Get-ChildItem -LiteralPath $root -File | Where-Object { $_.BaseName.StartsWith($old) } | ForEach-Object {
        $destination = Join-Path $root ($_.Name.Replace($old, $new))
        if (Test-Path -LiteralPath $destination) { throw 'El destino ya existe' }
        Move-Item -LiteralPath $_.FullName -Destination $destination -ErrorAction Stop
    }
    Get-ChildItem -LiteralPath $root -Recurse -File -Include '*.md','*.json' | ForEach-Object {
        $text = Get-Content -LiteralPath $_.FullName -Raw
        if ($text.Contains($old)) {
            [System.IO.File]::WriteAllText($_.FullName, $text.Replace($old, $new), [System.Text.UTF8Encoding]::new($false))
        }
    }
    $source = Join-Path $root ($new + '.tex')
    $text = Get-Content -LiteralPath $source -Raw
    $text = $text.Replace('\def\actividadtitulo{Preparación del examen de conceptos}', '\def\actividadtitulo{Examen de conceptos}')
    [System.IO.File]::WriteAllText($source, $text, [System.Text.UTF8Encoding]::new($false))
    if (Test-Path -LiteralPath (Join-Path $root ($old + '.tex'))) { throw 'Fuente anterior restante' }
    if (-not (Test-Path -LiteralPath $source)) { throw 'Fuente renombrada ausente' }
    'Reporte renombrado; estado de examen no realizado conservado.'
}