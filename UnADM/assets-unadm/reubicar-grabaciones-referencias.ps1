$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$moves = @()
$folderMap = @{}
foreach ($slug in @('teoria-del-estado-y-constitucion','antecedentes-de-los-derechos-humanos','derecho-penal-especial-mexicano')) {
    $matter = Join-Path $root "UnADM/licenciatura-en-derecho-unadm/$slug-lde"
    $refs = Join-Path $matter "referencias-$slug"
    $source = Join-Path $refs "notas-$slug/materiales-generales/grabaciones"
    $target = Join-Path $refs 'grabaciones'
    if (Test-Path -LiteralPath $target) { throw "Destino existente: $target" }
    $files = @(Get-ChildItem -LiteralPath $source -Recurse -File | ForEach-Object { @{ruta=[IO.Path]::GetRelativePath($source,$_.FullName);sha256=(Get-FileHash -LiteralPath $_.FullName).Hash} })
    Move-Item -LiteralPath $source -Destination $target
    foreach ($file in $files) { if((Get-FileHash -LiteralPath (Join-Path $target $file.ruta)).Hash -ne $file.sha256){throw 'Hash alterado'} }
    $folderMap[$source] = $target
    $moves += @{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$target).Replace('\','/');archivos=$files}
}
$markdown = @(Get-ChildItem -LiteralPath (Join-Path $root 'UnADM/licenciatura-en-derecho-unadm') -Recurse -Filter '*.md' -File)
$markdown += Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.md' -File
foreach ($file in $markdown | Where-Object FullName -notmatch 'registros-organizacion|comprobantes-envio|historico-control|antes-') {
    $oldDirectory = $file.DirectoryName
    foreach ($source in $folderMap.Keys) {
        $target = $folderMap[$source]
        if ($oldDirectory.StartsWith($target, [StringComparison]::OrdinalIgnoreCase)) { $oldDirectory = $source + $oldDirectory.Substring($target.Length) }
    }
    $text = [IO.File]::ReadAllText($file.FullName)
    $updated = [regex]::Replace($text,'\]\(([^)]+)\)', { param($match)
        $href = $match.Groups[1].Value
        if ($href -match '^[a-z]+:|^#') { return $match.Value }
        $parts = $href.Split('#',2)
        $path = [IO.Path]::GetFullPath((Join-Path $oldDirectory ([Uri]::UnescapeDataString($parts[0]))))
        foreach ($source in $folderMap.Keys) { if($path.StartsWith($source,[StringComparison]::OrdinalIgnoreCase)) { $path = $folderMap[$source] + $path.Substring($source.Length) } }
        if (-not(Test-Path -LiteralPath $path)) { return $match.Value }
        $relative = [IO.Path]::GetRelativePath($file.DirectoryName,$path).Replace('\','/').Replace(' ','%20')
        if($parts.Length -gt 1){$relative += '#'+$parts[1]}
        return ']('+$relative+')'
    })
    $updated = $updated.Replace('referencias-<materia>/notas-<materia>/materiales-generales/grabaciones/','referencias-<materia>/grabaciones/')
    $updated = $updated.Replace('materiales-generales/grabaciones/','grabaciones/')
    if($updated -ne $text){[IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false))}
}
$moves | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'reubicacion-grabaciones-referencias.json') -Encoding utf8
foreach ($move in $moves) {
    $target = Join-Path $root $move.destino
    foreach ($file in $move.archivos | Where-Object ruta -notlike '*.md') { if((Get-FileHash -LiteralPath (Join-Path $target $file.ruta)).Hash -ne $file.sha256){throw 'Archivo no Markdown alterado'} }
}
'Tres carpetas trasladadas; medios y procedencia intactos; enlaces actualizados.'