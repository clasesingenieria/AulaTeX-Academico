$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
$registryPath = Join-Path $root 'assets-plan-de-negocios/portadas-word/registro-word.json'
$records = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json
foreach ($record in $records) {
    if ((Get-FileHash -LiteralPath (Join-Path $root $record.respaldo)).Hash.ToLowerInvariant() -ne $record.sha256_original) { throw 'Respaldo distinto' }
    if ((Get-FileHash -LiteralPath (Join-Path $root $record.destino)).Hash.ToLowerInvariant() -ne $record.sha256_word_nuevo) { throw 'Word nuevo distinto' }
    if (-not(Test-Path -LiteralPath ([IO.Path]::ChangeExtension((Join-Path $root $record.destino),'.pdf')))) { throw 'PDF ausente' }
}
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.Extension -in @('.md','.json','.py','.ps1','.tex') -and $_.FullName -notmatch '\\(word-antes-portada-oficial|portadas-word)\\' -and $_.Name -ne 'finalizar-ubicacion-word.ps1' }) {
    $text = [IO.File]::ReadAllText($file.FullName)
    $updated = $text
    if ($file.Extension -eq '.md') {
        $updated = [regex]::Replace($updated,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
            $url = $match.Groups[1].Value
            if ($url -match '^[a-z]+://|^#') { return $match.Value }
            $parts = $url.Split('#',2)
            try { $absolute = [IO.Path]::GetFullPath((Join-Path $file.DirectoryName ([Uri]::UnescapeDataString($parts[0])))) } catch { return $match.Value }
            foreach ($record in $records) {
                if ($absolute -eq [IO.Path]::GetFullPath((Join-Path $root $record.origen))) {
                    $relative = [IO.Path]::GetRelativePath($file.DirectoryName,(Join-Path $root $record.destino)).Replace('\','/').Replace(' ','%20')
                    if ($parts.Count -gt 1) { $relative += '#'+$parts[1] }
                    return "]($relative)"
                }
            }
            return $match.Value
        })
    }
    foreach ($record in $records) {
        $oldAbsolute = (Join-Path $root $record.origen).Replace('\','/')
        $newAbsolute = (Join-Path $root $record.destino).Replace('\','/')
        $updated = $updated.Replace($oldAbsolute,$newAbsolute)
        $updated = $updated.Replace('"'+$record.origen+'"','"'+$record.destino+'"')
        $updated = $updated.Replace("'"+$record.origen+"'","'"+$record.destino+"'")
    }
    if ($updated -ne $text) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
$blocked = @()
foreach ($record in $records) {
    $source = Join-Path $root $record.origen
    if (Test-Path -LiteralPath $source) {
        $sourceHash = $null
        try { $sourceHash = (Get-FileHash -LiteralPath $source -ErrorAction Stop).Hash.ToLowerInvariant() } catch { $blocked += $record.origen }
        if ($null -ne $sourceHash) {
            if ($sourceHash -ne $record.sha256_original) { throw 'Original cambio durante la operacion; no retirar' }
            try { Remove-Item -LiteralPath $source } catch { $blocked += $record.origen }
        }
    }
    $record.original_raiz_pendiente_retirada = Test-Path -LiteralPath $source
}
[IO.File]::WriteAllText($registryPath,($records | ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
Write-Output ('17 Word y respaldos verificados; bloqueados en raiz: '+($blocked -join ', '))