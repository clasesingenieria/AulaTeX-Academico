$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../../')).Path
$notes = 'referencias-teoria-del-estado-y-constitucion/notas-teoria-del-estado-y-constitucion'
$planning = 'planeaciones-teoria-del-estado-y-constitucion'
$map = @{
    "$planning/planeacion-S2.md" = "$notes/actividad-02-linea-de-tiempo/planeacion-S2.md"
    "$planning/planeacion-S3.md" = "$notes/actividad-03-analisis-de-hechos/planeacion-S3.md"
    "$planning/README.md" = "$notes/materiales-generales/historico-control/README-planeaciones-antes-absorcion.md"
}
$record = Join-Path $PSScriptRoot 'absorcion-md.json'
if (Test-Path -LiteralPath $record) { throw 'Absorcion ya registrada.' }
$moves = @()
$origins = @{}
$protected = @(Get-ChildItem -LiteralPath (Join-Path $root 'Entregas') -File | ForEach-Object { @{archivo=[IO.Path]::GetRelativePath($root,$_.FullName);sha256=(Get-FileHash -LiteralPath $_.FullName).Hash} })
foreach ($old in $map.Keys) {
    $source = Join-Path $root $old
    $target = Join-Path $root $map[$old]
    if (Test-Path -LiteralPath $target) { throw "Destino existente: $target" }
    $hash = (Get-FileHash -LiteralPath $source).Hash
    Move-Item -LiteralPath $source -Destination $target
    if ((Get-FileHash -LiteralPath $target).Hash -ne $hash) { throw 'Hash alterado en traslado' }
    $moves += @{origen=$old;destino=$map[$old];sha256_original=$hash}
    $origins[$map[$old]] = $old
}
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.md' | Where-Object FullName -notmatch 'registros-organizacion|historico-control|comprobantes-envio|extractor-aulatex') {
    $current = [IO.Path]::GetRelativePath($root,$file.FullName).Replace('\','/')
    $original = if ($origins.ContainsKey($current)) { $origins[$current] } else { $current }
    $text = [IO.File]::ReadAllText($file.FullName)
    $updated = [regex]::Replace($text,'\]\(([^)]+)\)', { param($match)
        $href = $match.Groups[1].Value
        if ($href -match '^[a-z]+:|^#') { return $match.Value }
        $parts = $href.Split('#',2)
        $target = [IO.Path]::GetFullPath((Join-Path (Split-Path (Join-Path $root $original)) ([Uri]::UnescapeDataString($parts[0]))))
        $relative = [IO.Path]::GetRelativePath($root,$target).Replace('\','/')
        if ($relative -eq "$planning/README.md") { $target = Join-Path $root 'README.md' }
        elseif ($map.ContainsKey($relative)) { $target = Join-Path $root $map[$relative] }
        if (-not (Test-Path -LiteralPath $target)) { return $match.Value }
        $newHref = [IO.Path]::GetRelativePath($file.DirectoryName,$target).Replace('\','/').Replace(' ','%20')
        if ($parts.Length -gt 1) { $newHref += '#' + $parts[1] }
        return '](' + $newHref + ')'
    })
    if ($text -ne $updated) {
        $backup = Join-Path $PSScriptRoot "antes-absorcion-md/$current"
        New-Item -ItemType Directory -Path (Split-Path $backup) -Force | Out-Null
        [IO.File]::WriteAllText($backup,$text,[Text.UTF8Encoding]::new($false))
        [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false))
    }
}
foreach ($item in $moves) { $item.sha256_actual=(Get-FileHash -LiteralPath (Join-Path $root $item.destino)).Hash }
foreach ($item in $protected) { if((Get-FileHash -LiteralPath (Join-Path $root $item.archivo)).Hash -ne $item.sha256){throw 'Entrega alterada'} }
@{fecha='2026-10-11';movimientos=$moves;entregas_protegidas=$protected;nota='Traslado posterior al manifiesto previo; hash original y revisado separados; enlaces rebasados y originales respaldados.'} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $record -Encoding utf8
if (@(Get-ChildItem -LiteralPath (Join-Path $root $planning) -Filter '*.md').Count) { throw 'Quedan Markdown en planeaciones' }
'Tres Markdown absorbidos; PDF/TXT y entrega preservados.'