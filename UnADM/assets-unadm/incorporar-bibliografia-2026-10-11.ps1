$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$library = 'C:\Users\Sysx\Documents\Libros\Derecho'
$courses = Join-Path $root 'UnADM/licenciatura-en-derecho-unadm'
$records = @()
$selections = @(
    @{author='Francisco Javier Ansuategui Roig';book='Razon y voluntad en el estado de der (55)';name='Razon y voluntad en el Estado de Derecho - Francisco Javier Ansuategui Roig';courses=@('teoria-del-estado-y-constitucion');use='Estado de derecho, legitimidad y limites del poder'},
    @{author='Antonio Garcia-Pablos de Molina';book='Criminologia_ Fundamentos y principi (2)';name='Criminologia fundamentos y principios - Antonio Garcia-Pablos de Molina';courses=@('derecho-penal-especial-mexicano');use='Contexto criminologico; no sustituye tipos penales ni penas vigentes'},
    @{author='Javier Hernandez Manriquez';book='Nociones de hermeneutica e interpre (101)';name='Nociones de hermeneutica e interpretacion juridica - Javier Hernandez Manriquez';courses=@('teoria-del-estado-y-constitucion','derecho-penal-especial-mexicano');use='Metodo de interpretacion juridica; cotejar capitulos antes de citar'},
    @{author='Eduardo Andrade Sanchez';book='Teoria general del estado (2a. ed.) (110)';name='Teoria general del Estado (2a edicion) - Eduardo Andrade Sanchez';courses=@('teoria-del-estado-y-constitucion');use='Teoria general del Estado; comprobar pagina legal y localizadores'},
    @{author='Juan Jacobo Rousseau';book='El Contrato Social (108)';name='El contrato social - Juan Jacobo Rousseau';courses=@('teoria-del-estado-y-constitucion');use='S3: soberania y voluntad general; verificar traduccion y edicion'},
    @{author='Montesquieu';book='Del espiritu de las leyes (107)';name='Del espiritu de las leyes - Montesquieu';courses=@('teoria-del-estado-y-constitucion');use='S3: division del poder; verificar libro, capitulo y traduccion'},
    @{author='Heriberto Frias';book='Sentimientos de la nacion _ El siti (109)';name='Sentimientos de la nacion y El sitio de Cuautla - Heriberto Frias';courses=@('teoria-del-estado-y-constitucion');use='Referencia historica catalogada bajo Frias; no equivale por si sola al documento original de Morelos'},
    @{author='I. Griselda Amuchategui Requena';book='Derecho penal, 4ta Edicion (105)';name='Derecho penal (4a edicion) - Griselda Amuchategui Requena';courses=@('derecho-penal-especial-mexicano');use='Doctrina penal mexicana; no sustituye legislacion vigente'},
    @{author='Jesus Maria Silva Sanchez';book='Derecho Penal. Parte General (106)';name='Derecho penal Parte general - Jesus Maria Silva Sanchez';courses=@('derecho-penal-especial-mexicano');use='Doctrina de parte general; comprobar autoria completa, edicion y contexto juridico'}
)
foreach ($selection in $selections) {
    $directory = Join-Path (Join-Path $library $selection.author) $selection.book
    $sources = @(Get-ChildItem -LiteralPath $directory -Filter '*.pdf' -File)
    if ($sources.Count -ne 1) { throw 'Seleccion bibliografica no univoca' }
    $source = $sources[0]
    $hash = (Get-FileHash -LiteralPath $source.FullName).Hash.ToLowerInvariant()
    [xml]$metadata = Get-Content -LiteralPath (Join-Path $directory 'metadata.opf') -Raw
    $title = $metadata.SelectSingleNode('//*[local-name()="title"]').InnerText
    foreach ($slug in $selection.courses) {
        $destination = Join-Path $courses "$slug-lde/referencias-$slug/libros-$slug"
        $pdf = Join-Path $destination ($selection.name+'.pdf')
        if (Test-Path -LiteralPath $pdf) {
            if ((Get-FileHash -LiteralPath $pdf).Hash.ToLowerInvariant() -ne $hash) { throw 'Destino existente diferente' }
        } else { Copy-Item -LiteralPath $source.FullName -Destination $pdf }
        if ((Get-FileHash -LiteralPath $pdf).Hash.ToLowerInvariant() -ne $hash) { throw 'Copia no integra' }
        $txt = [IO.Path]::ChangeExtension($pdf,'.txt')
        if (-not (Test-Path -LiteralPath $txt)) {
            $temporary = Join-Path $root 'tmp/bibliografia-extraccion'
            New-Item -ItemType Directory -Path $temporary -Force | Out-Null
            Copy-Item -LiteralPath $pdf -Destination (Join-Path $temporary 'entrada.pdf')
            Push-Location $temporary
            try { & pdftotext -layout -enc UTF-8 entrada.pdf salida.txt; if ($LASTEXITCODE -ne 0) { throw 'Extraccion fallida' } }
            finally { Pop-Location }
            Move-Item -LiteralPath (Join-Path $temporary 'salida.txt') -Destination $txt
            Remove-Item -LiteralPath $temporary -Recurse -Force
        }
        $records += [ordered]@{titulo_catalogo=$title;autor_catalogo=$selection.author;origen=[IO.Path]::GetRelativePath($library,$source.FullName).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$pdf).Replace('\','/');sha256=$hash;txt=[IO.Path]::GetRelativePath($root,$txt).Replace('\','/');sha256_txt=(Get-FileHash -LiteralPath $txt).Hash.ToLowerInvariant();uso=$selection.use;estado='Disponible; no acredita lectura completa ni cita; edicion y localizadores requieren ficha'}
    }
    if ((Get-FileHash -LiteralPath $source.FullName).Hash.ToLowerInvariant() -ne $hash) { throw 'Original alterado' }
}
$records | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'bibliografia-incorporada-2026-10-11.json') -Encoding utf8
foreach ($record in $records) { if (-not(Test-Path -LiteralPath (Join-Path $root $record.txt))) {throw 'TXT ausente'} }
"$($records.Count) copias y TXT verificados; biblioteca Calibre intacta."