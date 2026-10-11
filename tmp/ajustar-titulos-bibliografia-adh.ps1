$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
$refs = Join-Path $root 'referencias-antecedentes-de-los-derechos-humanos'
$library = Join-Path $refs 'libros-antecedentes-de-los-derechos-humanos'
$changes = @{
 'Derechos humanos, teorias y doctrina - Luis Manuel Marcano Salazar'='Derechos humanos, teorias y doctrinas - Luis Manuel Marcano Salazar'
 'Como se hicieron los derechos humanos - Ricardo Rabinovich Berkman'='Como se hicieron los derechos humanos - Volumen I - Ricardo Rabinovich Berkman'
 'El neoconstitucionalismo y la constitucionalizacion'='El neoconstitucionalismo y la constitucionalizacion del derecho - Luis Roberto Barroso'
 'Historia minima del neoliberalismo'='Historia minima del neoliberalismo - Fernando Escalante Gonzalbo'
}
$mapping = @{}
foreach ($file in Get-ChildItem -LiteralPath $library -File) {
    foreach ($old in $changes.Keys) {
        if ($file.BaseName -eq $old -or $file.BaseName.StartsWith("$old - captura ")) {
            $name = $changes[$old] + $file.BaseName.Substring($old.Length) + $file.Extension
            $target = Join-Path $library $name
            if (Test-Path -LiteralPath $target) { throw 'Colision' }
            $mapping[$file.Name] = $name
            Move-Item -LiteralPath $file.FullName -Destination $target
            break
        }
    }
}
function Update-Names($node) {
    if ($node -is [array]) { foreach ($child in $node) { Update-Names $child }; return }
    if ($node -isnot [pscustomobject]) { return }
    foreach ($property in $node.PSObject.Properties) {
        if ($property.Value -is [string] -and $property.Name -in @('file','archivo','archivo_local','destino')) {
            $leaf = Split-Path $property.Value -Leaf
            if ($mapping.ContainsKey($leaf)) { $property.Value=$property.Value.Substring(0,$property.Value.Length-$leaf.Length)+$mapping[$leaf] }
        } else { Update-Names $property.Value }
    }
}
foreach ($file in Get-ChildItem -LiteralPath $refs -Recurse -Filter '*.json' | Where-Object { $_.Name -like 'inventario*' -or $_.Name -in @('organizacion-materiales.json','renombrado-bibliografia.json') }) {
    $data = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    Update-Names $data
    [IO.File]::WriteAllText($file.FullName,($data | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
}
Write-Output "$($mapping.Count) nombres precisados mediante portada."