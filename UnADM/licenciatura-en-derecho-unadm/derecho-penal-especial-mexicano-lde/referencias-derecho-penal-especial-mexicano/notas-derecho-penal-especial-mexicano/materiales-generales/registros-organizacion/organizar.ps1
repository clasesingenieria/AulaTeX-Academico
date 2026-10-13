param([switch]$ValidateOnly, [switch]$Recover)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../../')).Path
$refs = Join-Path $root 'referencias-derecho-penal-especial-mexicano'
$notes = 'referencias-derecho-penal-especial-mexicano/notas-derecho-penal-especial-mexicano'
$general = "$notes/materiales-generales"
$manifest = Join-Path $PSScriptRoot 'movimientos-2026-10-11.json'
function RelativePath($path) { [IO.Path]::GetRelativePath($root, $path).Replace('\','/') }
function Hash($path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Category($path) {
    if ($path -match '/libros-') { return 'bibliografia' }
    if ($path -match 'Entregas/') { return 'version preparada; no prueba envio' }
    if ($path -match 'originales|material-docente|normas') { return 'material docente o norma' }
    if ($path -match 'auditoria|evidencia|comprobante|registros') { return 'evidencia o control' }
    if ($path -match 'historico|borrador|antecedentes') { return 'borrador o antecedente preservado' }
    if ($path -match 'Actividad-[12]\.(tex|pdf)$') { return 'producto activo' }
    if ($path -match 'extractor|memoria|\.txt$') { return 'auxiliar regenerable; conservado' }
    return 'soporte; revisar antes de eliminar'
}
if ($ValidateOnly) {
    $data = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    foreach ($item in $data.movimientos) {
        $target = Join-Path $root $item.destino
        if (-not (Test-Path -LiteralPath $target)) { throw "Destino ausente: $($item.destino)" }
        if ((Hash $target) -ne $item.sha256) { throw "Hash alterado: $($item.destino)" }
    }
    'Movimientos y hashes verificados: ' + $data.movimientos.Count
    return
}
if (Test-Path -LiteralPath $manifest) { throw 'Registro existente: usar -ValidateOnly; no repetir migracion.' }
if ($Recover) {
    $initial = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'inventario-inicial-2026-10-11.json') -Raw | ConvertFrom-Json
    $current = @(Get-ChildItem -LiteralPath $root -Recurse -Force -File | ForEach-Object { [pscustomobject]@{path=(RelativePath $_.FullName);hash=(Hash $_.FullName)} })
    $recovered = @()
    foreach ($item in $initial) {
        if (Test-Path -LiteralPath (Join-Path $root $item.archivo)) { continue }
        $candidates = @($current | Where-Object hash -eq $item.sha256)
        if ($candidates.Count -gt 1 -and $item.archivo -match 'Archivo-1[01]\.pdf$') { $candidates = @($candidates | Where-Object path -match '/material-docente/') }
        if ($candidates.Count -gt 1 -and $item.archivo -match '/fuentes-oficiales-') { $candidates = @($candidates | Where-Object path -match '/investigacion/fuentes-oficiales-') }
        if ($candidates.Count -ne 1) { throw "Recuperacion ambigua: $($item.archivo)" }
        $recovered += [ordered]@{origen=$item.archivo;destino=$candidates[0].path;sha256=$item.sha256;accion='traslado recuperado por hash'}
    }
    [ordered]@{fecha='2026-10-11';movimientos=$recovered;unicos_eliminados=0;originales_docentes_modificados=0;nota='Registro recuperado del inventario inicial despues de fallo de extraccion por ruta larga.'} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifest -Encoding utf8
    foreach ($file in Get-ChildItem -LiteralPath $refs -Recurse -Filter '*.pdf' -File) {
        $text = [IO.Path]::ChangeExtension($file.FullName,'.txt')
        if (-not (Test-Path -LiteralPath $text)) {
            Push-Location $file.DirectoryName
            try { & pdftotext -layout -enc UTF-8 $file.Name ([IO.Path]::ChangeExtension($file.Name,'.txt')); if ($LASTEXITCODE -ne 0) { throw 'Extraccion fallida' } }
            finally { Pop-Location }
        }
    }
    & $PSCommandPath -ValidateOnly
    return
}
$inventory = @(Get-ChildItem -LiteralPath $root -Recurse -Force -File | ForEach-Object {
    $relative = RelativePath $_.FullName
    [ordered]@{archivo=$relative;bytes=$_.Length;sha256=(Hash $_.FullName);clase=(Category $relative)}
})
$inventory | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'inventario-inicial-2026-10-11.json') -Encoding utf8
$moves = [Collections.Generic.List[object]]::new()
$map = @{}
function MoveVerified($sourceRelative, $targetRelative) {
    $source = Join-Path $root $sourceRelative
    $target = Join-Path $root $targetRelative
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { return }
    $digest = Hash $source
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    $action = 'traslado'
    if (Test-Path -LiteralPath $target) {
        if ((Hash $target) -ne $digest) { throw "Colision no identica: $targetRelative" }
        Remove-Item -LiteralPath $source
        $action = 'duplicado identico retirado'
    } else { Move-Item -LiteralPath $source -Destination $target }
    if ((Hash $target) -ne $digest) { throw "Traslado no integro: $targetRelative" }
    $map[$sourceRelative] = $targetRelative
    $moves.Add([ordered]@{origen=$sourceRelative;destino=$targetRelative;sha256=$digest;accion=$action})
}
foreach ($file in Get-ChildItem -LiteralPath $refs -File) {
    $name = $file.Name
    $destination = $null
    switch -Regex ($name) {
        '^PLANIFICACI-N--Archivo-8\.(pdf|txt)$' { $destination = "planeaciones-derecho-penal-especial-mexicano/originales-docentes/Planificacion-S2-docente.$($file.Extension.TrimStart('.'))"; break }
        '^MATERIAL-DE-APOYO-S2--Archivo-9\.(pdf|txt)$' { $destination = "$notes/actividad-02-cuadro-comparativo-robo/material-docente/Material-de-apoyo-S2.$($file.Extension.TrimStart('.'))"; break }
        '^C-DIGO-PENAL-FEDERAL--Archivo-10\.(pdf|txt)$' { $destination = "$notes/actividad-02-cuadro-comparativo-robo/material-docente/Codigo-Penal-Federal-copia-aula.$($file.Extension.TrimStart('.'))"; break }
        '^C-DIGO-PENAL-DF--Archivo-11\.(pdf|txt)$' { $destination = "$notes/actividad-02-cuadro-comparativo-robo/material-docente/Codigo-Penal-DF-copia-aula.$($file.Extension.TrimStart('.'))"; break }
        '^consigna-foro-S1\.png$' { $destination = "$notes/actividad-01-foro-diagnostico/consigna/Consigna-foro-S1.png"; break }
        '^modulo-6\.txt$' { $destination = "$notes/actividad-01-foro-diagnostico/evidencias/Consulta-foro-2026-10-04.txt"; break }
        '^modulo-7\.txt$' { $destination = "$notes/actividad-02-cuadro-comparativo-robo/evidencias/Consulta-tarea-2026-10-04.txt"; break }
        '^modulo-12\.txt$' { $destination = "$notes/actividad-02-cuadro-comparativo-robo/evidencias/Foro-dudas-S2-2026-10-04.txt"; break }
        '^modulo-[01]\.txt$|^curso-aula\.txt$' { $destination = "$general/antecedentes-aula/$name"; break }
        '^C-DIGO-DE--TICA.*\.pdf$' { $destination = "$general/normas/Codigo-de-etica-estudiantes-UnADM.pdf"; break }
        '^LINEAMIENTOS-PARA-EL-USO.*\.pdf$' { $destination = "$general/normas/Lineamientos-uso-etico-IA-UnADM.pdf"; break }
        '^LINEAMIENTOS-PARA-LA-EVALUACI.*\.pdf$' { $destination = "$general/normas/Lineamientos-evaluacion-aprendizaje-UnADM.pdf"; break }
        '^REGLAMENTO-UNIVERSITARIO.*\.pdf$' { $destination = "$general/normas/Reglamento-universitario-UnADM.pdf"; break }
        '^INDICE-AULA\.md$|^README\.md$' { $destination = "$general/historico-control/referencias-$name"; break }
    }
    if ($destination) { MoveVerified (RelativePath $file.FullName) $destination }
}
foreach ($folder in @('auditoria-semana-2-2026-10-09','auditoria-actual-2026-10-11','fuentes-oficiales-2026-10-11')) {
    $source = Join-Path $refs $folder
    if (Test-Path -LiteralPath $source) {
        $destination = if ($folder -like 'fuentes-*') { "$notes/actividad-02-cuadro-comparativo-robo/investigacion/$folder" } else { "$general/auditorias/$folder" }
        foreach ($file in Get-ChildItem -LiteralPath $source -Recurse -File) {
            $tail = [IO.Path]::GetRelativePath($source,$file.FullName).Replace('\','/')
            MoveVerified (RelativePath $file.FullName) "$destination/$tail"
        }
    }
}
foreach ($name in @('COMPILACION-derecho-penal-especial-mexicano.md','SEGUIMIENTO-2026-2-B2.md','programa-analitico-derecho-penal-especial-mexicano.md')) {
    MoveVerified $name "$general/historico-control/$name"
}
foreach ($extension in @('md','pdf')) {
    MoveVerified "borrador-S2-cuadro-comparativo-robo.$extension" "$notes/actividad-02-cuadro-comparativo-robo/propuestas/borrador-S2-cuadro-comparativo-robo.$extension"
}
$books = 'referencias-derecho-penal-especial-mexicano/libros-derecho-penal-especial-mexicano'
MoveVerified "$books/Introduccion al estudio del Der - Eduardo Garcia Maynez.pdf" "$books/Introduccion-al-estudio-del-Derecho-Eduardo-Garcia-Maynez.pdf"
MoveVerified "$books/Curso de argumentacion juridica - Manuel Atienza.pdf" "$books/Curso-de-argumentacion-juridica-Manuel-Atienza.pdf"
$originalInventory = Join-Path $refs 'inventario-aula.json'
Copy-Item -LiteralPath $originalInventory -Destination (Join-Path $PSScriptRoot 'inventario-aula-original-2026-10-04.json')
$aula = Get-Content -LiteralPath $originalInventory -Raw | ConvertFrom-Json
foreach ($item in $aula.resources) {
    if (-not $item.file) { continue }
    $old = 'referencias-derecho-penal-especial-mexicano/' + $item.file
    if ($map.ContainsKey($old)) {
        $item | Add-Member -NotePropertyName archivo_original -NotePropertyValue $item.file
        $item.file = [IO.Path]::GetRelativePath($refs,(Join-Path $root $map[$old])).Replace('\','/')
        $item | Add-Member -NotePropertyName sha256 -NotePropertyValue (Hash (Join-Path $refs $item.file))
    }
}
$aula | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $originalInventory -Encoding utf8
$bookInventory = Join-Path $root "$books/inventario-libros.json"
Copy-Item -LiteralPath $bookInventory -Destination (Join-Path $PSScriptRoot 'inventario-libros-original.json')
$bookData = Get-Content -LiteralPath $bookInventory -Raw | ConvertFrom-Json
foreach ($item in $bookData) {
    $old = "$books/$($item.archivo)"
    if ($map.ContainsKey($old)) { $item.archivo = Split-Path $map[$old] -Leaf }
}
$bookData | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $bookInventory -Encoding utf8
[ordered]@{fecha='2026-10-11';movimientos=$moves;unicos_eliminados=0;originales_docentes_modificados=0} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifest -Encoding utf8
foreach ($file in Get-ChildItem -LiteralPath $refs -Recurse -Filter '*.pdf' -File) {
    $text = [IO.Path]::ChangeExtension($file.FullName,'.txt')
    if (-not (Test-Path -LiteralPath $text)) {
        Push-Location $file.DirectoryName
        try { & pdftotext -layout -enc UTF-8 $file.Name ([IO.Path]::ChangeExtension($file.Name,'.txt')); if ($LASTEXITCODE -ne 0) { throw "Extraccion fallida: $($file.Name)" } }
        finally { Pop-Location }
    }
}
$extractions = @(Get-ChildItem -LiteralPath $refs -Recurse -Filter '*.pdf' -File | ForEach-Object {
    $text = [IO.Path]::ChangeExtension($_.FullName,'.txt')
    [ordered]@{pdf=(RelativePath $_.FullName);sha256_pdf=(Hash $_.FullName);txt=(RelativePath $text);sha256_txt=(Hash $text);bytes_txt=(Get-Item -LiteralPath $text).Length;metodo='pdftotext -layout; sin OCR; verificar legibilidad'}
})
$extractions | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'extracciones-2026-10-11.json') -Encoding utf8
[ordered]@{fecha='2026-10-11';raiz='derecho-penal-especial-mexicano-lde';movimientos=$moves;unicos_eliminados=0;originales_docentes_modificados=0;nota='Controles historicos conservan enlaces originales; inventarios actuales actualizados.'} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifest -Encoding utf8
& $PSCommandPath -ValidateOnly