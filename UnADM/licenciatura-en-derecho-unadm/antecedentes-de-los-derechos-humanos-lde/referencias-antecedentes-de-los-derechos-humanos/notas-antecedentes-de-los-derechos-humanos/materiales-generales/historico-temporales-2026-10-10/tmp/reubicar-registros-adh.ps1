$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
$refs = Join-Path $root 'referencias-antecedentes-de-los-derechos-humanos'
$notes = Join-Path $refs 'notas-antecedentes-de-los-derechos-humanos'
$activity = Join-Path $notes 'actividad-4-foro-de-participacion'
$general = Join-Path $notes 'materiales-generales/registros-organizacion'
$mapping = @{}
foreach ($name in @('inventario-aula.json','organizacion-materiales.json','renombrado-bibliografia.json','deduplicacion-bibliografia.json')) {
    $mapping[(Join-Path $refs $name)] = Join-Path $general $name
}
$mapping[(Join-Path $refs 'libros-antecedentes-de-los-derechos-humanos/inventario-libros.json')] = Join-Path $general 'inventario-libros.json'
$mapping[(Join-Path $refs 'REVISION-FOROS-Y-REPLICAS-S2.md')] = Join-Path $activity 'REVISION-FOROS-Y-REPLICAS-S2.md'
$mapping[(Join-Path $root 'participacion-foro-S2.md')] = Join-Path $activity 'participacion-foro-S2.md'
foreach ($entry in @(
    @{source=(Join-Path $refs 'envio-foro-S2-2026-10-10');target=(Join-Path $activity 'comprobantes-envio')},
    @{source=(Join-Path $refs 'auditoria-semana-2-2026-10-09');target=(Join-Path $notes 'materiales-generales/auditoria-semana-2-2026-10-09')}
)) {
    foreach ($file in Get-ChildItem -LiteralPath $entry.source -Recurse -File) {
        $mapping[$file.FullName] = Join-Path $entry.target ([IO.Path]::GetRelativePath($entry.source,$file.FullName))
    }
}
$records = @()
foreach ($source in $mapping.Keys) {
    if (-not(Test-Path -LiteralPath $source)) { throw "Origen ausente: $source" }
    if (Test-Path -LiteralPath $mapping[$source]) { throw 'Destino existente' }
    $records += [pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$mapping[$source]).Replace('\','/');sha256=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()}
}
$documents = @(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.json'))
foreach ($file in $documents) {
    $oldDirectory = $file.DirectoryName
    $targetFile = $file.FullName
    if ($mapping.ContainsKey($targetFile)) { $targetFile=$mapping[$targetFile] }
    $newDirectory = Split-Path $targetFile
    $content = [IO.File]::ReadAllText($file.FullName)
    if ($file.Extension -eq '.md') {
        $content = [regex]::Replace($content,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
            $url=$match.Groups[1].Value
            if ($url -match '^[a-z]+://|^#') { return $match.Value }
            $parts=$url.Split('#',2)
            $absolute=[IO.Path]::GetFullPath((Join-Path $oldDirectory ([Uri]::UnescapeDataString($parts[0]))))
            if ($mapping.ContainsKey($absolute)) { $absolute=$mapping[$absolute] }
            $relative=[IO.Path]::GetRelativePath($newDirectory,$absolute).Replace('\','/').Replace(' ','%20')
            if ($parts.Count -gt 1) { $relative+='#'+$parts[1] }
            return "]($relative)"
        })
    } else {
        $data = $content | ConvertFrom-Json
        function Rebase-Node($node) {
            if ($node -is [array]) { foreach($child in $node){Rebase-Node $child}; return }
            if ($node -isnot [pscustomobject]) { return }
            foreach($property in $node.PSObject.Properties) {
                if ($property.Value -is [string] -and $property.Name -in @('file','archivo','archivo_local','destino')) {
                    $base=$oldDirectory; $newBase=$newDirectory
                    if ($property.Name -eq 'destino') { $base=$root; $newBase=$root }
                    $absolute=[IO.Path]::GetFullPath((Join-Path $base $property.Value))
                    if ($mapping.ContainsKey($absolute)) { $absolute=$mapping[$absolute] }
                    if ((Test-Path -LiteralPath $absolute) -or ($mapping.Values -contains $absolute)) {
                        $property.Value=[IO.Path]::GetRelativePath($newBase,$absolute).Replace('\','/')
                    }
                } else { Rebase-Node $property.Value }
            }
        }
        Rebase-Node $data
        $content=$data | ConvertTo-Json -Depth 100
    }
    New-Item -ItemType Directory -Path $newDirectory -Force | Out-Null
    [IO.File]::WriteAllText($targetFile,$content,[Text.UTF8Encoding]::new($false))
}
foreach ($source in $mapping.Keys) {
    $target=$mapping[$source]
    if (-not(Test-Path -LiteralPath $target)) {
        New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
        Move-Item -LiteralPath $source -Destination $target
    } else { Remove-Item -LiteralPath $source }
}
foreach ($directory in @((Join-Path $refs 'envio-foro-S2-2026-10-10'),(Join-Path $refs 'auditoria-semana-2-2026-10-09'))) {
    if (Get-ChildItem -LiteralPath $directory -Recurse -File) { throw 'Directorio no vacio' }
    Remove-Item -LiteralPath $directory -Recurse
}
$report=[pscustomobject]@{fecha='2026-10-10';criterio='Foro en actividad 4, registros transversales en notas generales';movimientos=$records;nota='Hashes previos al cambio de rutas JSON y enlaces MD; documentos binarios no modificados'}
[IO.File]::WriteAllText((Join-Path $general 'reubicacion-registros.json'),($report | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -Filter '*.md') {
    foreach($match in [regex]::Matches([IO.File]::ReadAllText($file.FullName),'\]\(([^)]+)\)')) {
        $url=$match.Groups[1].Value
        if($url -match '^[a-z]+://|^#'){continue}
        $target=Join-Path $file.DirectoryName ([Uri]::UnescapeDataString(($url -split '#')[0]))
        if(-not(Test-Path -LiteralPath $target)){throw "Enlace roto: $($file.Name) -> $url"}
    }
}
Write-Output "$($records.Count) registros trasladados; enlaces Markdown verificados."