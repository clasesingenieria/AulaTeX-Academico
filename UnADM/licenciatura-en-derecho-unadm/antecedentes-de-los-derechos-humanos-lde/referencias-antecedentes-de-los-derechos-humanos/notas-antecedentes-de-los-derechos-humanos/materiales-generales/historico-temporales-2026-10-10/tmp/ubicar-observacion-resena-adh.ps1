$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
$notes = Join-Path $root 'referencias-antecedentes-de-los-derechos-humanos/notas-antecedentes-de-los-derechos-humanos'
$source = Join-Path $notes 'materiales-generales/auditorias/semana-2-2026-10-09/observacion-resena-2026-10-09-185726'
$target = Join-Path $notes 'actividad-3-resena-critica-de-video/evaluacion-local/2026-10-09-185726'
if (Test-Path -LiteralPath $target) { throw 'Destino existente' }
$mapping = @{}
foreach ($file in Get-ChildItem -LiteralPath $source -File) { $mapping[$file.FullName] = Join-Path $target $file.Name }
New-Item -ItemType Directory -Path $target -Force | Out-Null
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.json')) {
    $newPath = $file.FullName
    if ($mapping.ContainsKey($newPath)) { $newPath = $mapping[$newPath] }
    $content = [IO.File]::ReadAllText($file.FullName)
    if ($file.Extension -eq '.md') {
        $content = [regex]::Replace($content,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
            $url = $match.Groups[1].Value
            if ($url -match '^[a-z]+://|^#') { return $match.Value }
            $parts = $url.Split('#',2)
            $absolute = [IO.Path]::GetFullPath((Join-Path $file.DirectoryName ([Uri]::UnescapeDataString($parts[0]))))
            if ($mapping.ContainsKey($absolute)) { $absolute = $mapping[$absolute] }
            $relative = [IO.Path]::GetRelativePath((Split-Path $newPath),$absolute).Replace('\','/').Replace(' ','%20')
            if ($parts.Count -gt 1) { $relative += '#'+$parts[1] }
            return "]($relative)"
        })
    } else {
        $data = $content | ConvertFrom-Json
        function Fix-Paths($node) {
            if ($node -is [array]) { foreach ($child in $node) { Fix-Paths $child }; return }
            if ($node -isnot [pscustomobject]) { return }
            foreach ($property in $node.PSObject.Properties) {
                if ($property.Value -is [string] -and $property.Name -notin @('origen','texto','ruta_historica') -and $property.Value -notmatch '^[a-z]+://|[\r\n]' -and $property.Value.Length -lt 400) {
                    $bases = @($file.DirectoryName,$root)
                    if ($property.Name -eq 'destino') { $bases = @($root,$file.DirectoryName) }
                    foreach ($base in $bases) {
                        try { $absolute = [IO.Path]::GetFullPath((Join-Path $base $property.Value)) } catch { continue }
                        $mapped = $mapping.ContainsKey($absolute)
                        if ($mapped) { $absolute = $mapping[$absolute] }
                        if ($mapped -or ($newPath -ne $file.FullName -and (Test-Path -LiteralPath $absolute -PathType Leaf))) {
                            $newBase = Split-Path $newPath
                            if ($base -eq $root) { $newBase = $root }
                            $property.Value = [IO.Path]::GetRelativePath($newBase,$absolute).Replace('\','/')
                            break
                        }
                    }
                } else { Fix-Paths $property.Value }
            }
        }
        Fix-Paths $data
        $content = $data | ConvertTo-Json -Depth 100
    }
    if ($content -ne [IO.File]::ReadAllText($file.FullName) -or $newPath -ne $file.FullName) { [IO.File]::WriteAllText($newPath,$content,[Text.UTF8Encoding]::new($false)) }
}
foreach ($oldPath in $mapping.Keys) { if (-not(Test-Path -LiteralPath $mapping[$oldPath])) { throw 'Traslado incompleto' }; Remove-Item -LiteralPath $oldPath }
Remove-Item -LiteralPath $source
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -Filter '*.md') {
    foreach ($match in [regex]::Matches([IO.File]::ReadAllText($file.FullName),'\]\(([^)]+)\)')) {
        $url = $match.Groups[1].Value
        if ($url -match '^[a-z]+://|^#') { continue }
        if (-not(Test-Path -LiteralPath (Join-Path $file.DirectoryName ([Uri]::UnescapeDataString(($url -split '#')[0]))))) { throw "Enlace roto: $url" }
    }
}
Write-Output 'Cuatro registros asignados a actividad 3; enlaces verificados.'