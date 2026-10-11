$ErrorActionPreference='Stop'
$root='C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
$notes='referencias-seminario-i/notas-seminario-i'
$modules=@{'2877'='actividad-1-ruta-titulacion';'2885'='actividad-2-normas-apa';'2886'='actividad-3-estado-del-arte';'2887'='actividad-4-errores-circulo-covey';'2889'='actividad-6-formato-institucional';'2907'='actividad-7-tema-titulo';'2908'='actividad-8-antecedentes';'2909'='actividad-9-planteamiento-problema';'2910'='actividad-10-objetivos'}
$mapping=@{}; $records=@()
$original=Join-Path $root 'anteproyecto'
foreach($file in Get-ChildItem -LiteralPath $original -Recurse -File){
 $relative=[IO.Path]::GetRelativePath($original,$file.FullName).Replace('\','/')
 $destination="$notes/materiales-generales/anteproyecto-acumulativo/$relative"
 if($relative -like 'actividad-07-*'){$destination="$notes/actividad-7-tema-titulo/borradores/$($file.Name)"}
 elseif($relative -like 'vtaxi-2026-09-28/*'){$destination="$notes/actividad-10-objetivos/elaboracion-vtaxi-2026-09-28/$($file.Name)"}
 elseif($relative -like 'matrices/matriz-estado-del-arte.csv'){$destination="$notes/actividad-3-estado-del-arte/matrices/$($file.Name)"}
 elseif($relative -like 'evidencias/envio-actividad-10-2026-10-04/*'){$destination="$notes/actividad-10-objetivos/comprobantes-envio/2026-10-04/"+$relative.Substring('evidencias/envio-actividad-10-2026-10-04/'.Length)}
 elseif($relative -like 'evidencias/*'){
  $module=[regex]::Match($file.Name,'^(2877|2885|2886|2887|2889|2907|2908|2909|2910)(?:-|\.)')
  $activity=$null
  if($module.Success){$activity=$modules[$module.Groups[1].Value]}
  elseif($file.Name -eq '03.01 Seleccion de proyecto de titulacion 25130604.docx'){$activity='actividad-7-tema-titulo'}
  elseif($file.Name -in @('Formato 01. Matriz de estado del arte.docx','reporte-seminario-i-Actividad-3.pdf')){$activity='actividad-3-estado-del-arte'}
  elseif($file.Name -in @('Matriz de Consistencia.pdf','3.2 Planteamiento del problema.pdf')){$activity='actividad-9-planteamiento-problema'}
  elseif($file.Name -eq '3.1 Antecedentes.pdf'){$activity='actividad-8-antecedentes'}
  if($activity){$destination="$notes/$activity/evidencias/"+$relative.Substring('evidencias/'.Length)}
  else{$destination="$notes/materiales-generales/auditorias-anteproyecto/"+$relative.Substring('evidencias/'.Length)}
 }
 $mapping[$file.FullName]=Join-Path $root $destination
}
$registration=Join-Path $root "$notes/registro-proyecto"
foreach($file in Get-ChildItem -LiteralPath $registration -Recurse -File){$mapping[$file.FullName]=Join-Path $root ("$notes/actividad-7-tema-titulo/registro-proyecto/"+[IO.Path]::GetRelativePath($registration,$file.FullName))}
foreach($source in $mapping.Keys){if(Test-Path -LiteralPath $mapping[$source]){throw "Destino existente: $($mapping[$source])"};$records+=[pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$mapping[$source]).Replace('\','/');sha256=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()}}
function Resolve-Target($absolute){if($mapping.ContainsKey($absolute)){return $mapping[$absolute]};return $absolute}
foreach($file in @(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.json','.tex','.bib','.py','.csv'))){
 $target=Resolve-Target $file.FullName; $oldDir=$file.DirectoryName; $newDir=Split-Path $target
 $text=[IO.File]::ReadAllText($file.FullName);$updated=$text
 if($file.Extension -eq '.md'){
  $updated=[regex]::Replace($updated,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
   $url=$match.Groups[1].Value;if($url -match '^[a-z]+://|^#'){return $match.Value}
   $parts=$url.Split('#',2);$absolute=[IO.Path]::GetFullPath((Join-Path $oldDir ([Uri]::UnescapeDataString($parts[0]))));$absolute=Resolve-Target $absolute
   $relative=[IO.Path]::GetRelativePath($newDir,$absolute).Replace('\','/').Replace(' ','%20');if($parts.Count -gt 1){$relative+='#'+$parts[1]};return "]($relative)"
  })
 }
 if($file.Extension -eq '.json'){
  $data=$updated | ConvertFrom-Json
  function Rebase($node){
   if($node -is [array]){foreach($child in $node){Rebase $child};return};if($node -isnot [pscustomobject]){return}
   foreach($prop in $node.PSObject.Properties){
    if($prop.Value -is [string] -and $prop.Value.Length -lt 600 -and $prop.Value -notmatch '^[a-z]+://|[\r\n]' -and $prop.Name -notin @('origen','location_original','texto','text','title')){
     foreach($base in @($oldDir,$root,'C:/Users/Sysx/Documents/AulaTeX-Academico')){
      try{$absolute=[IO.Path]::GetFullPath((Join-Path $base $prop.Value))}catch{continue}
      $mapped=$mapping.ContainsKey($absolute);$absolute=Resolve-Target $absolute
      if($mapped -or ($oldDir -ne $newDir -and (Test-Path -LiteralPath $absolute -PathType Leaf))){$newBase=$base;if($base -eq $oldDir){$newBase=$newDir};$prop.Value=[IO.Path]::GetRelativePath($newBase,$absolute).Replace('\','/');break}
     }
    }else{Rebase $prop.Value}
   }
  }
  Rebase $data;$updated=$data | ConvertTo-Json -Depth 100
 }
 foreach($record in $records){
  $updated=$updated.Replace($record.origen,$record.destino)
  $oldRelative=[IO.Path]::GetRelativePath($oldDir,(Join-Path $root $record.origen)).Replace('\','/')
  $newRelative=[IO.Path]::GetRelativePath($newDir,(Join-Path $root $record.destino)).Replace('\','/')
  $updated=$updated.Replace('{'+$oldRelative+'}','{'+$newRelative+'}')
  $updated=$updated.Replace((Join-Path $root $record.origen).Replace('\','/'),(Join-Path $root $record.destino).Replace('\','/'))
 }
 if($file.Extension -eq '.py'){
  $updated=$updated.Replace('SUBJECT / "anteproyecto/vtaxi-2026-09-28"','SUBJECT / "'+$notes+'/actividad-10-objetivos/elaboracion-vtaxi-2026-09-28"')
 }
 if($target -ne $file.FullName -or $updated -ne $text){New-Item -ItemType Directory -Path $newDir -Force | Out-Null;[IO.File]::WriteAllText($target,$updated,[Text.UTF8Encoding]::new($false))}
}
foreach($source in $mapping.Keys){$target=$mapping[$source];if(-not(Test-Path -LiteralPath $target)){New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null;Move-Item -LiteralPath $source -Destination $target}else{Remove-Item -LiteralPath $source}}
foreach($record in $records){if([IO.Path]::GetExtension($record.destino) -in @('.docx','.pdf','.png','.txt','.csv')){if((Get-FileHash -LiteralPath (Join-Path $root $record.destino)).Hash.ToLowerInvariant() -ne $record.sha256){throw 'Contenido cambiado'}}}
foreach($directory in @($original,$registration)){if(Get-ChildItem -LiteralPath $directory -Recurse -File){throw 'Absorcion incompleta'};Remove-Item -LiteralPath $directory -Recurse}
[IO.File]::WriteAllText((Join-Path $root "$notes/materiales-generales/absorcion-anteproyecto-2026-10-10.json"),(@{fecha='2026-10-10';movimientos=$records;nota='Hashes previos a ajustes de rutas JSON/MD/TEX; archivos entregados y binarios intactos'} | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
Write-Output "$($records.Count) archivos distribuidos por actividad y alcance; carpetas absorbidas."