$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$manifest = Join-Path $PSScriptRoot 'limpieza-grabaciones-2026-10-12.json'
if (Test-Path -LiteralPath $manifest) { throw 'Limpieza ya registrada; no repetir.' }
$finals = @(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'grabaciones-combinadas.json') -Raw | ConvertFrom-Json)
$deletions = @()
$moves = @()
$map = @{}
$origins = @{}
foreach ($item in $finals) {
    $pdf = Join-Path $root $item.archivo
    if ((Get-FileHash -LiteralPath $pdf).Hash.ToLowerInvariant() -ne $item.sha256) { throw 'MP4 final no coincide; no borrar fuentes.' }
    $info = (& ffprobe -v error -show_streams -show_format -of json $pdf | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) { throw 'MP4 no legible' }
    $duration = [double]::Parse($info.format.duration,[Globalization.CultureInfo]::InvariantCulture)
    if (@($info.streams | Where-Object codec_type -eq 'video').Count -ne 1 -or @($info.streams | Where-Object codec_type -eq 'audio').Count -ne 1 -or [Math]::Abs($duration-$item.duracion_segundos) -gt 2) { throw 'MP4 incompleto' }
    $folder = Split-Path $pdf
    $receipt = Join-Path $folder "Grabacion - $($item.fecha) - procedencia.json"
    $data = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    foreach ($source in $data.archivos) {
        $path = Join-Path $folder $source.archivo
        if ([IO.Path]::GetExtension($path) -notin @('.webm','.m4a')) { throw 'Archivo no autorizado para eliminar' }
        if ((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -ne $source.sha256) { throw 'Fuente no coincide; revisar antes de borrar' }
        $deletions += @{archivo=[IO.Path]::GetRelativePath($root,$path).Replace('\','/');sha256=$source.sha256;bytes=(Get-Item -LiteralPath $path).Length;reemplazo=$item.archivo}
    }
}
$folders = @($finals | ForEach-Object { Split-Path (Join-Path $root $_.archivo) } | Select-Object -Unique)
foreach ($folder in $folders) {
    $slug = (Split-Path $folder -Leaf).Substring('grabaciones-'.Length)
    $refs = Split-Path $folder
    $control = Join-Path $refs "notas-$slug/materiales-generales/control-grabaciones"
    foreach ($file in Get-ChildItem -LiteralPath $folder -File | Where-Object Extension -in @('.json','.md')) {
        $target = Join-Path $control $file.Name
        if (Test-Path -LiteralPath $target) { throw "Destino existente: $target" }
        $moves += @{origen=$file.FullName;destino=$target;sha256=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
        $map[$file.FullName] = $target
        $origins[$target] = $file.FullName
    }
}
foreach ($item in $moves) {
    New-Item -ItemType Directory -Path (Split-Path $item.destino) -Force | Out-Null
    Move-Item -LiteralPath $item.origen -Destination $item.destino
    if ((Get-FileHash -LiteralPath $item.destino).Hash.ToLowerInvariant() -ne $item.sha256) { throw 'Control alterado durante traslado' }
}
$markdown = @(Get-ChildItem -LiteralPath (Join-Path $root 'UnADM/licenciatura-en-derecho-unadm') -Recurse -Filter '*.md' -File)
foreach ($file in $markdown | Where-Object FullName -notmatch 'registros-organizacion|historico-control|comprobantes-envio|antes-') {
    $origin = if ($origins.ContainsKey($file.FullName)) { $origins[$file.FullName] } else { $file.FullName }
    $text = [IO.File]::ReadAllText($file.FullName)
    $updated = [regex]::Replace($text,'\]\(([^)]+)\)', { param($match)
        $href = $match.Groups[1].Value
        if ($href -match '^[a-z]+:|^#') { return $match.Value }
        $parts = $href.Split('#',2)
        $target = [IO.Path]::GetFullPath((Join-Path (Split-Path $origin) ([Uri]::UnescapeDataString($parts[0]))))
        if ($map.ContainsKey($target)) { $target = $map[$target] }
        if (-not (Test-Path -LiteralPath $target)) { return $match.Value }
        $relative = [IO.Path]::GetRelativePath($file.DirectoryName,$target).Replace('\','/').Replace(' ','%20')
        if ($parts.Length -gt 1) { $relative += '#' + $parts[1] }
        return '](' + $relative + ')'
    })
    if ($updated -ne $text) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
@{fecha='2026-10-12';autorizacion='Usuario solicita eliminar lo que no se requerira';eliminaciones=$deletions;controles_trasladados=$moves;mp4_preservados=$finals;nota='WEBM y M4A eliminados tras verificar MP4 finales; no son duplicados binarios. Fuentes necesarias para recomponer se recuperarian del aula. No tocar SRT, libros o entregas.'} | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $manifest -Encoding utf8
foreach ($item in $deletions) { Remove-Item -LiteralPath (Join-Path $root $item.archivo) }
foreach ($item in $finals) { if ((Get-FileHash -LiteralPath (Join-Path $root $item.archivo)).Hash.ToLowerInvariant() -ne $item.sha256) { throw 'MP4 final alterado' } }
foreach ($folder in $folders) {
    if (@(Get-ChildItem -LiteralPath $folder -Directory).Count) { throw 'No se permiten subcarpetas' }
    $extras = @(Get-ChildItem -LiteralPath $folder -File | Where-Object Extension -notin @('.mp4','.srt'))
    if ($extras.Count) { throw 'Archivos desconocidos conservados; revisar' }
}
"$($deletions.Count) auxiliares eliminados; $($moves.Count) controles preservados fuera de grabaciones; cinco MP4 intactos."