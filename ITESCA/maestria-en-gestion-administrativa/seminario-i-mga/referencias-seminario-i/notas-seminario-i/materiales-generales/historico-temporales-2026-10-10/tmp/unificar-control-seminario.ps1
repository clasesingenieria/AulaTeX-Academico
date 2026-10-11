$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
$target = Join-Path $root 'Readme - Seminario I.md'
$sources = @('ESTADO-ENTREGABLES.md','COMPILACION-seminario-i.md','COMPILACION.md')
$text = [IO.File]::ReadAllText($target)
if ($text.Contains('## Compilacion vigente')) { throw 'Seccion ya integrada; revisar antes de repetir' }
$state = [IO.File]::ReadAllText((Join-Path $root 'ESTADO-ENTREGABLES.md'))
$state = [regex]::Replace($state,'\A# Seminario I: estado de documentos\s*','')
$state = [regex]::Replace($state,'(?m)^(#{2,5}) ','$1# ')
$state = $state.Replace('entregas/','Entregas/')
$state = $state.Replace('Revisión estructural: 22 de septiembre de 2026.', 'Historial de revision estructural: 22 de septiembre de 2026. La tabla siguiente describe aquella revision local, no la identidad de los archivos enviados ni un estado vigente de plataforma.')
$state = $state.Replace('### Verificación técnica del 22 de septiembre de 2026','### Historial de verificacion tecnica del 22 de septiembre de 2026')
$state = $state.Replace('[compilación](COMPILACION-seminario-i.md)','[compilacion](#compilacion-vigente)')
$compilation = @'
## Compilacion vigente

Ejecutar desde la raiz del repositorio que contiene ITESCA. En Windows:

```powershell
$materia = '.\ITESCA\maestria-en-gestion-administrativa\seminario-i-mga'
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-mga.tex"
.\scripts\latexmk-build.ps1 "$materia\presentacion-seminario-i-mga.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-1.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-2.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-3.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-4.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-6.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-10.tex"
.\scripts\latexmk-build.ps1 "$materia\presentacion-seminario-i-Actividad-10.tex"
```

La presentacion base de materia es una entrada reutilizable, no una entrega especifica ni una compilacion comprobada en la auditoria del 10 de octubre. No confundir los comandos disponibles con ejecuciones verificadas.

En Linux, para la infografia y el complemento de Tarea 6:

```bash
bash scripts/latexmk-build.sh ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-Actividad-4.tex
bash scripts/latexmk-build.sh ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-Actividad-6.tex
```

### Contrato unico

- El unico argumento obligatorio del compilador es la ruta del TEX. El PDF final queda junto a su fuente; Entregas conserva los archivos destinados al aula y las copias recuperadas de lo enviado.
- El motor es pdfLaTeX mediante latexmk; el nucleo local no requiere fontspec. La bibliografia local es seminario-i.bib; varias actividades presentan referencias manuales.
- Los reportes 1, 2, 3 y 6 cargan template.tex de la materia. Tarea 2 no es autocontenida: tiene formato y referencias locales, pero depende de ese nucleo.
- El reporte base y Tarea 10 cargan reporte-seminario-i-plantilla-actividad.tex. La infografia 4 y la presentacion de Tarea 10 son autocontenidas; los emblemas residen en ITESCA/assets-itesca.
- El nucleo replicado contiene 19 modulos con manifiesto de procedencia. No asumir una dependencia de ITESCA/_shared si no existe.
- No compilar plantillas aisladas ni versiones historicas como entregables. Las entradas genericas con identidad UnADM no estan certificadas para ITESCA.
- Compilar sin errores no acredita cumplimiento de rubrica, formato oficial, envio o calificacion. Los PDF actuales de T1-T3 no son las copias exactas enviadas. T6 y T10 requieren Word; LaTeX es complementario.

### Particularidades de Tareas 4 y 6

Tarea 4 produce portada e infografia en dos paginas A4 horizontales con TikZ y bibliografia manual. El control 26130503 ya esta incorporado; semestre y fecha de entrega vigente requieren revision. [Revision de la actividad 4](referencias-seminario-i/notas-seminario-i/actividad-4-errores-circulo-covey/revision-actividad-04.md).

Tarea 6 carga el [contenido editable](referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/elaboracion/contenido-actividad-6.tex) y dos imagenes locales; no necesita descargas para compilar. Cinco referencias manuales, indice, listas y referencias cruzadas se resuelven con las pasadas de latexmk. [Control LaTeX](referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/elaboracion/validar_latex.py) y [resultado registrado](referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/elaboracion/validacion/verificacion-latex.json). El resultado historico del control no sustituye una ejecucion nueva. El [Word preparado](Entregas/Tarea6_DeLaCruzMunoz.docx) no se reemplaza por el PDF. En Windows, el validador del Word requiere PYTHONUTF8=1 para leer la salida de Poppler.

## Discrepancias y regla de mantenimiento

Las dos guias de compilacion eran versiones breve y ampliada del mismo procedimiento, actualizadas por separado. El estado de entregables mezclaba verificaciones historicas con consultas posteriores. Esto produjo instrucciones repetidas, rutas con capitalizacion antigua, una clasificacion incorrecta de Tarea 2 y pendientes de control que ya estaban resueltos.

Se consolida un unico contrato y control de estado en este Readme. Los estados se identifican por fecha y evidencia; la consulta del 10 de octubre prevalece sobre estados anteriores incompatibles. La evidencia historica se conserva como tal, sin atribuir nuevas consultas a T8/T9 ni aprobar requisitos pendientes. Actualizar aqui el estado vigente y sus enlaces cuando cambien archivos, requisitos o entregas; mantener comprobantes y auditorias especificas en notas, no crear otra guia paralela de compilacion. Esta consolidacion no modifica reportes, entregas ni publicaciones.
'@
$text = $text.Replace('[Estado de entregables y revisión estructural](ESTADO-ENTREGABLES.md)', '[Estado de entregables y revision estructural](#estado-de-entregables)')
$text = $text.Replace('`COMPILACION-seminario-i.md`: comandos y contrato de compilación.', '[Compilacion vigente](#compilacion-vigente): comandos y contrato unico.')
$text = $text.Replace('`entregas/`','`Entregas/`')
$text += "`n`n## Estado de entregables`n`n" + $state.Trim() + "`n`n" + $compilation.Trim() + "`n"
[IO.File]::WriteAllText($target,$text,[Text.UTF8Encoding]::new($false))
$mapping = @{}
foreach ($source in $sources) { $mapping[[IO.Path]::GetFullPath((Join-Path $root $source))] = if ($source -eq 'ESTADO-ENTREGABLES.md') {'estado-de-entregables'} else {'compilacion-vigente'} }
foreach ($file in Get-ChildItem -LiteralPath 'C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA' -Recurse -File | Where-Object Extension -in @('.md','.json')) {
    if ($sources -contains $file.Name -and $file.DirectoryName -eq [IO.Path]::GetFullPath($root)) { continue }
    $content = [IO.File]::ReadAllText($file.FullName)
    $updated = [regex]::Replace($content,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
        $url=$match.Groups[1].Value
        if ($url -match '^[a-z]+://|^#') { return $match.Value }
        try { $absolute=[IO.Path]::GetFullPath((Join-Path $file.DirectoryName ([Uri]::UnescapeDataString(($url -split '#')[0])))) } catch { return $match.Value }
        if (-not $mapping.ContainsKey($absolute)) { return $match.Value }
        if ($file.FullName -eq $target) { return '](#'+$mapping[$absolute]+')' }
        return ']('+[IO.Path]::GetRelativePath($file.DirectoryName,$target).Replace('\','/').Replace(' ','%20')+'#'+$mapping[$absolute]+')'
    })
    if ($file.Extension -eq '.json' -and $file.FullName.StartsWith([IO.Path]::GetFullPath($root))) {
        foreach ($source in $sources) { $updated=$updated.Replace('"'+$source+'"','"Readme - Seminario I.md"') }
    }
    if ($updated -ne $content) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
foreach ($source in $sources) { Remove-Item -LiteralPath (Join-Path $root $source) }
$final=[IO.File]::ReadAllText($target)
foreach ($match in [regex]::Matches($final,'\]\(([^)]+)\)')) {
    $url=$match.Groups[1].Value
    if ($url -match '^[a-z]+://') { continue }
    $parts=$url.Split('#',2)
    if ($parts[0] -and -not(Test-Path -LiteralPath (Join-Path $root ([Uri]::UnescapeDataString($parts[0]))))) { throw "Enlace roto: $url" }
    if (-not $parts[0] -and $parts.Count -gt 1 -and $parts[1] -in @('estado-de-entregables','compilacion-vigente')) {
        if (-not $final.Contains('## '+(@{'estado-de-entregables'='Estado de entregables';'compilacion-vigente'='Compilacion vigente'}[$parts[1]]))) { throw 'Ancla ausente' }
    }
}
Write-Output 'Tres documentos absorbidos; contrato unico y estado fechado integrados; enlaces y anclas verificadas.'