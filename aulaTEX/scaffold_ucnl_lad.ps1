Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$degreeRoot = Join-Path $repoRoot 'UCNL\licenciatura-en-administracion'
$templateRoot = Join-Path $degreeRoot 'administracion-i-lad'

if (-not (Test-Path $templateRoot)) {
    throw "No se encontro la carpeta plantilla base: $templateRoot"
}

$templateReport = Get-Content -Raw -Path (Join-Path $templateRoot 'reporte-administracion-I.tex')
$templateActivity = Get-Content -Raw -Path (Join-Path $templateRoot 'reporte-administracion-I-Actividad-1.tex')
$templatePresentation = Get-Content -Raw -Path (Join-Path $templateRoot 'presentacion-administracion.tex')
$templateBib = Get-Content -Raw -Path (Join-Path $templateRoot 'administracion-I.bib')

$courses = @(
    [pscustomobject]@{ Tetramestre = 1; Name = 'Administracion I'; Folder = 'administracion-i-lad'; BibStem = 'administracion-I'; ReportStem = 'administracion-I'; PresentationStem = 'administracion'; Code = 'ADM-I' },
    [pscustomobject]@{ Tetramestre = 1; Name = 'Contabilidad I'; Folder = 'contabilidad-i-lad'; BibStem = 'contabilidad-I'; ReportStem = 'contabilidad-I'; PresentationStem = 'contabilidad'; Code = 'CON-I' },
    [pscustomobject]@{ Tetramestre = 1; Name = 'Microeconomia'; Folder = 'microeconomia-lad'; BibStem = 'microeconomia'; ReportStem = 'microeconomia'; PresentationStem = 'microeconomia'; Code = 'MIC' },
    [pscustomobject]@{ Tetramestre = 1; Name = 'Desarrollo sustentable'; Folder = 'desarrollo-sustentable-lad'; BibStem = 'desarrollo-sustentable'; ReportStem = 'desarrollo-sustentable'; PresentationStem = 'desarrollo-sustentable'; Code = 'DSU' },
    [pscustomobject]@{ Tetramestre = 1; Name = 'Matematicas I'; Folder = 'matematicas-i-lad'; BibStem = 'matematicas-I'; ReportStem = 'matematicas-I'; PresentationStem = 'matematicas'; Code = 'MAT-I' },
    [pscustomobject]@{ Tetramestre = 1; Name = 'Ingles I'; Folder = 'ingles-i-lad'; BibStem = 'ingles-I'; ReportStem = 'ingles-I'; PresentationStem = 'ingles'; Code = 'ING-I' },

    [pscustomobject]@{ Tetramestre = 2; Name = 'Administracion II'; Folder = 'administracion-ii-lad'; BibStem = 'administracion-II'; ReportStem = 'administracion-II'; PresentationStem = 'administracion'; Code = 'ADM-II' },
    [pscustomobject]@{ Tetramestre = 2; Name = 'Contabilidad II'; Folder = 'contabilidad-ii-lad'; BibStem = 'contabilidad-II'; ReportStem = 'contabilidad-II'; PresentationStem = 'contabilidad'; Code = 'CON-II' },
    [pscustomobject]@{ Tetramestre = 2; Name = 'Derecho constitucional'; Folder = 'derecho-constitucional-lad'; BibStem = 'derecho-constitucional'; ReportStem = 'derecho-constitucional'; PresentationStem = 'derecho-constitucional'; Code = 'DER-CON' },
    [pscustomobject]@{ Tetramestre = 2; Name = 'Macroeconomia'; Folder = 'macroeconomia-lad'; BibStem = 'macroeconomia'; ReportStem = 'macroeconomia'; PresentationStem = 'macroeconomia'; Code = 'MAC' },
    [pscustomobject]@{ Tetramestre = 2; Name = 'Matematicas II'; Folder = 'matematicas-ii-lad'; BibStem = 'matematicas-II'; ReportStem = 'matematicas-II'; PresentationStem = 'matematicas'; Code = 'MAT-II' },
    [pscustomobject]@{ Tetramestre = 2; Name = 'Ingles II'; Folder = 'ingles-ii-lad'; BibStem = 'ingles-II'; ReportStem = 'ingles-II'; PresentationStem = 'ingles'; Code = 'ING-II' },

    [pscustomobject]@{ Tetramestre = 3; Name = 'Contabilidad III'; Folder = 'contabilidad-iii-lad'; BibStem = 'contabilidad-III'; ReportStem = 'contabilidad-III'; PresentationStem = 'contabilidad'; Code = 'CON-III' },
    [pscustomobject]@{ Tetramestre = 3; Name = 'Derecho civil'; Folder = 'derecho-civil-lad'; BibStem = 'derecho-civil'; ReportStem = 'derecho-civil'; PresentationStem = 'derecho-civil'; Code = 'DER-CIV' },
    [pscustomobject]@{ Tetramestre = 3; Name = 'Ingles III'; Folder = 'ingles-iii-lad'; BibStem = 'ingles-III'; ReportStem = 'ingles-III'; PresentationStem = 'ingles'; Code = 'ING-III' },
    [pscustomobject]@{ Tetramestre = 3; Name = 'Informatica'; Folder = 'informatica-lad'; BibStem = 'informatica'; ReportStem = 'informatica'; PresentationStem = 'informatica'; Code = 'INF' },
    [pscustomobject]@{ Tetramestre = 3; Name = 'Etica y responsabilidad social'; Folder = 'etica-y-responsabilidad-social-lad'; BibStem = 'etica-y-responsabilidad-social'; ReportStem = 'etica-y-responsabilidad-social'; PresentationStem = 'etica-y-responsabilidad-social'; Code = 'ETI-RSO' },
    [pscustomobject]@{ Tetramestre = 3; Name = 'Derechos humanos'; Folder = 'derechos-humanos-lad'; BibStem = 'derechos-humanos'; ReportStem = 'derechos-humanos'; PresentationStem = 'derechos-humanos'; Code = 'DER-HUM' },

    [pscustomobject]@{ Tetramestre = 4; Name = 'Habilidades directivas'; Folder = 'habilidades-directivas-lad'; BibStem = 'habilidades-directivas'; ReportStem = 'habilidades-directivas'; PresentationStem = 'habilidades-directivas'; Code = 'HAB-DIR' },
    [pscustomobject]@{ Tetramestre = 4; Name = 'Costos I'; Folder = 'costos-i-lad'; BibStem = 'costos-I'; ReportStem = 'costos-I'; PresentationStem = 'costos'; Code = 'COS-I' },
    [pscustomobject]@{ Tetramestre = 4; Name = 'Derecho laboral'; Folder = 'derecho-laboral-lad'; BibStem = 'derecho-laboral'; ReportStem = 'derecho-laboral'; PresentationStem = 'derecho-laboral'; Code = 'DER-LAB' },
    [pscustomobject]@{ Tetramestre = 4; Name = 'Administracion de recursos humanos'; Folder = 'administracion-de-recursos-humanos-lad'; BibStem = 'administracion-de-recursos-humanos'; ReportStem = 'administracion-de-recursos-humanos'; PresentationStem = 'administracion-de-recursos-humanos'; Code = 'ADM-RH' },
    [pscustomobject]@{ Tetramestre = 4; Name = 'Finanzas I'; Folder = 'finanzas-i-lad'; BibStem = 'finanzas-I'; ReportStem = 'finanzas-I'; PresentationStem = 'finanzas'; Code = 'FIN-I' },
    [pscustomobject]@{ Tetramestre = 4; Name = 'Administracion de ventas'; Folder = 'administracion-de-ventas-lad'; BibStem = 'administracion-de-ventas'; ReportStem = 'administracion-de-ventas'; PresentationStem = 'administracion-de-ventas'; Code = 'ADM-VEN' },

    [pscustomobject]@{ Tetramestre = 5; Name = 'Diseno organizacional'; Folder = 'diseno-organizacional-lad'; BibStem = 'diseno-organizacional'; ReportStem = 'diseno-organizacional'; PresentationStem = 'diseno-organizacional'; Code = 'DIS-ORG' },
    [pscustomobject]@{ Tetramestre = 5; Name = 'Investigacion de mercados'; Folder = 'investigacion-de-mercados-lad'; BibStem = 'investigacion-de-mercados'; ReportStem = 'investigacion-de-mercados'; PresentationStem = 'investigacion-de-mercados'; Code = 'INV-MER' },
    [pscustomobject]@{ Tetramestre = 5; Name = 'Comercio internacional'; Folder = 'comercio-internacional-lad'; BibStem = 'comercio-internacional'; ReportStem = 'comercio-internacional'; PresentationStem = 'comercio-internacional'; Code = 'COM-INT' },
    [pscustomobject]@{ Tetramestre = 5; Name = 'Administracion de operaciones'; Folder = 'administracion-de-operaciones-lad'; BibStem = 'administracion-de-operaciones'; ReportStem = 'administracion-de-operaciones'; PresentationStem = 'administracion-de-operaciones'; Code = 'ADM-OPE' },
    [pscustomobject]@{ Tetramestre = 5; Name = 'Costos II'; Folder = 'costos-ii-lad'; BibStem = 'costos-II'; ReportStem = 'costos-II'; PresentationStem = 'costos'; Code = 'COS-II' },
    [pscustomobject]@{ Tetramestre = 5; Name = 'Derecho fiscal'; Folder = 'derecho-fiscal-lad'; BibStem = 'derecho-fiscal'; ReportStem = 'derecho-fiscal'; PresentationStem = 'derecho-fiscal'; Code = 'DER-FIS' },

    [pscustomobject]@{ Tetramestre = 6; Name = 'Derecho mercantil'; Folder = 'derecho-mercantil-lad'; BibStem = 'derecho-mercantil'; ReportStem = 'derecho-mercantil'; PresentationStem = 'derecho-mercantil'; Code = 'DER-MER' },
    [pscustomobject]@{ Tetramestre = 6; Name = 'Estadistica descriptiva'; Folder = 'estadistica-descriptiva-lad'; BibStem = 'estadistica-descriptiva'; ReportStem = 'estadistica-descriptiva'; PresentationStem = 'estadistica-descriptiva'; Code = 'EST-DES' },
    [pscustomobject]@{ Tetramestre = 6; Name = 'Presupuestos con enfoque gerencial'; Folder = 'presupuestos-con-enfoque-gerencial-lad'; BibStem = 'presupuestos-con-enfoque-gerencial'; ReportStem = 'presupuestos-con-enfoque-gerencial'; PresentationStem = 'presupuestos-con-enfoque-gerencial'; Code = 'PRE-GER' },
    [pscustomobject]@{ Tetramestre = 6; Name = 'Auditoria administrativa'; Folder = 'auditoria-administrativa-lad'; BibStem = 'auditoria-administrativa'; ReportStem = 'auditoria-administrativa'; PresentationStem = 'auditoria-administrativa'; Code = 'AUD-ADM' },
    [pscustomobject]@{ Tetramestre = 6; Name = 'Evaluacion de proyectos y modelos de negocios'; Folder = 'evaluacion-de-proyectos-y-modelos-de-negocios-lad'; BibStem = 'evaluacion-de-proyectos-y-modelos-de-negocios'; ReportStem = 'evaluacion-de-proyectos-y-modelos-de-negocios'; PresentationStem = 'evaluacion-de-proyectos-y-modelos-de-negocios'; Code = 'EVA-PMN' },
    [pscustomobject]@{ Tetramestre = 6; Name = 'Finanzas II'; Folder = 'finanzas-ii-lad'; BibStem = 'finanzas-II'; ReportStem = 'finanzas-II'; PresentationStem = 'finanzas'; Code = 'FIN-II' },

    [pscustomobject]@{ Tetramestre = 7; Name = 'Planeacion y control de la produccion'; Folder = 'planeacion-y-control-de-la-produccion-lad'; BibStem = 'planeacion-y-control-de-la-produccion'; ReportStem = 'planeacion-y-control-de-la-produccion'; PresentationStem = 'planeacion-y-control-de-la-produccion'; Code = 'PLA-CPR' },
    [pscustomobject]@{ Tetramestre = 7; Name = 'Estrategias de promocion'; Folder = 'estrategias-de-promocion-lad'; BibStem = 'estrategias-de-promocion'; ReportStem = 'estrategias-de-promocion'; PresentationStem = 'estrategias-de-promocion'; Code = 'EST-PRO' },
    [pscustomobject]@{ Tetramestre = 7; Name = 'Dotacion e induccion de recursos humanos'; Folder = 'dotacion-e-induccion-de-recursos-humanos-lad'; BibStem = 'dotacion-e-induccion-de-recursos-humanos'; ReportStem = 'dotacion-e-induccion-de-recursos-humanos'; PresentationStem = 'dotacion-e-induccion-de-recursos-humanos'; Code = 'DOT-IRH' },
    [pscustomobject]@{ Tetramestre = 7; Name = 'Etica en el ejercicio profesional'; Folder = 'etica-en-el-ejercicio-profesional-lad'; BibStem = 'etica-en-el-ejercicio-profesional'; ReportStem = 'etica-en-el-ejercicio-profesional'; PresentationStem = 'etica-en-el-ejercicio-profesional'; Code = 'ETI-EEP' },
    [pscustomobject]@{ Tetramestre = 7; Name = 'Direccion de marketing'; Folder = 'direccion-de-marketing-lad'; BibStem = 'direccion-de-marketing'; ReportStem = 'direccion-de-marketing'; PresentationStem = 'direccion-de-marketing'; Code = 'DIR-MKT' },
    [pscustomobject]@{ Tetramestre = 7; Name = 'Ingenieria economica y financiera'; Folder = 'ingenieria-economica-y-financiera-lad'; BibStem = 'ingenieria-economica-y-financiera'; ReportStem = 'ingenieria-economica-y-financiera'; PresentationStem = 'ingenieria-economica-y-financiera'; Code = 'ING-EFI' },

    [pscustomobject]@{ Tetramestre = 8; Name = 'Planeacion de estados financieros'; Folder = 'planeacion-de-estados-financieros-lad'; BibStem = 'planeacion-de-estados-financieros'; ReportStem = 'planeacion-de-estados-financieros'; PresentationStem = 'planeacion-de-estados-financieros'; Code = 'PLA-EFI' },
    [pscustomobject]@{ Tetramestre = 8; Name = 'Practicas profesionales I'; Folder = 'practicas-profesionales-i-lad'; BibStem = 'practicas-profesionales-I'; ReportStem = 'practicas-profesionales-I'; PresentationStem = 'practicas-profesionales'; Code = 'PRA-PRO-I' },
    [pscustomobject]@{ Tetramestre = 8; Name = 'Software aplicado a la ingenieria financiera'; Folder = 'software-aplicado-a-la-ingenieria-financiera-lad'; BibStem = 'software-aplicado-a-la-ingenieria-financiera'; ReportStem = 'software-aplicado-a-la-ingenieria-financiera'; PresentationStem = 'software-aplicado-a-la-ingenieria-financiera'; Code = 'SOF-IIF' },
    [pscustomobject]@{ Tetramestre = 8; Name = 'Modificacion del comportamiento organizacional'; Folder = 'modificacion-del-comportamiento-organizacional-lad'; BibStem = 'modificacion-del-comportamiento-organizacional'; ReportStem = 'modificacion-del-comportamiento-organizacional'; PresentationStem = 'modificacion-del-comportamiento-organizacional'; Code = 'MOD-ORG' },
    [pscustomobject]@{ Tetramestre = 8; Name = 'Administracion de operaciones'; Folder = 'administracion-de-operaciones-t8-lad'; BibStem = 'administracion-de-operaciones'; ReportStem = 'administracion-de-operaciones'; PresentationStem = 'administracion-de-operaciones'; Code = 'ADM-OPE-T8' },
    [pscustomobject]@{ Tetramestre = 8; Name = 'Administracion de PYMES'; Folder = 'administracion-de-pymes-lad'; BibStem = 'administracion-de-pymes'; ReportStem = 'administracion-de-pymes'; PresentationStem = 'administracion-de-pymes'; Code = 'ADM-PYM' },

    [pscustomobject]@{ Tetramestre = 9; Name = 'Diagnostico y evaluacion empresarial'; Folder = 'diagnostico-y-evaluacion-empresarial-lad'; BibStem = 'diagnostico-y-evaluacion-empresarial'; ReportStem = 'diagnostico-y-evaluacion-empresarial'; PresentationStem = 'diagnostico-y-evaluacion-empresarial'; Code = 'DIA-EMP' },
    [pscustomobject]@{ Tetramestre = 9; Name = 'Seguridad industrial y prevencion de riesgos laborales'; Folder = 'seguridad-industrial-y-prevencion-de-riesgos-laborales-lad'; BibStem = 'seguridad-industrial-y-prevencion-de-riesgos-laborales'; ReportStem = 'seguridad-industrial-y-prevencion-de-riesgos-laborales'; PresentationStem = 'seguridad-industrial-y-prevencion-de-riesgos-laborales'; Code = 'SEG-RLA' },
    [pscustomobject]@{ Tetramestre = 9; Name = 'Planeacion estrategica financiera'; Folder = 'planeacion-estrategica-financiera-lad'; BibStem = 'planeacion-estrategica-financiera'; ReportStem = 'planeacion-estrategica-financiera'; PresentationStem = 'planeacion-estrategica-financiera'; Code = 'PLA-ESF' },
    [pscustomobject]@{ Tetramestre = 9; Name = 'Administracion de emprendedores'; Folder = 'administracion-de-emprendedores-lad'; BibStem = 'administracion-de-emprendedores'; ReportStem = 'administracion-de-emprendedores'; PresentationStem = 'administracion-de-emprendedores'; Code = 'ADM-EMP' },
    [pscustomobject]@{ Tetramestre = 9; Name = 'Administracion de calidad'; Folder = 'administracion-de-calidad-lad'; BibStem = 'administracion-de-calidad'; ReportStem = 'administracion-de-calidad'; PresentationStem = 'administracion-de-calidad'; Code = 'ADM-CAL' },
    [pscustomobject]@{ Tetramestre = 9; Name = 'Practicas profesionales'; Folder = 'practicas-profesionales-lad'; BibStem = 'practicas-profesionales'; ReportStem = 'practicas-profesionales'; PresentationStem = 'practicas-profesionales'; Code = 'PRA-PRO' }
)

function New-FileIfMissing {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    if (Test-Path $Path) {
        return $false
    }

    $directory = Split-Path -Parent $Path
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    Set-Content -Path $Path -Value $Content -Encoding UTF8
    return $true
}

function Convert-Template {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text,
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Course
    )

    $updated = $Text.Replace('Administracion I', $Course.Name)
    $updated = $updated.Replace('administracion-I', $Course.BibStem)
    $updated = $updated.Replace('ADM-I', $Course.Code)
    return $updated
}

$didacticEntry = @"

@misc{unadm100TecnicasDidacticas2023,
    author = {{Universidad Abierta y a Distancia de Mexico}},
    title = {100 Tecnicas didacticas de ensenanza y aprendizaje},
    year = {2023},
    note = {Referencia metodologica para las tecnicas didacticas de apoyo.}
}
"@

$createdDirectories = 0
$createdFiles = 0

foreach ($course in $courses) {
    $courseRoot = Join-Path $degreeRoot $course.Folder
    if (-not (Test-Path $courseRoot)) {
        New-Item -ItemType Directory -Path $courseRoot -Force | Out-Null
        $createdDirectories++
    }

    $reportContent = Convert-Template -Text $templateReport -Course $course
    $activityContent = Convert-Template -Text $templateActivity -Course $course
    $presentationContent = Convert-Template -Text $templatePresentation -Course $course
    $bibContent = Convert-Template -Text $templateBib -Course $course

    if (New-FileIfMissing -Path (Join-Path $courseRoot ("$($course.BibStem).bib")) -Content $bibContent) {
        $createdFiles++
    }
    if (New-FileIfMissing -Path (Join-Path $courseRoot ("reporte-$($course.ReportStem).tex")) -Content $reportContent) {
        $createdFiles++
    }
    if (New-FileIfMissing -Path (Join-Path $courseRoot ("reporte-$($course.ReportStem)-Actividad-1.tex")) -Content $activityContent) {
        $createdFiles++
    }
    if (New-FileIfMissing -Path (Join-Path $courseRoot ("presentacion-$($course.PresentationStem).tex")) -Content $presentationContent) {
        $createdFiles++
    }

    $compileContent = @"
# Compilacion - $($course.Name)

Ejecutar siempre desde la raiz del proyecto:

```powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\$($course.Folder)\reporte-$($course.ReportStem).tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\$($course.Folder)\reporte-$($course.ReportStem)-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\$($course.Folder)\presentacion-$($course.PresentationStem).tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del `.tex`.
- El `\input{template}` no se pasa como argumento. MiKTeX lo busca con `TEXINPUTS`, definido en `.latexmkrc`.
- En reportes, `\input{template}` debe resolver a `aulaTEX/base/Plantilla-Informe/template.tex`.
- El `.bib` no se pasa al script. Los reportes deben declarar `\bibliography{$($course.BibStem)}`.
- BibTeX busca `$($course.BibStem).bib` con `BIBINPUTS`.
- El estilo `natnumurl.bst` se resuelve con `BSTINPUTS`.
- El PDF final queda en esta misma carpeta, junto al `.tex`.
- Los auxiliares quedan en `.build/latex` y `.build/latex/aux-files`.

## Checklist del `.tex`

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en `$($course.BibStem).bib`.
"@

    if (New-FileIfMissing -Path (Join-Path $courseRoot 'COMPILACION.md') -Content $compileContent.TrimStart()) {
        $createdFiles++
    }
}

$reportFiles = Get-ChildItem -Path $degreeRoot -Recurse -File -Filter 'reporte-*.tex'
foreach ($reportFile in $reportFiles) {
    $reportText = Get-Content -Raw -Path $reportFile.FullName
    $normalizedReportText = [regex]::Replace(
        $reportText,
        '(?m)^\\input\{T.*did.*aprendizaje\}\r?\n?',
        '% Referencia opcional desactivada: archivo externo no disponible en este repositorio.' + [Environment]::NewLine
    )

    if ($normalizedReportText -ne $reportText) {
        Set-Content -Path $reportFile.FullName -Value $normalizedReportText -Encoding UTF8
    }
}

$bibFiles = Get-ChildItem -Path $degreeRoot -Recurse -File -Filter '*.bib'
foreach ($bibFile in $bibFiles) {
    $bibText = Get-Content -Raw -Path $bibFile.FullName
    if ($bibText -notmatch 'unadm100TecnicasDidacticas2023') {
        Set-Content -Path $bibFile.FullName -Value ($bibText.TrimEnd() + [Environment]::NewLine + $didacticEntry.TrimStart()) -Encoding UTF8
    }
}

$readmeLines = New-Object System.Collections.Generic.List[string]
$readmeLines.Add('# Licenciatura en Administracion UCNL')
$readmeLines.Add('')
$readmeLines.Add('Sistema de carpetas y plantillas para las materias del plan de estudios 2025 de la Licenciatura en Administracion con acentuacion en Empresas de la Universidad Ciudadana de Nuevo Leon.')
$readmeLines.Add('')
$readmeLines.Add('## Fuente curricular')
$readmeLines.Add('')
$readmeLines.Add('- UCNL/assets-ucnl/oferta-educativa/planes-2025/l-admon-emp/2.png')
$readmeLines.Add('')
$readmeLines.Add('## Estructura por materia')
$readmeLines.Add('')
$readmeLines.Add('Cada carpeta de materia contiene:')
$readmeLines.Add('')
$readmeLines.Add('- Un archivo `.bib` local de la materia.')
$readmeLines.Add('- Un reporte base `reporte-...tex`.')
$readmeLines.Add('- Una actividad inicial `reporte-...-Actividad-1.tex`.')
$readmeLines.Add('- Una presentacion `presentacion-...tex`.')
$readmeLines.Add('- Una guia de compilacion `COMPILACION.md`.')
$readmeLines.Add('')
$readmeLines.Add('## Observaciones')
$readmeLines.Add('')
$readmeLines.Add('- Se conserva `curso-inductivo-lad` como carpeta adicional ya existente fuera del plan mostrado en la lamina curricular.')
$readmeLines.Add('- Para evitar colision de nombres, la materia repetida `Administracion de operaciones` del octavo tetramestre se creo como carpeta `administracion-de-operaciones-t8-lad`.')
$readmeLines.Add('')

foreach ($tetramestre in ($courses | Group-Object Tetramestre | Sort-Object Name)) {
    $readmeLines.Add("## Tetramestre $($tetramestre.Name)")
    $readmeLines.Add('')

    foreach ($course in ($tetramestre.Group | Sort-Object Name)) {
        $readmeLines.Add("- $($course.Name): $($course.Folder)")
    }

    $readmeLines.Add('')
}

Set-Content -Path (Join-Path $degreeRoot 'README.md') -Value ($readmeLines -join [Environment]::NewLine) -Encoding UTF8

Write-Output ("directories_created={0}" -f $createdDirectories)
Write-Output ("files_created={0}" -f $createdFiles)
Write-Output ("courses_total={0}" -f $courses.Count)