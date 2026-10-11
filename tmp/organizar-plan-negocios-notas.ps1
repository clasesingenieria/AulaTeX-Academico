$ErrorActionPreference='Stop'
$root='C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
$notes=Join-Path $root 'referencias-plan-de-negocios/notas-plan-de-negocios'
$modules=@{'6534'=1;'6530'=2;'6540'=3;'6539'=4;'6548'=5;'6545'=6;'6547'=7;'6546'=8;'6552'=9;'6549'=10;'6550'=11;'6551'=12;'6553'=13;'6557'=14;'6555'=15}
$mapping=@{}; $records=@()
foreach($kind in @('planeaciones-generadas','actividades-generadas')){
 $source=Join-Path $root $kind
 foreach($file in Get-ChildItem -LiteralPath $source -Recurse -File){
  $relative=[IO.Path]::GetRelativePath($source,$file.FullName)
  $match=[regex]::Match($file.Name,'(?:modulo-|Actividad-)(\d+)')
  if($match.Success -and $modules.ContainsKey($match.Groups[1].Value)){
   $destination=Join-Path $notes ('actividad-'+$modules[$match.Groups[1].Value]+'/'+$kind+'/'+$relative)
  }else{$destination=Join-Path $notes ('materiales-generales/'+$kind+'/'+$relative)}
  $mapping[$file.FullName]=$destination
 }
}
foreach($entry in @(
 @{source='referencias-plan-de-negocios/actividad-11-2026-09-30';target='actividad-11/evidencias/2026-09-30'},
 @{source='referencias-plan-de-negocios/actividad-11-2026-10-01';target='actividad-11/evidencias/2026-10-01'},
 @{source='referencias-plan-de-negocios/actividad-12-2026-10-05';target='actividad-12/evidencias/2026-10-05'},
 @{source='referencias-plan-de-negocios/correccion-sondeo-2026-09-30';target='actividad-10/correccion-sondeo-2026-09-30'},
 @{source='referencias-plan-de-negocios/metodologia-actividad-5';target='actividad-5/metodologia'},
 @{source='referencias-plan-de-negocios/monterrey-2026-09-23';target='materiales-generales/fuentes-monterrey-2026-09-23'}
)){
 $source=Join-Path $root $entry.source
 foreach($file in Get-ChildItem -LiteralPath $source -Recurse -File){$mapping[$file.FullName]=Join-Path $notes ($entry.target+'/'+[IO.Path]::GetRelativePath($source,$file.FullName))}
}
foreach($source in $mapping.Keys){if(Test-Path -LiteralPath $mapping[$source]){throw 'Destino existente'};$records+=[pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$mapping[$source]).Replace('\','/');sha256=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()}}
foreach($file in @(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.json','.tex','.bib','.py','.ps1'))){
 $target=$file.FullName;if($mapping.ContainsKey($target)){$target=$mapping[$target]};$oldDir=$file.DirectoryName;$newDir=Split-Path $target
 $text=[IO.File]::ReadAllText($file.FullName);$updated=$text
 if($file.Extension -eq '.md'){
  $updated=[regex]::Replace($updated,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
   $url=$match.Groups[1].Value;if($url -match '^[a-z]+://|^#'){return $match.Value};$parts=$url.Split('#',2)
   try{$absolute=[IO.Path]::GetFullPath((Join-Path $oldDir ([Uri]::UnescapeDataString($parts[0]))))}catch{return $match.Value}
   if($mapping.ContainsKey($absolute)){$absolute=$mapping[$absolute]}
   else{foreach($entry in @(@{old='planeaciones-generadas';new='materiales-generales/planeaciones-generadas'},@{old='actividades-generadas';new='materiales-generales/actividades-generadas'})){ $prefix=Join-Path $root $entry.old;if($absolute.StartsWith($prefix+[IO.Path]::DirectorySeparatorChar)){$candidate=Join-Path $notes ($entry.new+'/'+[IO.Path]::GetRelativePath($prefix,$absolute));if($mapping.Values | Where-Object {$_ -eq $candidate -or $_.StartsWith($candidate+[IO.Path]::DirectorySeparatorChar)}){$absolute=$candidate};break}}}
   $relative=[IO.Path]::GetRelativePath($newDir,$absolute).Replace('\','/').Replace(' ','%20');if($parts.Count -gt 1){$relative+='#'+$parts[1]};return "]($relative)"
  })
 }
 if($file.Extension -eq '.json'){
  $data=$updated | ConvertFrom-Json
  function Rebase($node){
   if($node -is [array]){foreach($child in $node){Rebase $child};return};if($node -isnot [pscustomobject]){return}
   foreach($prop in $node.PSObject.Properties){
    if($prop.Value -is [string] -and $prop.Name -notin @('origen','source_original','location_original','text','texto','title') -and $prop.Value.Length -lt 600 -and $prop.Value -notmatch '^[a-z]+://|[\r\n]'){
     foreach($base in @($oldDir,$root,'C:/Users/Sysx/Documents/AulaTeX-Academico')){try{$absolute=[IO.Path]::GetFullPath((Join-Path $base $prop.Value))}catch{continue};$mapped=$mapping.ContainsKey($absolute);if($mapped){$absolute=$mapping[$absolute]};if($mapped -or ($oldDir -ne $newDir -and (Test-Path -LiteralPath $absolute -PathType Leaf))){$newBase=$base;if($base -eq $oldDir){$newBase=$newDir};$prop.Value=[IO.Path]::GetRelativePath($newBase,$absolute).Replace('\','/');break}}
    }else{Rebase $prop.Value}
   }
  };Rebase $data;$updated=$data | ConvertTo-Json -Depth 100
 }
 if($file.Extension -in @('.py','.tex','.bib','.ps1')){foreach($record in $records){$updated=$updated.Replace($record.origen,$record.destino)}}
 if($target -ne $file.FullName -or $updated -ne $text){New-Item -ItemType Directory -Path $newDir -Force|Out-Null;[IO.File]::WriteAllText($target,$updated,[Text.UTF8Encoding]::new($false))}
}
foreach($source in $mapping.Keys){$target=$mapping[$source];if(Test-Path -LiteralPath $target){Remove-Item -LiteralPath $source}else{New-Item -ItemType Directory -Path (Split-Path $target) -Force|Out-Null;Move-Item -LiteralPath $source -Destination $target}}
foreach($record in $records){if([IO.Path]::GetExtension($record.destino) -notin @('.md','.json','.tex','.bib','.py','.ps1')){if((Get-FileHash -LiteralPath (Join-Path $root $record.destino)).Hash.ToLowerInvariant() -ne $record.sha256){throw 'Hash cambiado'}}}
foreach($relative in @('planeaciones-generadas','actividades-generadas','referencias-plan-de-negocios/actividad-11-2026-09-30','referencias-plan-de-negocios/actividad-11-2026-10-01','referencias-plan-de-negocios/actividad-12-2026-10-05','referencias-plan-de-negocios/correccion-sondeo-2026-09-30','referencias-plan-de-negocios/metodologia-actividad-5','referencias-plan-de-negocios/monterrey-2026-09-23')){ $directory=Join-Path $root $relative;if(Get-ChildItem -LiteralPath $directory -Recurse -File){throw 'Carpeta no vacia'};Remove-Item -LiteralPath $directory -Recurse }
New-Item -ItemType Directory -Path (Join-Path $notes 'materiales-generales') -Force|Out-Null
[IO.File]::WriteAllText((Join-Path $notes 'materiales-generales/organizacion-2026-10-10.json'),(@{fecha='2026-10-10';movimientos=$records;nota='Hashes previos a ajustes de rutas; variantes y evidencias conservadas'}|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output "$($records.Count) archivos organizados por actividad; originales binarios integros."