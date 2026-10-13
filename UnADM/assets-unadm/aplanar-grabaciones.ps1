$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$manifest = Join-Path $PSScriptRoot 'grabaciones-estructura-plana.json'
if (Test-Path -LiteralPath $manifest) { throw 'Migracion ya registrada.' }
$plans = @()
$map = @{}
$origins = @{}
$folders = @(Get-ChildItem -LiteralPath (Join-Path $root 'UnADM/licenciatura-en-derecho-unadm') -Recurse -Directory | Where-Object Name -like 'grabaciones-*')
foreach ($folder in $folders) {
    foreach ($file in Get-ChildItem -LiteralPath $folder.FullName -Recurse -File | Where-Object DirectoryName -ne $folder.FullName) {
        $name = $file.Name
        if ($name -eq 'LEEME.md') { $name = "Grabacion - $($file.Directory.Name) - LEEME.md" }
        if ($name -eq 'procedencia.json') { $name = "Grabacion - $($file.Directory.Name) - procedencia.json" }
        $target = Join-Path $folder.FullName $name
        if (Test-Path -LiteralPath $target) { throw "Destino existente: $target" }
        if (@($plans | Where-Object destino -eq $target).Count) { throw "Nombre repetido: $name" }
        $plans += @{origen=$file.FullName;destino=$target;sha256=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
        $map[$file.FullName] = $target
        $origins[$target] = $file.FullName
    }
}
foreach ($item in $plans) {
    Move-Item -LiteralPath $item.origen -Destination $item.destino
    if ((Get-FileHash -LiteralPath $item.destino).Hash.ToLowerInvariant() -ne $item.sha256) { throw 'Hash distinto' }
}
$files = @(Get-ChildItem -LiteralPath (Join-Path $root 'UnADM/licenciatura-en-derecho-unadm') -Recurse -File -Filter '*.md')
$files += Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.md' -File
foreach ($file in $files | Where-Object FullName -notmatch 'registros-organizacion|historico-control|comprobantes-envio|antes-') {
    $originalPath = if ($origins.ContainsKey($file.FullName)) { $origins[$file.FullName] } else { $file.FullName }
    $text = [IO.File]::ReadAllText($file.FullName)
    $updated = [regex]::Replace($text,'\]\(([^)]+)\)', { param($match)
        $href = $match.Groups[1].Value
        if ($href -match '^[a-z]+:|^#') { return $match.Value }
        $parts = $href.Split('#',2)
        $target = [IO.Path]::GetFullPath((Join-Path (Split-Path $originalPath) ([Uri]::UnescapeDataString($parts[0]))))
        if ($map.ContainsKey($target)) { $target = $map[$target] }
        if (-not (Test-Path -LiteralPath $target)) { return $match.Value }
        $relative = [IO.Path]::GetRelativePath($file.DirectoryName,$target).Replace('\','/').Replace(' ','%20')
        if ($parts.Length -gt 1) { $relative += '#' + $parts[1] }
        return '](' + $relative + ')'
    })
    if ($text -ne $updated) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
foreach ($folder in $folders) {
    Get-ChildItem -LiteralPath $folder.FullName -Recurse -Directory | Sort-Object {$_.FullName.Length} -Descending | ForEach-Object {
        if (@(Get-ChildItem -LiteralPath $_.FullName -Force).Count) { throw 'Directorio no vacio: conservar' }
        Remove-Item -LiteralPath $_.FullName
    }
    if (@(Get-ChildItem -LiteralPath $folder.FullName -Directory).Count) { throw 'Quedan subcarpetas' }
}
$records = @($plans | ForEach-Object { @{origen=[IO.Path]::GetRelativePath($root,$_.origen).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$_.destino).Replace('\','/');sha256_original=$_.sha256;sha256_actual=(Get-FileHash -LiteralPath $_.destino).Hash.ToLowerInvariant()} })
$records | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifest -Encoding utf8
foreach ($item in $plans | Where-Object destino -notlike '*.md') { if((Get-FileHash -LiteralPath $item.destino).Hash.ToLowerInvariant() -ne $item.sha256){throw 'Medio o procedencia alterado'} }
"$($plans.Count) archivos reubicados; tres carpetas planas; medios y procedencia intactos."