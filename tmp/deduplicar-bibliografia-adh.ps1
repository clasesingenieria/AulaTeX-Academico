$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
$refs = Join-Path $root 'referencias-antecedentes-de-los-derechos-humanos'
$library = Join-Path $refs 'libros-antecedentes-de-los-derechos-humanos'
$records = @(Get-ChildItem -LiteralPath $library -File | Where-Object Extension -in @('.pdf','.txt') | ForEach-Object {
    [pscustomobject]@{file=$_;hash=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant()}
})
$groups = $records | Group-Object hash
$mapping = @{}
$changes = @()
$reserved = @{}
foreach ($group in $groups) {
    $ordered = @($group.Group | Sort-Object @{Expression={$_.file.Name -match ' - captura \d+'}},@{Expression={$_.file.Name}})
    $keeper = $ordered[0].file
    $baseName = $keeper.BaseName -replace ' - captura \d+( - variante)?$',''
    $name = $baseName + $keeper.Extension
    $target = Join-Path $library $name
    if ($reserved.ContainsKey($target) -or ((Test-Path -LiteralPath $target) -and -not ($ordered.file.FullName -contains $target))) {
        $name = $baseName + ' - version ' + $group.Name.Substring(0,8) + $keeper.Extension
        $target = Join-Path $library $name
    }
    if ($reserved.ContainsKey($target)) { throw 'Colision de destinos' }
    $reserved[$target] = $true
    foreach ($record in $ordered) {
        $mapping[$record.file.FullName] = $target
        if ($record.file.FullName -ne $target) {
            $changes += [pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$record.file.FullName).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$target).Replace('\','/');sha256=$group.Name;accion=if($record.file.FullName -eq $keeper.FullName){'renombrado'}else{'duplicado exacto consolidado'}}
        }
    }
    foreach ($record in $ordered | Select-Object -Skip 1) {
        if ((Get-FileHash -LiteralPath $record.file.FullName).Hash.ToLowerInvariant() -ne $group.Name) { throw 'Contenido cambiado' }
        Remove-Item -LiteralPath $record.file.FullName
    }
    if ($keeper.FullName -ne $target) { Move-Item -LiteralPath $keeper.FullName -Destination $target }
    if ((Get-FileHash -LiteralPath $target).Hash.ToLowerInvariant() -ne $group.Name) { throw 'Integridad incorrecta' }
}
function Update-Paths($node, $directory) {
    if ($node -is [array]) { foreach ($child in $node) { Update-Paths $child $directory }; return }
    if ($node -isnot [pscustomobject]) { return }
    foreach ($property in $node.PSObject.Properties) {
        if ($property.Value -is [string] -and $property.Name -in @('file','archivo','archivo_local','destino')) {
            $bases = @($directory)
            if ($property.Name -eq 'destino') { $bases = @($root,$directory) }
            foreach ($baseDirectory in $bases) {
                $absolute = [IO.Path]::GetFullPath((Join-Path $baseDirectory $property.Value))
                if ($mapping.ContainsKey($absolute)) {
                    $property.Value = [IO.Path]::GetRelativePath($baseDirectory,$mapping[$absolute]).Replace('\','/')
                    break
                }
            }
        } else { Update-Paths $property.Value $directory }
    }
}
foreach ($file in Get-ChildItem -LiteralPath $refs -Recurse -Filter '*.json' -File | Where-Object { $_.Name -like 'inventario*' -or $_.Name -in @('organizacion-materiales.json','renombrado-bibliografia.json') }) {
    $data = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    Update-Paths $data $file.DirectoryName
    [IO.File]::WriteAllText($file.FullName,($data | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
}
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.tex','.bib')) {
    $text = [IO.File]::ReadAllText($file.FullName)
    $updated = $text
    foreach ($source in $mapping.Keys) {
        $old = [IO.Path]::GetRelativePath($file.DirectoryName,$source).Replace('\','/')
        $new = [IO.Path]::GetRelativePath($file.DirectoryName,$mapping[$source]).Replace('\','/')
        $updated = $updated.Replace("]($old)","]($new)").Replace("]($($old.Replace(' ','%20')))","]($($new.Replace(' ','%20')))")
    }
    if ($text -ne $updated) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
$result = [pscustomobject]@{fecha='2026-10-10';criterio='Solo SHA256 identico; conservar contenidos diferentes';archivos_antes=$records.Count;archivos_despues=@($groups).Count;duplicados_eliminados=$records.Count-@($groups).Count;movimientos=$changes}
[IO.File]::WriteAllText((Join-Path $refs 'deduplicacion-bibliografia.json'),($result | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
Write-Output ($result | Select-Object archivos_antes,archivos_despues,duplicados_eliminados | ConvertTo-Json)