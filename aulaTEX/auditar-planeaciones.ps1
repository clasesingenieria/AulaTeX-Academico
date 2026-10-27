[CmdletBinding()]
param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [string]$Output = ''
)

$ErrorActionPreference = 'Stop'
$rootPath = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\', '/')
$institutions = @('IIIEPE', 'ITESCA', 'tecnmNL', 'UAdeC', 'UANL', 'UAS', 'UCNL', 'UnADM')
$records = [System.Collections.Generic.List[object]]::new()
$summaries = [System.Collections.Generic.List[object]]::new()

function Get-RelativePath([string]$FullPath) {
    return $FullPath.Substring($rootPath.Length + 1).Replace('\', '/')
}

foreach ($institution in $institutions) {
    $institutionPath = Join-Path $rootPath $institution
    if (-not (Test-Path -LiteralPath $institutionPath -PathType Container)) { continue }
    $allFiles = @(Get-ChildItem -LiteralPath $institutionPath -Recurse -File)
    $planningDirs = @(Get-ChildItem -LiteralPath $institutionPath -Recurse -Directory | Where-Object { $_.Name -like 'planeaciones*' })
    $planningFiles = @($allFiles | Where-Object { (Get-RelativePath $_.DirectoryName) -match '(^|/)planeaciones[^/]*(/|$)' })
    $outsideFiles = @($allFiles | Where-Object {
        $_.Name -match '^(plan\.md|programa-analitico.*\.md|planeacion.*\.(md|json|txt|pdf))$' -and
        (Get-RelativePath $_.DirectoryName) -notmatch '(^|/)planeaciones[^/]*(/|$)'
    })
    $summaries.Add([pscustomobject]@{
        institution = $institution
        planning_directories = $planningDirs.Count
        planning_files = $planningFiles.Count
        outside_candidates = $outsideFiles.Count
        formats = @($planningFiles | Group-Object Extension | Sort-Object Name | ForEach-Object {
            [pscustomobject]@{ extension = $_.Name; count = $_.Count }
        })
    })

    foreach ($file in @($planningFiles) + @($outsideFiles)) {
        $parent = $file.Directory
        $planningDir = $null
        while ($null -ne $parent -and $parent.FullName.Length -gt $institutionPath.Length) {
            if ($parent.Name -like 'planeaciones*') { $planningDir = $parent; break }
            $parent = $parent.Parent
        }
        $subject = $null
        $locationState = 'candidato_externo'
        $expectedDirectory = $null
        if ($null -ne $planningDir) {
            if ($planningDir.Name -ne 'planeaciones-generadas') {
                $subject = $planningDir.Parent
            } else {
                $ancestor = $planningDir.Parent
                while ($null -ne $ancestor -and $ancestor.FullName.Length -gt $institutionPath.Length) {
                    $siblings = @(Get-ChildItem -LiteralPath $ancestor.FullName -Directory | Where-Object {
                        $_.Name -like 'planeaciones-*' -and $_.Name -ne 'planeaciones-generadas'
                    })
                    if ($siblings.Count -gt 0) { $subject = $ancestor; break }
                    $ancestor = $ancestor.Parent
                }
            }
            if ($null -eq $subject) {
                $locationState = 'materia_no_resuelta'
            } else {
                $slug = $subject.Name -replace '-(lde|lad|mga|isc|imtc)$', ''
                $expectedDirectory = (Get-RelativePath $subject.FullName) + '/planeaciones-' + $slug
                if ($planningDir.Name -eq 'planeaciones-generadas') {
                    $locationState = 'derivado_fuera_de_ruta_canonica'
                } elseif ((Get-RelativePath $planningDir.FullName) -eq $expectedDirectory) {
                    $locationState = 'ubicacion_coherente'
                } else {
                    $locationState = 'alias_o_discrepancia_de_ruta'
                }
            }
        }

        $kind = 'auxiliar'
        $declaredIds = @()
        $schemaVersion = $null
        $jsonState = 'no_aplica'
        $sourceCount = $null
        if ($file.Extension -in @('.pdf', '.docx', '.html', '.png', '.ppsx')) { $kind = 'fuente_o_recurso' }
        if ($file.BaseName -match '^(planeacion|planificaci[oó]n|consigna|programa-analitico)' -or $file.Name -eq 'plan.md') { $kind = 'candidato_planeacion' }
        if ($file.Extension -eq '.json') {
            try {
                $data = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
                $jsonState = 'sintaxis_valida'
                $schemaVersion = $data.schema_version
                $activities = @()
                if ($null -ne $data.activity) { $activities += $data.activity }
                if ($null -ne $data.activities) { $activities += @($data.activities) }
                $declaredIds = @($activities | Where-Object { $null -ne $_.id } | ForEach-Object { [string]$_.id })
                if ($activities.Count -gt 0) { $kind = 'modelo_con_actividades' }
                $sourceCount = @($data.sources | Where-Object { $null -ne $_ }).Count
                foreach ($activity in $activities) {
                    $sourceCount += @($activity.sources | Where-Object { $null -ne $_ }).Count
                }
            } catch {
                $jsonState = 'error_lectura_o_sintaxis'
            }
        }
        $records.Add([pscustomobject]@{
            institution = $institution
            file = Get-RelativePath $file.FullName
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            extension = $file.Extension
            artifact_kind = $kind
            observed_subject_directory = $(if ($null -ne $subject) { Get-RelativePath $subject.FullName } else { $null })
            observed_planning_directory = $(if ($null -ne $planningDir) { Get-RelativePath $planningDir.FullName } else { $null })
            expected_planning_directory = $expectedDirectory
            location_state = $locationState
            declared_activity_ids = $declaredIds
            declared_schema_version = $schemaVersion
            json_state = $jsonState
            declared_source_count = $sourceCount
            binding_state = 'pendiente_cotejo'
        })
    }
}

$duplicates = @($records | Group-Object sha256 | Where-Object { $_.Count -gt 1 } | ForEach-Object {
    [pscustomobject]@{ sha256 = $_.Name; files = @($_.Group.file) }
})
$result = [pscustomobject]@{
    audit_version = '1.0'
    captured_at = (Get-Date).ToString('o')
    scope = 'Inventario local; no verifica identidad docente, vigencia de plataforma ni contenido completo.'
    method = 'Archivos unicos bajo planeaciones* y candidatos externos por nombre; materia inferida por ubicacion, no por titulo ni semana.'
    summaries = $summaries.ToArray()
    records = @($records | Sort-Object institution, file)
    identical_content_groups = $duplicates
}
$json = $result | ConvertTo-Json -Depth 12
if ([string]::IsNullOrWhiteSpace($Output)) {
    $json
} else {
    $outputPath = [System.IO.Path]::GetFullPath($Output)
    $outputParent = Split-Path -Parent $outputPath
    if (-not (Test-Path -LiteralPath $outputParent)) { [void](New-Item -ItemType Directory -Path $outputParent -Force) }
    if (Test-Path -LiteralPath $outputPath) { throw 'La salida ya existe; elegir otra ruta para conservar la auditoria previa.' }
    [System.IO.File]::WriteAllText($outputPath, $json, [System.Text.UTF8Encoding]::new($false))
    [pscustomobject]@{ output = $outputPath; records = $records.Count; planning_files = ($summaries | Measure-Object planning_files -Sum).Sum }
}