param([switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../../')).Path
$slug = 'teoria-del-estado-y-constitucion'
$refs = "referencias-$slug"
$notes = "$refs/notas-$slug"
$general = "$notes/materiales-generales"
$activity2 = "$notes/actividad-02-linea-de-tiempo"
$activity3 = "$notes/actividad-03-analisis-de-hechos"
$planning = "planeaciones-$slug"
$manifest = Join-Path $PSScriptRoot 'movimientos-2026-10-11.json'
function Digest($path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Relative($path) { [IO.Path]::GetRelativePath($root,$path).Replace('\','/') }
if ($ValidateOnly) {
    $data = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    foreach ($item in $data.movimientos) {
        $path = Join-Path $root $item.destino
        $revision = @($data.actualizaciones | Where-Object archivo -eq $item.destino)
        $expected = if ($revision.Count) { $revision[-1].sha256_despues } else { $item.sha256 }
        if (-not (Test-Path -LiteralPath $path) -or (Digest $path) -ne $expected) { throw "Destino no integro: $($item.destino)" }
    }
    foreach ($item in $data.protegidos) {
        if ((Digest (Join-Path $root $item.archivo)) -ne $item.sha256) { throw "Entrega alterada: $($item.archivo)" }
    }
    foreach ($item in $data.extracciones) {
        if (-not (Test-Path -LiteralPath (Join-Path $root $item.txt))) { throw "TXT ausente: $($item.txt)" }
    }
    "$($data.movimientos.Count) movimientos; $(@($data.movimientos | Where-Object accion -eq 'duplicado identico consolidado').Count) duplicados identicos; $($data.protegidos.Count) archivos protegidos verificados."
    return
}
if (Test-Path -LiteralPath $manifest) { throw 'Migracion ya registrada; usar -ValidateOnly.' }
$inventory = @(Get-ChildItem -LiteralPath $root -Recurse -Force -File | ForEach-Object { [ordered]@{archivo=(Relative $_.FullName);bytes=$_.Length;sha256=(Digest $_.FullName)} })
$inventory | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'inventario-inicial.json') -Encoding utf8
$protected = @($inventory | Where-Object { $_.archivo -like 'Entregas/*' -or $_.archivo -match '/comprobantes-envio/' })
$moves = [Collections.Generic.List[object]]::new()
$updates = [Collections.Generic.List[object]]::new()
$map = [ordered]@{}
function MoveVerified($old,$new) {
    $source = Join-Path $root $old
    $target = Join-Path $root $new
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { return }
    $hash = Digest $source
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    $action = 'traslado'
    if (Test-Path -LiteralPath $target) {
        if ((Digest $target) -ne $hash) { throw "Colision no identica: $new" }
        Remove-Item -LiteralPath $source
        $action = 'duplicado identico consolidado'
    } else { Move-Item -LiteralPath $source -Destination $target }
    if ((Digest $target) -ne $hash) { throw "Hash no coincide: $new" }
    $map[$old] = $new
    $moves.Add([ordered]@{origen=$old;destino=$new;sha256=$hash;accion=$action})
}
$files = [ordered]@{
    "$refs/PA-S2_S3-Teor-a-del-Estado-y-Constituci-n-2026--Archivo-8.pdf" = "$planning/Planificacion-de-actividades-S2-S3-Teoria-del-Estado-y-Constitucion.pdf"
    "$refs/PA-S2_S3-Teor-a-del-Estado-y-Constituci-n-2026--Archivo-10.pdf" = "$planning/Planificacion-de-actividades-S2-S3-Teoria-del-Estado-y-Constitucion.pdf"
    "$refs/PA-S2_S3-Teor-a-del-Estado-y-Constituci-n-2026--Archivo-10.txt" = "$planning/Planificacion-de-actividades-S2-S3-Teoria-del-Estado-y-Constitucion.txt"
    "$refs/calendario-5.pdf" = "$general/calendario/Calendario-docente-2026-B2.pdf"
    "$refs/calendario-6.pdf" = "$general/calendario/Calendario-docente-2026-B2.pdf"
    "$refs/calendario-7.pdf" = "$general/calendario/Calendario-docente-2026-B2.pdf"
    "$refs/Calendario-Archivo-5.pdf" = "$general/calendario/Calendario-docente-2026-B2.pdf"
    "$refs/calendario-6.txt" = "$general/calendario/Calendario-docente-2026-B2.txt"
    "$refs/calendario-7.txt" = "$general/calendario/Calendario-extraccion-captura-7.txt"
    "$refs/Calendario-Archivo-5.txt" = "$general/calendario/Calendario-extraccion-captura-5.txt"
    "$refs/Reglamento_Universitario_2026-Archivo-2.pdf" = "$general/normas/Reglamento-universitario-UnADM-2026.pdf"
    "$refs/Lineamientos_IA_Aprobados-Archivo-3.pdf" = "$general/normas/Lineamientos-uso-IA-UnADM.pdf"
    "$refs/Lineamientos_IA_Aprobados-Archivo-3.txt" = "$general/normas/Lineamientos-uso-IA-UnADM.txt"
    "$refs/LineamientosEvaluacionAprendizaje_2024-Archivo-4.pdf" = "$general/normas/Lineamientos-evaluacion-aprendizaje-UnADM-2024.pdf"
    "$refs/curso-aula.txt" = "$general/capturas-aula/Curso-captura-2026-10-04.txt"
    "$refs/modulo-0.txt" = "$general/capturas-aula/Avisos-modulo-0.txt"
    "$refs/modulo-1.txt" = "$general/capturas-aula/Foro-dudas-modulo-1.txt"
    "$refs/modulo-6.txt" = "$general/sesiones-sincronas/Formulario-modulo-6.txt"
    "$refs/modulo-8.txt" = "$general/sesiones-sincronas/Formulario-modulo-8.txt"
    "$refs/modulo-7.txt" = "$notes/actividad-01-foro-diagnostico/consignas/Foro-diagnostico-modulo-7.txt"
    "$refs/modulo-9.txt" = "$notes/actividad-01-foro-diagnostico/consignas/Foro-diagnostico-modulo-9.txt"
    "$refs/FUENTES-LINEA-DE-TIEMPO-S2.md" = "$activity2/investigacion/FUENTES-LINEA-DE-TIEMPO-S2.md"
    "$refs/INDICE-AULA.md" = "$general/historico-control/INDICE-AULA.md"
    "$refs/README.md" = "$general/historico-control/README-referencias-anterior.md"
    'COMPILACION-teoria-del-estado-y-constitucion.md' = "$general/historico-control/COMPILACION-teoria-del-estado-y-constitucion.md"
    'programa-analitico-teoria-del-estado-y-constitucion.md' = "$general/historico-control/programa-analitico-teoria-del-estado-y-constitucion.md"
    'borrador-S2-linea-de-tiempo.md' = "$activity2/propuestas/borrador-S2-linea-de-tiempo.md"
    'borrador-S2-linea-de-tiempo.pdf' = "$activity2/propuestas/borrador-S2-linea-de-tiempo.pdf"
    'borrador-S3-analisis-de-hechos.md' = "$activity3/propuestas/borrador-S3-analisis-de-hechos.md"
    'borrador-S3-analisis-de-hechos.pdf' = "$activity3/propuestas/borrador-S3-analisis-de-hechos.pdf"
    "$planning/planeacion-S2-estructurada.md" = "$planning/planeacion-S2.md"
    "$planning/planeacion-S2-S3.md" = "$general/historico-control/planeacion-S2-S3-original.md"
}
$books = "$refs/libros-$slug"
$files["$books/Introduccion al estudio del Der - Eduardo Garcia Maynez.pdf"] = "$books/Introduccion-al-estudio-del-Derecho-Eduardo-Garcia-Maynez.pdf"
$files["$books/Teoria pura del derecho - Hans Kelsen.pdf"] = "$books/Teoria-pura-del-Derecho-Hans-Kelsen.pdf"
$files["$books/En defensa del estado de derech - Ignacio Campoy Cervera.pdf"] = "$books/En-defensa-del-Estado-de-Derecho-Ignacio-Campoy-Cervera.pdf"
$files["$books/Constitucion Politica de los Es - Camara de Diputados del H. Cong.pdf"] = "$books/Constitucion-Politica-de-los-Estados-Unidos-Mexicanos-copia-biblioteca.pdf"
$folderMap = [ordered]@{
    "$refs/imagenes-linea-S2" = "$activity2/imagenes-linea-S2"
    "$refs/validacion-latex-S2" = "$activity2/revisiones/validacion-latex-S2"
    "$refs/auditoria-semana-2-2026-10-09" = "$general/auditorias/semana-2-2026-10-09"
}
foreach ($old in $folderMap.Keys) {
    $folder = Join-Path $root $old
    foreach ($file in Get-ChildItem -LiteralPath $folder -Recurse -File) { $files[(Relative $file.FullName)] = $folderMap[$old] + '/' + [IO.Path]::GetRelativePath($folder,$file.FullName).Replace('\','/') }
}
foreach ($old in $files.Keys) { MoveVerified $old $files[$old] }
[ordered]@{movimientos=$moves;actualizaciones=$updates;protegidos=$protected;extracciones=@()} | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifest -Encoding utf8
$initialPaths = @{}
foreach ($item in $inventory) { $initialPaths[$item.archivo] = $item.archivo }
foreach ($old in $map.Keys) { $initialPaths[$map[$old]] = $old }
function NewRelativeTarget($oldTarget,$currentFile) {
    $relative = [IO.Path]::GetRelativePath((Split-Path (Join-Path $root $currentFile)),(Join-Path $root $oldTarget)).Replace('\','/')
    return $relative
}
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -Force -File | Where-Object Extension -in @('.md','.tex','.json','.bib')) {
    $current = Relative $file.FullName
    if ($current -match '/registros-organizacion/|/comprobantes-envio/|^Entregas/') { continue }
    $original = if ($initialPaths.ContainsKey($current)) { $initialPaths[$current] } else { $current }
    $text = [IO.File]::ReadAllText($file.FullName)
    $before = Digest $file.FullName
    if ($text -match '\]\(') {
        $text = [regex]::Replace($text,'\]\(([^)]+)\)', { param($match)
            $href = $match.Groups[1].Value
            if ($href -match '^[a-z]+:|^#') { return $match.Value }
            $parts = $href.Split('#',2)
            $decoded = [Uri]::UnescapeDataString($parts[0])
            $absolute = [IO.Path]::GetFullPath((Join-Path (Split-Path (Join-Path $root $original)) $decoded))
            $oldRelative = Relative $absolute
            $newTarget = if ($map.Contains($oldRelative)) { $map[$oldRelative] } else { $oldRelative }
            if (-not (Test-Path -LiteralPath (Join-Path $root $newTarget))) { return $match.Value }
            $newHref = (NewRelativeTarget $newTarget $current).Replace(' ','%20')
            if ($parts.Length -gt 1) { $newHref += '#' + $parts[1] }
            return '](' + $newHref + ')'
        })
    }
    foreach ($old in $folderMap.Keys) { $text = $text.Replace($old,$folderMap[$old]) }
    foreach ($old in $map.Keys) { $text = $text.Replace($old,$map[$old]) }
    if ($text -ne [IO.File]::ReadAllText($file.FullName)) {
        $backup = Join-Path $PSScriptRoot ("antes-actualizar-enlaces/$current")
        New-Item -ItemType Directory -Path (Split-Path $backup) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $backup
        [IO.File]::WriteAllText($file.FullName,$text,[Text.UTF8Encoding]::new($false))
        $updates.Add([ordered]@{archivo=$current;sha256_antes=$before;sha256_despues=(Digest $file.FullName);motivo='Actualizacion mecanica de enlaces; copia previa preservada'})
    }
}
foreach ($pair in @(@("$refs/inventario-aula.json",'resources','file'),@("$books/inventario-libros.json",'','archivo'))) {
    $path = Join-Path $root $pair[0]
    $before = Digest $path
    Copy-Item -LiteralPath $path -Destination (Join-Path $PSScriptRoot ([IO.Path]::GetFileNameWithoutExtension($path)+'-original.json'))
    $data = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    $entries = if ($pair[1]) { $data.resources } else { $data }
    $base = if ($pair[1]) { Join-Path $root $refs } else { Join-Path $root $books }
    foreach ($entry in $entries) {
        $property = $pair[2]
        if (-not $entry.$property) { continue }
        $old = Relative (Join-Path $base $entry.$property)
        if ($map.Contains($old)) {
            $entry | Add-Member -NotePropertyName nombre_original -NotePropertyValue $entry.$property -Force
            $entry.$property = [IO.Path]::GetRelativePath($base,(Join-Path $root $map[$old])).Replace('\','/')
            $entry | Add-Member -NotePropertyName sha256 -NotePropertyValue (Digest (Join-Path $base $entry.$property)) -Force
        }
    }
    $data | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $path -Encoding utf8
    $updates.Add([ordered]@{archivo=$pair[0];sha256_antes=$before;sha256_despues=(Digest $path);motivo='Inventario estructurado con procedencia original y ruta actual'})
}
$extractions = @()
$temp = Join-Path $root '.extraccion-organizacion'
New-Item -ItemType Directory -Path $temp -Force | Out-Null
try {
    $pdfs = @(Get-ChildItem -LiteralPath (Join-Path $root $refs),(Join-Path $root $planning) -Recurse -File -Filter '*.pdf' | Where-Object { $_.FullName -notmatch 'comprobantes-envio|registros-organizacion|revision-2026-10-11' })
    foreach ($file in $pdfs) {
        $txt = [IO.Path]::ChangeExtension($file.FullName,'.txt')
        if (-not (Test-Path -LiteralPath $txt)) {
            Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $temp 'entrada.pdf')
            Push-Location $temp
            try { & pdftotext -layout -enc UTF-8 entrada.pdf salida.txt; if ($LASTEXITCODE -ne 0) { throw 'Extraccion fallida' } }
            finally { Pop-Location }
            Move-Item -LiteralPath (Join-Path $temp 'salida.txt') -Destination $txt
        }
        $extractions += [ordered]@{pdf=(Relative $file.FullName);txt=(Relative $txt);sha256_pdf=(Digest $file.FullName);sha256_txt=(Digest $txt);metodo='TXT existente conservado o pdftotext -layout UTF8; sin OCR'}
    }
} finally { Remove-Item -LiteralPath $temp -Recurse -Force }
Get-ChildItem -LiteralPath $root -Directory -Recurse | Sort-Object { $_.FullName.Length } -Descending | ForEach-Object { if (@(Get-ChildItem -LiteralPath $_.FullName -Force).Count -eq 0) { Remove-Item -LiteralPath $_.FullName } }
[ordered]@{fecha='2026-10-11';movimientos=$moves;actualizaciones=$updates;protegidos=$protected;extracciones=$extractions;unicos_eliminados=0;nota='Originales completos; copia enviada protegida; duplicados retirados solo con hash identico.'} | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $manifest -Encoding utf8
& $PSCommandPath -ValidateOnly