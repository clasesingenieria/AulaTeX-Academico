$ErrorActionPreference='Stop'
$root='C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
$notes='referencias-seminario-i/notas-seminario-i'
$work="$notes/actividad-6-formato-institucional/elaboracion"
$activities=@{'2876'='actividad-0-foro-presentacion';'2877'='actividad-1-ruta-titulacion';'2885'='actividad-2-normas-apa';'2886'='actividad-3-estado-del-arte';'2887'='actividad-4-errores-circulo-covey';'2888'='actividad-5-escritura-cientifica';'2889'='actividad-6-formato-institucional';'2906'='actividad-7-tema-titulo';'2907'='registro-proyecto';'2908'='actividad-8-antecedentes';'2909'='actividad-9-planteamiento-problema';'2910'='actividad-10-objetivos';'2911'='actividad-11-justificacion'}
$mapping=@{}; $records=@()
foreach($file in Get-ChildItem -LiteralPath (Join-Path $root 'tarea6') -Recurse -File){
 $mapping[$file.FullName]=Join-Path $root ("$work/"+[IO.Path]::GetRelativePath((Join-Path $root 'tarea6'),$file.FullName))
}
foreach($file in Get-ChildItem -LiteralPath (Join-Path $root 'planeaciones-generadas') -Recurse -File){
 $match=[regex]::Match($file.Name,'modulo-(\d+)')
 if(-not $match.Success -or -not $activities.ContainsKey($match.Groups[1].Value)){throw "Modulo no clasificado: $($file.Name)"}
 $mapping[$file.FullName]=Join-Path $root ("$notes/"+$activities[$match.Groups[1].Value]+"/planeacion-generada/revision-2026-09-15/"+$file.Name)
}
foreach($source in $mapping.Keys){if(Test-Path -LiteralPath $mapping[$source]){throw 'Destino existente'}; $records+=[pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$mapping[$source]).Replace('\','/');sha256=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()}}
$documents=@(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.json','.tex','.bib','.py'))
foreach($file in $documents){
 $target=$file.FullName; if($mapping.ContainsKey($target)){$target=$mapping[$target]}
 $oldDir=$file.DirectoryName; $newDir=Split-Path $target
 $text=[IO.File]::ReadAllText($file.FullName); $updated=$text
 if($file.Extension -eq '.md'){
  $updated=[regex]::Replace($updated,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
   $url=$match.Groups[1].Value; if($url -match '^[a-z]+://|^#'){return $match.Value}
   $parts=$url.Split('#',2); $absolute=[IO.Path]::GetFullPath((Join-Path $oldDir ([Uri]::UnescapeDataString($parts[0]))))
   if($mapping.ContainsKey($absolute)){$absolute=$mapping[$absolute]}
   elseif($absolute.StartsWith((Join-Path $root 'tarea6')+[IO.Path]::DirectorySeparatorChar)){$absolute=Join-Path (Join-Path $root $work) ([IO.Path]::GetRelativePath((Join-Path $root 'tarea6'),$absolute))}
   $relative=[IO.Path]::GetRelativePath($newDir,$absolute).Replace('\','/').Replace(' ','%20'); if($parts.Count -gt 1){$relative+='#'+$parts[1]}; return "]($relative)"
  })
 }
 if($file.Extension -eq '.json'){
  $data=$updated | ConvertFrom-Json
  function Rebase($node){
   if($node -is [array]){foreach($child in $node){Rebase $child};return}; if($node -isnot [pscustomobject]){return}
   foreach($prop in $node.PSObject.Properties){
    if($prop.Value -is [string] -and $prop.Value.Length -lt 600 -and $prop.Value -notmatch '^[a-z]+://|[\r\n]' -and $prop.Name -notin @('origen','location_original','texto')){
     foreach($base in @($oldDir,$root,(Split-Path (Split-Path (Split-Path $root))))){
      try{$absolute=[IO.Path]::GetFullPath((Join-Path $base $prop.Value))}catch{continue}
      $mapped=$mapping.ContainsKey($absolute); if($mapped){$absolute=$mapping[$absolute]}
      if($mapped -or ($oldDir -ne $newDir -and (Test-Path -LiteralPath $absolute -PathType Leaf))){$newBase=$base; if($base -eq $oldDir){$newBase=$newDir}; $prop.Value=[IO.Path]::GetRelativePath($newBase,$absolute).Replace('\','/');break}
     }
    }else{Rebase $prop.Value}
   }
  }
  Rebase $data; $updated=$data | ConvertTo-Json -Depth 100
 }
 foreach($record in $records){$updated=$updated.Replace($record.origen,$record.destino)}
 if($file.Extension -in @('.tex','.py','.md')){$updated=$updated.Replace('tarea6/',$work+'/')}
 if($file.Extension -eq '.py' -and $file.FullName.StartsWith((Join-Path $root 'tarea6'))){
  $updated=$updated.Replace('COURSE = ROOT.parent','COURSE = ROOT.parents[3]').Replace('REPO = ROOT.parents[3]','REPO = ROOT.parents[3].parents[2]')
  $updated=$updated.Replace('ROOT.parent /','ROOT.parents[3] /')
  $updated=$updated.Replace('Path(__file__).resolve().parents[1] / "referencias-seminario-i','Path(__file__).resolve().parents[4] / "referencias-seminario-i')
 }
 if($target -ne $file.FullName -or $updated -ne $text){New-Item -ItemType Directory -Path $newDir -Force | Out-Null; [IO.File]::WriteAllText($target,$updated,[Text.UTF8Encoding]::new($false))}
}
foreach($source in $mapping.Keys){$target=$mapping[$source]; if(-not(Test-Path -LiteralPath $target)){New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null; Move-Item -LiteralPath $source -Destination $target}else{Remove-Item -LiteralPath $source}}
foreach($record in $records){if([IO.Path]::GetExtension($record.destino) -notin @('.md','.json','.tex','.bib','.py')){if((Get-FileHash -LiteralPath (Join-Path $root $record.destino)).Hash.ToLowerInvariant() -ne $record.sha256){throw 'Integridad incorrecta'}}}
foreach($folder in @('tarea6','planeaciones-generadas')){ $path=Join-Path $root $folder; if(Get-ChildItem -LiteralPath $path -Recurse -File){throw 'Archivos pendientes'}; Remove-Item -LiteralPath $path -Recurse }
[IO.File]::WriteAllText((Join-Path $root "$notes/materiales-generales/absorcion-carpetas-2026-10-10.json"),(@{movimientos=$records;nota='Hashes originales; rutas actualizadas en fuentes de texto';fecha='2026-10-10'} | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
Write-Output "$($records.Count) archivos redistribuidos; ambas carpetas absorbidas; binarios integros."