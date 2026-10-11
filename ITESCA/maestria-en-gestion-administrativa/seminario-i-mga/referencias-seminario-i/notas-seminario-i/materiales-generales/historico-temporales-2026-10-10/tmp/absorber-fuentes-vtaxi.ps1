$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
$refs = Join-Path $root 'referencias-seminario-i'
$sourceFolder = Join-Path $refs 'vtaxi-2026-09-27'
$notes = Join-Path $refs 'notas-seminario-i'
$mapping = @{}
$records = @()
foreach ($file in Get-ChildItem -LiteralPath $sourceFolder -File) {
    $activity = 'actividad-8-antecedentes/fuentes-vtaxi-2026-09-27'
    if ($file.Name -in @('omrani-metadatos.txt','troise-metadatos.txt')) { $activity = 'actividad-3-estado-del-arte/verificacion-bibliografica-2026-09-27' }
    $destination = Join-Path $notes ($activity+'/'+$file.Name)
    if (Test-Path -LiteralPath $destination) { throw "Destino existente: $destination" }
    $mapping[$file.FullName] = $destination
    $records += [pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$file.FullName).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$destination).Replace('\','/');sha256=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
}
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.Extension -in @('.md','.json','.tex','.bib','.py') -and -not $_.FullName.StartsWith($sourceFolder+[IO.Path]::DirectorySeparatorChar) }) {
    $content = [IO.File]::ReadAllText($file.FullName)
    $updated = $content
    if ($file.Extension -eq '.md') {
        $updated = [regex]::Replace($updated,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
            $url = $match.Groups[1].Value
            if ($url -match '^[a-z]+://|^#') { return $match.Value }
            $parts = $url.Split('#',2)
            $absolute = [IO.Path]::GetFullPath((Join-Path $file.DirectoryName ([Uri]::UnescapeDataString($parts[0]))))
            if (-not $mapping.ContainsKey($absolute)) { return $match.Value }
            $relative = [IO.Path]::GetRelativePath($file.DirectoryName,$mapping[$absolute]).Replace('\','/').Replace(' ','%20')
            if ($parts.Count -gt 1) { $relative += '#'+$parts[1] }
            return "]($relative)"
        })
    }
    foreach ($record in $records) { $updated = $updated.Replace($record.origen,$record.destino) }
    $updated = $updated.Replace('`referencias-seminario-i/vtaxi-2026-09-27/`','`referencias-seminario-i/notas-seminario-i/actividad-8-antecedentes/fuentes-vtaxi-2026-09-27/`')
    if ($updated -ne $content) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
foreach ($record in $records) {
    $source = Join-Path $root $record.origen
    $destination = Join-Path $root $record.destino
    New-Item -ItemType Directory -Path (Split-Path $destination) -Force | Out-Null
    Move-Item -LiteralPath $source -Destination $destination
    if ((Get-FileHash -LiteralPath $destination).Hash.ToLowerInvariant() -ne $record.sha256) { throw 'Contenido alterado' }
}
Remove-Item -LiteralPath $sourceFolder
[IO.File]::WriteAllText((Join-Path $notes 'materiales-generales/absorcion-fuentes-vtaxi-2026-10-10.json'),(@{fecha='2026-10-10';movimientos=$records;criterio='Metadatos del corpus en T3; fuentes de diagnostico en T8, compartidas con T9 y T10';copias_internas_sin_modificar=$true} | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
Write-Output "$($records.Count) archivos redistribuidos con SHA256 intacto; carpeta original retirada."