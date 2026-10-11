$ErrorActionPreference='Stop'
$root='C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
$repo='C:/Users/Sysx/Documents/AulaTeX-Academico'
$notes='referencias-seminario-i/notas-seminario-i'
$plans=Join-Path $root 'planeaciones-seminario-i'
$archive="$notes/materiales-generales/historico-planeaciones-2026-10-10"
$mapping=@{}; $linkMapping=@{}; $records=@(); $outputs=@{}
$modules=@{0=2876;1=2877;2=2885;3=2886;4=2887;5=2888;6=2889;7=2906;8=2908;9=2909;10=2910;11=2911}
$audit=Get-Content -LiteralPath (Join-Path $root "$notes/materiales-generales/auditoria-entregables-2026-10-10.json") -Raw | ConvertFrom-Json
foreach($file in Get-ChildItem -LiteralPath $plans -Recurse -File){
 $relative=[IO.Path]::GetRelativePath($plans,$file.FullName).Replace('\','/')
 $target=Join-Path $root "$archive/$relative"
 if(Test-Path -LiteralPath $target){throw 'Archivo historico existente'}
 $mapping[$file.FullName]=$target
}
foreach($file in Get-ChildItem -LiteralPath $plans -Recurse -Filter 'actividad-*.md'){
 $match=[regex]::Match($file.Name,'^actividad-(\d+)-(.+)\.md$'); if(-not $match.Success){continue}
 $number=[int]$match.Groups[1].Value; $slug=$match.Groups[2].Value
 $name=if($number -eq 0){'Planeacion - Foro de presentacion.md'}else{'Planeacion - Tarea '+$number.ToString('00')+' - '+$slug+'.md'}
 $destination=Join-Path $plans $name
 $content=[IO.File]::ReadAllText($file.FullName)
 $current=@($audit.actividades | Where-Object actividad -eq $number)
 if($current.Count -eq 1){
  $content+="`n`n## Consigna cotejada en plataforma - 10 de octubre de 2026`n`n"+$current[0].consigna.Trim()+"`n`nEsta consigna cotejada prevalece sobre ampliaciones o requisitos incompatibles de la ficha local anterior. El estado de entrega se controla en el Readme; esta planeacion no acredita un nuevo envio.`n"
 }
 if($modules.ContainsKey($number)){
  $module=$modules[$number]; $jsonPath=Join-Path $plans "planeacion-modulo-$module.json"
  if(Test-Path -LiteralPath $jsonPath){
   $data=Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json; $activity=$data.activity
   $content+="`n`n## Secuencia y control documental`n`nModulo Moodle: $module. La normalizacion del 22 de septiembre fue local; no acredita aprobacion docente ni vigencia nueva.`n"
   if($activity.objective.value){$content+="`nObjetivo registrado: "+$activity.objective.value+"`n"}
   foreach($step in $activity.sequence){$content+="`n- "+$step.phase+': '+$step.student}
   foreach($pending in $activity.pending){$content+="`n- Pendiente de la ficha historica: "+$pending}
   $content+="`n`nLas propuestas y pendientes historicos se conservan como antecedente; no sustituyen datos posteriores cotejados. [Registro original completo](../$archive/planeacion-modulo-$module.json).`n"
   $linkMapping[(Join-Path $plans "planeacion-modulo-$module.md")]=$destination
  }
 }
 if($number -eq 7){
  $registration=Get-Content -LiteralPath (Join-Path $plans 'planeacion-modulo-2907.json') -Raw | ConvertFrom-Json
  $content+="`n`n## Registro del proyecto - tramite asociado`n`nModulo 2907; no constituye una tarea numerada adicional. "+$registration.activity.objective.value+"`n`n[Requisitos y procedencia originales](../$archive/planeacion-modulo-2907.json). Consultar los comprobantes en notas de Tarea 7 antes de volver a enviar.`n"
  $linkMapping[(Join-Path $plans 'planeacion-modulo-2907.md')]=$destination
 }
 $content+="`n`n## Alcance de esta planeacion`n`nUna ficha Markdown por tarea. No se genera PDF: aun no hay un formato aprobado de planeacion LaTeX. Conservar originales historicos en notas y actualizar esta ficha cuando cambie una consigna, sin crear otra planeacion paralela.`n"
 $outputs[$destination]=$content
 $linkMapping[$file.FullName]=$destination
}
$rootMoves=@{
 'template.tex'='assets-seminario-i/plantilla/template.tex'
 'reporte-seminario-i-plantilla-actividad.tex'='assets-seminario-i/plantilla/reporte-seminario-i-plantilla-actividad.tex'
 'presentacion-seminario-i-mga.tex'="$notes/materiales-generales/encuadre/presentacion-seminario-i-mga.tex"
 'reporte-seminario-i-mga.tex'="$notes/materiales-generales/encuadre/reporte-seminario-i-mga.tex"
 'reporte-seminario-i-mga.pdf'="$notes/materiales-generales/encuadre/reporte-seminario-i-mga.pdf"
 'presentacion-seminario-i.tex'="$notes/historico/plantillas-genericas/presentacion-seminario-i.tex"
 'reporte-seminario-i.tex'="$notes/historico/plantillas-genericas/reporte-seminario-i.tex"
}
foreach($name in $rootMoves.Keys){$source=Join-Path $root $name;$destination=Join-Path $root $rootMoves[$name];if(Test-Path -LiteralPath $destination){throw 'Destino de raiz existente'};$mapping[$source]=$destination}
foreach($source in $mapping.Keys){$records+=[pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$mapping[$source]).Replace('\','/');sha256=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()}}
$documents=@(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.tex','.json','.py','.bib'))
foreach($file in $documents){
 $target=$file.FullName;if($mapping.ContainsKey($target)){$target=$mapping[$target]}
 $oldDir=$file.DirectoryName;$newDir=Split-Path $target;$text=[IO.File]::ReadAllText($file.FullName);$updated=$text
 if($file.Extension -eq '.md'){
  $updated=[regex]::Replace($updated,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
   $url=$match.Groups[1].Value;if($url -match '^[a-z]+://|^#'){return $match.Value};$parts=$url.Split('#',2)
   $absolute=[IO.Path]::GetFullPath((Join-Path $oldDir ([Uri]::UnescapeDataString($parts[0]))))
   if($linkMapping.ContainsKey($absolute)){$absolute=$linkMapping[$absolute]}elseif($mapping.ContainsKey($absolute)){$absolute=$mapping[$absolute]}
   $relative=[IO.Path]::GetRelativePath($newDir,$absolute).Replace('\','/').Replace(' ','%20');if($parts.Count -gt 1){$relative+='#'+$parts[1]};return "]($relative)"
  })
 }
 if($file.Extension -eq '.json'){
  $data=$updated | ConvertFrom-Json
  function Rebase($node){
   if($node -is [array]){foreach($child in $node){Rebase $child};return};if($node -isnot [pscustomobject]){return}
   foreach($property in $node.PSObject.Properties){
    if($property.Value -is [string] -and $property.Name -notin @('origen','location_original','text','texto','title') -and $property.Value.Length -lt 650 -and $property.Value -notmatch '^[a-z]+://|[\r\n]'){
     foreach($base in @($oldDir,$root,$repo)){
      try{$absolute=[IO.Path]::GetFullPath((Join-Path $base $property.Value))}catch{continue};$mapped=$mapping.ContainsKey($absolute)
      if($mapped){$absolute=$mapping[$absolute]}
      if($mapped -or ($oldDir -ne $newDir -and (Test-Path -LiteralPath $absolute -PathType Leaf))){$newBase=$base;if($base -eq $oldDir){$newBase=$newDir};$property.Value=[IO.Path]::GetRelativePath($newBase,$absolute).Replace('\','/');break}
     }
    }else{Rebase $property.Value}
   }
  }
  Rebase $data;$updated=$data | ConvertTo-Json -Depth 100
 }
 if($file.Extension -in @('.py','.tex','.bib')){
  foreach($name in $rootMoves.Keys){
   $oldRoot='ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/'+$name;$newRoot='ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/'+$rootMoves[$name]
   $updated=$updated.Replace($oldRoot,$newRoot)
   $updated=$updated.Replace('{'+$name+'}','{'+$newRoot+'}')
   $updated=$updated.Replace('"'+$name+'"','"'+$rootMoves[$name]+'"')
  }
 }
 if($updated -ne $text -or $target -ne $file.FullName){New-Item -ItemType Directory -Path $newDir -Force | Out-Null;[IO.File]::WriteAllText($target,$updated,[Text.UTF8Encoding]::new($false))}
}
foreach($source in $mapping.Keys){$target=$mapping[$source];if(-not(Test-Path -LiteralPath $target)){New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null;Move-Item -LiteralPath $source -Destination $target}else{Remove-Item -LiteralPath $source}}
Get-ChildItem -LiteralPath $plans -Directory -Recurse | Sort-Object {$_.FullName.Length} -Descending | ForEach-Object {if(-not(Get-ChildItem -LiteralPath $_.FullName)){Remove-Item -LiteralPath $_.FullName}}
foreach($destination in $outputs.Keys){[IO.File]::WriteAllText($destination,$outputs[$destination],[Text.UTF8Encoding]::new($false))}
[IO.File]::WriteAllText((Join-Path $root "$notes/materiales-generales/uniformizacion-2026-10-10.json"),(@{fecha='2026-10-10';movimientos=$records;planeaciones=@($outputs.Keys | ForEach-Object {[IO.Path]::GetRelativePath($root,$_).Replace('\','/')});nota='Originales conservados en notas; rutas de texto actualizadas'} | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
if(@(Get-ChildItem -LiteralPath $plans -File).Count -ne 19){throw 'Numero de planeaciones inesperado'}
Write-Output '19 fichas: tareas 1-18 y foro; raiz sin entradas genericas ni plantillas; originales conservados.'