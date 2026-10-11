$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
$refs = 'referencias-antecedentes-de-los-derechos-humanos'
$notes = "$refs/notas-antecedentes-de-los-derechos-humanos"
$plans = 'planeaciones-antecedentes-de-los-derechos-humanos'
$moves = [System.Collections.Generic.List[object]]::new()
function Register-Move($source, $target) {
    $fullSource = Join-Path $root $source
    $fullTarget = Join-Path $root $target
    if (-not (Test-Path -LiteralPath $fullSource -PathType Leaf)) { throw "Origen ausente: $source" }
    if (Test-Path -LiteralPath $fullTarget) { throw "Destino existente: $target" }
    $moves.Add([pscustomobject]@{origen=$source;destino=$target;sha256=(Get-FileHash -LiteralPath $fullSource).Hash.ToLowerInvariant()})
}
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $root $refs) -File) {
    if ($file.Name -like 'Planificaci-n-de-Actividades*') {
        Register-Move "$refs/$($file.Name)" "$plans/originales-aula/$($file.Name)"
    } elseif ($file.Name -match 'Diagrama-20de-20Autoevaluaci') {
        Register-Move "$refs/$($file.Name)" "$notes/autoevaluacion-sin-numero-interno/$($file.Name)"
    } elseif ($file.Name -match '^(C-digo-de--tica|Lineamientos-|Reglamento-Universitario)') {
        Register-Move "$refs/$($file.Name)" "$notes/materiales-generales/$($file.Name)"
    }
}
Register-Move "$refs/modulo-3.txt" "$notes/actividad-2-foro-diagnostico/modulo-3.txt"
Register-Move "$refs/modulo-4.txt" "$notes/actividad-oficial-5-cuadro-comparativo/modulo-4.txt"
foreach ($name in @('revision-cuestionario-S1.md')) {
    Register-Move "$refs/$name" "$notes/actividad-1-cuestionario-diagnostico/$name"
}
$audit = "$refs/auditoria-semana-2-2026-10-09"
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $root $audit) -File) {
    if ($file.Name -match '^material-docente-|^Tema 11\.|^transcripcion-video\.json$') {
        Register-Move "$audit/$($file.Name)" "$notes/actividad-3-resena-critica-de-video/$($file.Name)"
    } elseif ($file.Name -like 'Diagrama de Autoevaluaci*') {
        Register-Move "$audit/$($file.Name)" "$notes/autoevaluacion-sin-numero-interno/$($file.Name)"
    }
}
foreach ($move in $moves) {
    $destination = Join-Path $root $move.destino
    New-Item -ItemType Directory -Path (Split-Path $destination) -Force | Out-Null
    Move-Item -LiteralPath (Join-Path $root $move.origen) -Destination $destination
    if ((Get-FileHash -LiteralPath $destination).Hash.ToLowerInvariant() -ne $move.sha256) { throw 'Hash distinto tras mover' }
}
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.Extension -in @('.md','.tex','.bib') }) {
    $content = [IO.File]::ReadAllText($file.FullName)
    $updated = $content
    $directory = [IO.Path]::GetDirectoryName($file.FullName)
    foreach ($move in $moves) {
        $old = [IO.Path]::GetRelativePath($directory,(Join-Path $root $move.origen)).Replace('\','/')
        $new = [IO.Path]::GetRelativePath($directory,(Join-Path $root $move.destino)).Replace('\','/')
        $updated = $updated.Replace("]($old)","]($new)")
    }
    if ($updated -ne $content) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
function Update-Paths($node, $baseDirectory) {
    if ($null -eq $node) { return }
    if ($node -is [array]) { foreach ($child in $node) { Update-Paths $child $baseDirectory }; return }
    if ($node -isnot [pscustomobject]) { return }
    foreach ($property in $node.PSObject.Properties) {
        if ($property.Name -in @('file','archivo','archivo_local') -and $property.Value -is [string]) {
            foreach ($move in $moves) {
                $old = [IO.Path]::GetRelativePath($baseDirectory,(Join-Path $root $move.origen)).Replace('\','/')
                if ($property.Value -eq $old) {
                    $property.Value = [IO.Path]::GetRelativePath($baseDirectory,(Join-Path $root $move.destino)).Replace('\','/')
                    break
                }
            }
        } else { Update-Paths $property.Value $baseDirectory }
    }
}
foreach ($relative in @("$refs/inventario-aula.json","$audit/plataforma.json")) {
    $path = Join-Path $root $relative
    $data = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    Update-Paths $data (Split-Path $path)
    [IO.File]::WriteAllText($path,($data | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
}
$manifest = [pscustomobject]@{fecha='2026-10-10';criterio='Bibliografia en referencias, materiales en notas por actividad, planeaciones aparte';movimientos=$moves.ToArray()}
[IO.File]::WriteAllText((Join-Path $root "$refs/organizacion-materiales.json"),($manifest | ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
Write-Output "$($moves.Count) archivos movidos y cotejados por SHA256; enlaces e inventarios actualizados."