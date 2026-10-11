$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
$target = Join-Path $root 'Readme - Seminario I.md'
if (Test-Path -LiteralPath $target) { throw 'El destino ya existe; no se sobrescribira' }
$sources = @('README.md','referencias-seminario-i/README.md','referencias-seminario-i/notas-seminario-i/README.md')
$mapping = @{}
foreach ($relative in $sources) { $mapping[(Join-Path $root $relative)] = $target }
$sections = @()
foreach ($relative in $sources) {
    $path = Join-Path $root $relative
    $content = [IO.File]::ReadAllText($path)
    $directory = Split-Path $path
    $content = [regex]::Replace($content,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{ param($match)
        $url = $match.Groups[1].Value
        if ($url -match '^[a-z]+://|^#') { return $match.Value }
        $parts = $url.Split('#',2)
        $absolute = [IO.Path]::GetFullPath((Join-Path $directory ([Uri]::UnescapeDataString($parts[0]))))
        if ($mapping.ContainsKey($absolute)) { $absolute = $target }
        $newRelative = [IO.Path]::GetRelativePath($root,$absolute).Replace('\','/').Replace(' ','%20')
        if ($parts.Count -gt 1) { $newRelative += '#'+$parts[1] }
        return "]($newRelative)"
    })
    if ($relative -ne 'README.md') {
        $content = [regex]::Replace($content,'(?m)^(#{1,5}) ', '$1# ')
        $content = [regex]::Replace($content,'`([^`\r\n]+)`',[Text.RegularExpressions.MatchEvaluator]{ param($match)
            $value = $match.Groups[1].Value
            if ($value -match '^[a-z]+://') { return $match.Value }
            try { $absolute = [IO.Path]::GetFullPath((Join-Path $directory $value)) } catch { return $match.Value }
            if (-not (Test-Path -LiteralPath $absolute)) { return $match.Value }
            $newRelative = [IO.Path]::GetRelativePath($root,$absolute).Replace('\','/')
            return '`'+$newRelative+'`'
        })
    }
    $sections += $content.Trim()
}
$merged = ($sections -join "`n`n") + "`n"
$merged = $merged.Replace('[Notas por actividad](Readme%20-%20Seminario%20I.md)', '[Notas por actividad](#notas-seminario-i)')
$merged = $merged.Replace('[notas por actividad](Readme%20-%20Seminario%20I.md)', '[notas por actividad](#notas-seminario-i)')
$merged += "`n## Consolidacion documental`n`nLos tres indices de materia, referencias y notas se integraron en este documento el 10 de octubre de 2026. Se conservaron sus contenidos y se recalcularon rutas. Las consignas, revisiones, notas academicas y README tecnicos por producto permanecen separados. No se modificaron entregas ni reportes.`n"
[IO.File]::WriteAllText($target,$merged,[Text.UTF8Encoding]::new($false))
foreach ($file in Get-ChildItem -LiteralPath 'C:/Users/Sysx/Documents/AulaTeX-Academico' -Recurse -File -Filter '*.md' | Where-Object { $_.FullName -notmatch '\\(node_modules|\.git|\.venv)\\' -and -not ($mapping.Keys -contains $_.FullName) -and $_.FullName -ne $target }) {
    $text = [IO.File]::ReadAllText($file.FullName)
    $updated = [regex]::Replace($text,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{ param($match)
        $url = $match.Groups[1].Value
        if ($url -match '^[a-z]+://|^#') { return $match.Value }
        $parts = $url.Split('#',2)
        try { $absolute = [IO.Path]::GetFullPath((Join-Path $file.DirectoryName ([Uri]::UnescapeDataString($parts[0])))) } catch { return $match.Value }
        if (-not $mapping.ContainsKey($absolute)) { return $match.Value }
        $newRelative = [IO.Path]::GetRelativePath($file.DirectoryName,$target).Replace('\','/').Replace(' ','%20')
        if ($parts.Count -gt 1) { $newRelative += '#'+$parts[1] }
        return "]($newRelative)"
    })
    if ($updated -ne $text) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
foreach ($path in $mapping.Keys) { Remove-Item -LiteralPath $path }
foreach ($match in [regex]::Matches($merged,'\]\(([^)]+)\)')) {
    $url = $match.Groups[1].Value
    if ($url -match '^[a-z]+://|^#') { continue }
    if (-not (Test-Path -LiteralPath (Join-Path $root ([Uri]::UnescapeDataString(($url -split '#')[0]))))) { throw "Enlace roto: $url" }
}
Write-Output 'Tres indices absorbidos; enlaces del Readme unico verificados.'