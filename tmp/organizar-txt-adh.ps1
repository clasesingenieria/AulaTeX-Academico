$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
$refs = Join-Path $root 'referencias-antecedentes-de-los-derechos-humanos'
$notes = 'notas-antecedentes-de-los-derechos-humanos'
$manifestPath = Join-Path $refs 'organizacion-materiales.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$moves = @()
foreach ($file in Get-ChildItem -LiteralPath $refs -File | Where-Object { $_.Name -like 'modulo-*.txt' -or $_.Name -eq 'curso-aula.txt' }) {
    $destination = 'materiales-generales/capturas-aula'
    if ($file.Name -match '^modulo-(2|5|8|11)\.txt$') { $destination = 'autoevaluacion-sin-numero-interno' }
    if ($file.Name -match '^modulo-(6|7|20)\.txt$') { $destination = 'actividad-2-foro-diagnostico' }
    $relative = "$notes/$destination/$($file.Name)"
    $target = Join-Path $refs $relative
    if (Test-Path -LiteralPath $target) { throw "Destino existente: $target" }
    $moves += [pscustomobject]@{origen="referencias-antecedentes-de-los-derechos-humanos/$($file.Name)";destino="referencias-antecedentes-de-los-derechos-humanos/$relative";sha256=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
}
foreach ($move in $moves) {
    $target = Join-Path $root $move.destino
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    Move-Item -LiteralPath (Join-Path $root $move.origen) -Destination $target
    if ((Get-FileHash -LiteralPath $target).Hash.ToLowerInvariant() -ne $move.sha256) { throw 'Hash incorrecto' }
}
foreach ($file in Get-ChildItem -LiteralPath $root -Filter '*.md' -Recurse -File) {
    $content = [IO.File]::ReadAllText($file.FullName)
    $updated = $content
    foreach ($move in $moves) {
        $old = [IO.Path]::GetRelativePath($file.DirectoryName,(Join-Path $root $move.origen)).Replace('\','/')
        $new = [IO.Path]::GetRelativePath($file.DirectoryName,(Join-Path $root $move.destino)).Replace('\','/')
        $updated = $updated.Replace("]($old)","]($new)")
    }
    if ($updated -ne $content) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
$inventoryPath = Join-Path $refs 'inventario-aula.json'
$inventory = Get-Content -LiteralPath $inventoryPath -Raw | ConvertFrom-Json
foreach ($resource in $inventory.resources) {
    foreach ($move in $moves) {
        if ($resource.file -eq (Split-Path $move.origen -Leaf)) {
            $resource.file = [IO.Path]::GetRelativePath($refs,(Join-Path $root $move.destino)).Replace('\','/')
        }
    }
}
$manifest.movimientos = @($manifest.movimientos) + $moves
[IO.File]::WriteAllText($manifestPath,($manifest | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($inventoryPath,($inventory | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output "$($moves.Count) TXT trasladados y verificados; inventario actualizado."