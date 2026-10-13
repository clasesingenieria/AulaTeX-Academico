$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$map = [ordered]@{
    'Constitucion-Politica-de-los-Estados-Unidos-Mexicanos-copia-biblioteca' = 'Constitucion Politica de los Estados Unidos Mexicanos (copia biblioteca) - Camara de Diputados'
    'CPEUM-consulta-2026-10-09' = 'Constitucion Politica de los Estados Unidos Mexicanos (consulta 2026-10-09) - Camara de Diputados'
    'Del-espiritu-de-las-leyes-Montesquieu' = 'Del espiritu de las leyes - Montesquieu'
    'El-contrato-social-Juan-Jacobo-Rousseau' = 'El contrato social - Juan Jacobo Rousseau'
    'En-defensa-del-Estado-de-Derecho-Ignacio-Campoy-Cervera' = 'En defensa del Estado de Derecho - Ignacio Campoy Cervera'
    'Garcia-Ricci-2011' = 'Estado de derecho y principio de legalidad (2011) - Diego Garcia Ricci'
    'Introduccion-al-estudio-del-Derecho-Eduardo-Garcia-Maynez' = 'Introduccion al estudio del Derecho - Eduardo Garcia Maynez'
    'Nociones-de-hermeneutica-e-interpretacion-juridica-Javier-Hernandez-Manriquez' = 'Nociones de hermeneutica e interpretacion juridica - Javier Hernandez Manriquez'
    'Razon-y-voluntad-en-el-Estado-de-Derecho-Francisco-Javier-Ansuategui-Roig' = 'Razon y voluntad en el Estado de Derecho - Francisco Javier Ansuategui Roig'
    'Sentimientos-de-la-nacion-El-sitio-de-Cuautla-Heriberto-Frias' = 'Sentimientos de la nacion y El sitio de Cuautla - Heriberto Frias'
    'Teoria-general-del-Estado-2a-edicion-Eduardo-Andrade-Sanchez' = 'Teoria general del Estado (2a edicion) - Eduardo Andrade Sanchez'
    'Teoria-pura-del-Derecho-Hans-Kelsen' = 'Teoria pura del Derecho - Hans Kelsen'
    'Criminologia-fundamentos-y-principios-Antonio-Garcia-Pablos-de-Molina' = 'Criminologia fundamentos y principios - Antonio Garcia-Pablos de Molina'
    'Curso-de-argumentacion-juridica-Manuel-Atienza' = 'Curso de argumentacion juridica - Manuel Atienza'
    'Derecho-penal-4a-edicion-Griselda-Amuchategui-Requena' = 'Derecho penal (4a edicion) - Griselda Amuchategui Requena'
    'Derecho-penal-Parte-general-Jesus-Maria-Silva-Sanchez' = 'Derecho penal Parte general - Jesus Maria Silva Sanchez'
}
$folders = @('teoria-del-estado-y-constitucion','derecho-penal-especial-mexicano') | ForEach-Object { Join-Path $root "UnADM/licenciatura-en-derecho-unadm/$_-lde" }
$recordPath = Join-Path $PSScriptRoot 'renombrado-libros-titulo-autor.json'
if (Test-Path -LiteralPath $recordPath) { throw 'Renombrado ya registrado.' }
$moves = @()
foreach ($folder in $folders) {
    $books = @(Get-ChildItem -LiteralPath $folder -Directory -Recurse | Where-Object Name -like 'libros-*')
    foreach ($directory in $books) {
        foreach ($old in $map.Keys) {
            foreach ($extension in @('.pdf','.txt')) {
                $source = Join-Path $directory.FullName ($old+$extension)
                $target = Join-Path $directory.FullName ($map[$old]+$extension)
                if (-not(Test-Path -LiteralPath $source)) { continue }
                if (Test-Path -LiteralPath $target) { throw "Destino existente: $target" }
                $hash = (Get-FileHash -LiteralPath $source).Hash
                Move-Item -LiteralPath $source -Destination $target
                if ((Get-FileHash -LiteralPath $target).Hash -ne $hash) { throw 'Contenido alterado' }
                $moves += @{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$target).Replace('\','/');sha256=$hash.ToLowerInvariant()}
            }
        }
    }
}
$files = @($folders | ForEach-Object {Get-ChildItem -LiteralPath $_ -Recurse -File})
$files += Get-ChildItem -LiteralPath $PSScriptRoot -File
foreach ($file in $files | Where-Object { $_.Extension -in @('.md','.json','.bib','.tex','.ps1') -and $_.FullName -ne $PSCommandPath -and $_.FullName -notmatch 'registros-organizacion|historico-control|comprobantes-envio|antes-|\\Entregas\\' }) {
    $original = [IO.File]::ReadAllText($file.FullName)
    $updated = $original
    foreach ($old in $map.Keys) {
        foreach ($extension in @('.pdf','.txt')) {
            if ($file.Extension -eq '.md') {
                $updated = $updated.Replace($old+$extension,($map[$old]+$extension).Replace(' ','%20'))
            } else { $updated = $updated.Replace($old+$extension,$map[$old]+$extension) }
        }
        if ($file.Name -eq 'incorporar-bibliografia-2026-10-11.ps1') { $updated = $updated.Replace("name='$old'","name='$($map[$old])'") }
    }
    if ($original -ne $updated) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
@{fecha='2026-10-11';formato='Titulo - Autor';movimientos=$moves;nota='Biblioteca Calibre y entregas intactas; registros historicos conservan nombres originales.'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $recordPath -Encoding utf8
foreach ($move in $moves) { if ((Get-FileHash -LiteralPath (Join-Path $root $move.destino)).Hash.ToLowerInvariant() -ne $move.sha256) { throw 'Hash final distinto' } }
"$($moves.Count) PDF/TXT renombrados con hashes verificados."