$ErrorActionPreference='Stop'
$root='C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
$target=Join-Path $root 'Readme - Seminario I.md'
if(Test-Path -LiteralPath $target){throw 'Destino existente; no sobrescribir'}
$sources=@('README.md','ESTADO-ENTREGABLES.md','ORDEN-ACTIVIDADES.md','LOTE-ACTIVIDADES.md','VALIDACION-ACTIVIDADES-1-15.md','COMPILACION.md')
$anchors=@{'README.md'='plan-de-negocios---ggpn01';'ESTADO-ENTREGABLES.md'='estado-de-entregables-historico';'ORDEN-ACTIVIDADES.md'='orden-y-numeracion';'LOTE-ACTIVIDADES.md'='historial-de-generacion';'VALIDACION-ACTIVIDADES-1-15.md'='validacion-historica';'COMPILACION.md'='compilacion-y-dependencias'}
$headings=@{'ESTADO-ENTREGABLES.md'='Estado de entregables historico';'ORDEN-ACTIVIDADES.md'='Orden y numeracion';'LOTE-ACTIVIDADES.md'='Historial de generacion';'VALIDACION-ACTIVIDADES-1-15.md'='Validacion historica';'COMPILACION.md'='Compilacion y dependencias'}
$technical='referencias-plan-de-negocios/notas-plan-de-negocios/materiales-generales/historico-formatos'
$moves=@{'formato-itesca-plan-negocios.tex'="$technical/formato-itesca-plan-negocios.tex";'formato-itesca-plan-negocios-generadas.tex'="$technical/formato-itesca-plan-negocios-generadas.tex"}
$parts=@()
foreach($name in $sources){
 $text=[IO.File]::ReadAllText((Join-Path $root $name))
 if($name -ne 'README.md'){
  $text=[regex]::Replace($text,'(?m)^(#{1,5}) ','$1# ')
  $text=[regex]::Replace($text,'\A## [^\r\n]+','## '+$headings[$name])
  $text=$text.Insert($text.IndexOf("`n")+1,"`nHistorial conservado con sus fechas originales. No acredita estado actual ni sustituye las actualizaciones del inicio de este documento.`n")
 }
 $parts+=$text.Trim()
}
$merged=$parts -join "`n`n"
$merged+="`n`n## Criterio vigente de consolidacion`n`nEl nombre de este archivo, Readme - Seminario I.md, fue solicitado expresamente para esta carpeta; su contenido corresponde a Plan de Negocios, GGPN01, no a Seminario I. Se integraron seis documentos de control; consignas y notas academicas especificas permanecen por actividad. Los cortes de septiembre son historicos, no una nueva consulta del aula.`n`nLos 17 Word con portada institucional y sus PDF estan en Entregas; sus cuerpos e imagenes previas se cotejaron contra respaldos. Los originales de portada se conservan en notas generales. La portada comun se controla desde reporte-plan-de-negocios-plantilla-actividad.tex; los dos formatos antiguos se retiraron de la raiz y se preservaron en notas tecnicas. Los borradores historicos que usan portadaITESCA cargan el formato-generadas archivado, no la plantilla activa. No se modificaron entregas confirmadas ni se hicieron envios.`n"
[IO.File]::WriteAllText($target,$merged,[Text.UTF8Encoding]::new($false))
foreach($name in $moves.Keys){$source=Join-Path $root $name;$destination=Join-Path $root $moves[$name];if(Test-Path -LiteralPath $destination){throw 'Formato archivado existente'};$hash=(Get-FileHash -LiteralPath $source).Hash;New-Item -ItemType Directory -Path (Split-Path $destination) -Force|Out-Null;Move-Item -LiteralPath $source -Destination $destination;if((Get-FileHash -LiteralPath $destination).Hash -ne $hash){throw 'Formato alterado'}}
foreach($file in Get-ChildItem -LiteralPath 'C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA' -Recurse -File | Where-Object Extension -in @('.md','.json','.tex','.py','.ps1')){
 if($file.DirectoryName -eq [IO.Path]::GetFullPath($root) -and $sources -contains $file.Name){continue}
 $text=[IO.File]::ReadAllText($file.FullName);$updated=$text
 if($file.Extension -eq '.md'){
  $updated=[regex]::Replace($updated,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
   $url=$match.Groups[1].Value;if($url -match '^[a-z]+://|^#'){return $match.Value}
   try{$absolute=[IO.Path]::GetFullPath((Join-Path $file.DirectoryName ([Uri]::UnescapeDataString(($url -split '#')[0]))))}catch{return $match.Value}
   foreach($name in $sources){if($absolute -eq [IO.Path]::GetFullPath((Join-Path $root $name))){$prefix=if($file.FullName -eq $target){''}else{[IO.Path]::GetRelativePath($file.DirectoryName,$target).Replace('\','/').Replace(' ','%20')};return ']('+$prefix+'#'+$anchors[$name]+')'}}
   foreach($name in $moves.Keys){if($absolute -eq [IO.Path]::GetFullPath((Join-Path $root $name))){return ']('+[IO.Path]::GetRelativePath($file.DirectoryName,(Join-Path $root $moves[$name])).Replace('\','/').Replace(' ','%20')+')'}}
   return $match.Value
  })
 }
 if($file.FullName.StartsWith([IO.Path]::GetFullPath($root)) -and $file.Extension -eq '.tex'){
  $old='ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/actividades-generadas/2026-II/revision-2026-09-20/formato-itesca-plan-negocios.tex'
  $updated=$updated.Replace($old,'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/'+$moves['formato-itesca-plan-negocios-generadas.tex'])
 }
 if($file.Extension -eq '.json' -and $file.FullName.StartsWith([IO.Path]::GetFullPath($root))){foreach($name in $sources){$updated=$updated.Replace('"'+$name+'"','"Readme - Seminario I.md"')}}
 if($updated -ne $text){[IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false))}
}
foreach($name in $sources){Remove-Item -LiteralPath (Join-Path $root $name)}
foreach($match in [regex]::Matches([IO.File]::ReadAllText($target),'\]\(([^)]+)\)')){$url=$match.Groups[1].Value;if($url -match '^[a-z]+://|^#'){continue};if(-not(Test-Path -LiteralPath (Join-Path $root ([Uri]::UnescapeDataString(($url -split '#')[0]))))){throw "Enlace roto: $url"}}
Write-Output 'Seis MD consolidados; dos formatos archivados; enlaces locales verificados.'