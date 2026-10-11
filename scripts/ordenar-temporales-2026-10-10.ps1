param([switch]$PlanOnly)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$audit = Join-Path $root 'retroalimentacion-editorial/aulatex/limpieza-temporales-2026-10-10'
if (Test-Path (Join-Path $audit 'manifiesto.json')) { throw 'La limpieza ya tiene un manifiesto; no repetir' }
New-Item -ItemType Directory -Path $audit -Force | Out-Null
$folders = @('tmp','.tmp-itesca-20260928','.tmp-seminario')
$files = @($folders | ForEach-Object { Get-ChildItem -LiteralPath (Join-Path $root $_) -Recurse -Force -File })
$plan = 'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/referencias-plan-de-negocios/notas-plan-de-negocios'
$seminario = 'ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/referencias-seminario-i/notas-seminario-i'
$adh = 'UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/referencias-antecedentes-de-los-derechos-humanos/notas-antecedentes-de-los-derechos-humanos'
$calculo = 'UANL/ingeniero-agronomo/calculo-integral/referencias-calculo-integral/notas-calculo-integral'
$biology = 'UANL/ingeniero-agronomo/biologia-celular/referencias-biologia-celular/notas-biologia-celular'
$uas = 'UAS/licenciatura-en-contaduria-uas/derecho-mercantil/referencias-derecho-mercantil/notas-derecho-mercantil'
$ucnl = 'UCNL/licenciatura-en-administracion/macroeconomia-lad/referencias-macroeconomia/notas-macroeconomia'
$outside = @{}
foreach ($area in @('ITESCA','UnADM','UANL','UAS','UCNL')) {
    Get-ChildItem -LiteralPath (Join-Path $root $area) -Recurse -File | ForEach-Object {
        $length = $_.Length.ToString()
        if (-not $outside.ContainsKey($length)) { $outside[$length] = [Collections.Generic.List[string]]::new() }
        $outside[$length].Add($_.FullName)
    }
}
$hashes = @{}
function Hash-File([string]$path) {
    if (-not $hashes.ContainsKey($path)) { $hashes[$path] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
    $hashes[$path]
}
$dependencies = @{}
$code = @(Get-ChildItem -LiteralPath (Join-Path $root 'scripts') -Recurse -File -Include '*.py','*.ps1','*.md')
$code += @($folders | ForEach-Object {Get-ChildItem -LiteralPath (Join-Path $root $_) -Recurse -File -Include '*.py','*.ps1'})
foreach ($source in $code) { $dependencies[$source.FullName] = [string](Get-Content -LiteralPath $source.FullName -Raw) }
$records = [Collections.Generic.List[object]]::new()
foreach ($file in $files) {
    $relative = $file.FullName.Substring($root.Length+1).Replace('\','/')
    $hash = Hash-File $file.FullName
    $action = 'conservar'
    $reason = 'Atribucion o dependencia sin resolver'
    $destination = $null
    $base = $null
    $dependent = @($dependencies.GetEnumerator() | Where-Object { $_.Key -ne $file.FullName -and $null -ne $_.Value -and $_.Value.Contains($file.Name) }).Count -gt 0
    if ($relative -match '/__pycache__/|\.pyc$' -or $file.Extension -in @('.aux','.fdb_latexmk','.fls','.out')) {
        $action = 'eliminar'; $reason = 'Cache o auxiliar regenerable'
    } else {
        foreach ($candidate in @($outside[$file.Length.ToString()])) {
            if ($dependent -or $file.Extension -in @('.py','.ps1')) { break }
            if ($candidate -and (Hash-File $candidate) -eq $hash) {
                $action='eliminar'; $reason='Duplicado SHA256 verificado'
                $destination=$candidate.Substring($root.Length+1).Replace('\','/'); break
            }
        }
    }
    if ($action -eq 'conservar') {
        if ($relative -like '.tmp-seminario/*') { $base=$seminario }
        elseif ($relative -like '.tmp-itesca-20260928/*') {
            if ($relative -match '/2910-|/3\.3-|/tarea10/') { $base=$seminario } else { $base=$plan }
        }
        elseif ($relative -match '^tmp/(adh-|foro4|.*-adh\.ps1|unadm-resena-audio/)') { $base=$adh }
        elseif ($relative -match '^tmp/(pdfs/calculo-actividad-2/)') { $base=$calculo }
        elseif ($relative -match '^tmp/biologia_revision/') { $base=$biology }
        elseif ($relative -match '^tmp/(uas-foro-S3/|uas-revision-2026-10-09/)') { $base=$uas }
        elseif ($relative -match '^tmp/ucnl-documental/') { $base=$ucnl }
        elseif ($relative -match '^tmp/(.*plan-negocios.*|portada-comun-|portada-t(6|12|14)|word-(sondeo|t12)|t12-|t13-|latexmk-comparison-)') { $base=$plan }
        elseif ($relative -match '^tmp/(.*seminario.*|.*vtaxi.*|confirmado-T|semestre-|uniformizacion-|t[1-9]-|t11-|oecd-lectura|justificacion\.pdf)') { $base=$seminario }
        if ($file.Extension -in @('.py','.ps1') -and $relative -match '^\.tmp-|^tmp/(ucnl_|itesca_|probe_|debug_)') {
            $reason='Controlador o paquete de scripts con dependencias locales; no ejecutar ni migrar sin adaptar'
        } elseif ($dependent) {
            $reason='Nombre referenciado desde scripts; conservar hasta adaptar dependencia'
        } elseif ($base) {
            $action='reubicar'; $reason='Material historico atribuible; no sustituye entregable ni fuente bibliografica'
            $destination=($base+'/materiales-generales/historico-temporales-2026-10-10/'+$relative)
        }
    }
    $records.Add([ordered]@{origen=$relative;accion=$action;motivo=$reason;destino=$destination;bytes=$file.Length;sha256=$hash})
}
[IO.File]::WriteAllText((Join-Path $audit 'plan.json'),($records | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
if ($PlanOnly) { $records | Group-Object accion | Select-Object Name,Count | Format-Table; return }
foreach ($record in $records) {
    $source=Join-Path $root $record.origen
    if ((Hash-File $source) -ne $record.sha256) { throw 'Origen modificado durante limpieza' }
    if ($record.accion -eq 'reubicar') {
        $target=Join-Path $root $record.destino
        if (Test-Path -LiteralPath $target) { throw "Destino existente: $($record.destino)" }
        New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
        Move-Item -LiteralPath $source -Destination $target
        if ((Get-FileHash -LiteralPath $target).Hash.ToLowerInvariant() -ne $record.sha256) { throw 'Hash de destino distinto' }
    } elseif ($record.accion -eq 'eliminar') {
        if ($record.destino -and (Get-FileHash -LiteralPath (Join-Path $root $record.destino)).Hash.ToLowerInvariant() -ne $record.sha256) { throw 'Duplicado no coincide' }
        Remove-Item -LiteralPath $source -Force
    }
}
foreach ($folder in $folders) {
    Get-ChildItem -LiteralPath (Join-Path $root $folder) -Recurse -Force -Directory | Sort-Object { $_.FullName.Length } -Descending | ForEach-Object {
        if (-not (Get-ChildItem -LiteralPath $_.FullName -Force)) { Remove-Item -LiteralPath $_.FullName -Force }
    }
}
[IO.File]::WriteAllText((Join-Path $audit 'manifiesto.json'),($records | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
$records | Group-Object accion | Select-Object Name,Count | Format-Table