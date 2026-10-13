$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$record = Join-Path $PSScriptRoot 'renombrado-grabaciones-por-materia.json'
if (Test-Path -LiteralPath $record) { throw 'Renombrado ya registrado.' }
$records = @()
foreach ($slug in @('teoria-del-estado-y-constitucion','antecedentes-de-los-derechos-humanos','derecho-penal-especial-mexicano')) {
    $matter = Join-Path $root "UnADM/licenciatura-en-derecho-unadm/$slug-lde"
    $refs = Join-Path $matter "referencias-$slug"
    $source = Join-Path $refs 'grabaciones'
    $destination = Join-Path $refs "grabaciones-$slug"
    if (Test-Path -LiteralPath $destination) { throw "Destino existente: $destination" }
    $files = @(Get-ChildItem -LiteralPath $source -Recurse -File | ForEach-Object { @{archivo=[IO.Path]::GetRelativePath($source,$_.FullName);sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant()} })
    Move-Item -LiteralPath $source -Destination $destination
    foreach ($file in $files) { if ((Get-FileHash -LiteralPath (Join-Path $destination $file.archivo)).Hash.ToLowerInvariant() -ne $file.sha256) { throw 'Contenido alterado en traslado' } }
    foreach ($file in Get-ChildItem -LiteralPath $matter -Recurse -File -Filter '*.md' | Where-Object FullName -notmatch 'registros-organizacion|historico-control|comprobantes-envio|antes-') {
        $text = [IO.File]::ReadAllText($file.FullName)
        $updated = $text.Replace('grabaciones/',"grabaciones-$slug/")
        if ($updated -ne $text) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
    }
    $records += @{materia=$slug;origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$destination).Replace('\','/');archivos=$files}
}
$records | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $record -Encoding utf8
foreach ($item in $records) {
    foreach ($file in $item.archivos | Where-Object archivo -notlike '*.md') { if ((Get-FileHash -LiteralPath (Join-Path (Join-Path $root $item.destino) $file.archivo)).Hash.ToLowerInvariant() -ne $file.sha256) { throw 'Medio o procedencia alterado' } }
}
'Tres carpetas renombradas; archivos multimedia y procedencia intactos.'