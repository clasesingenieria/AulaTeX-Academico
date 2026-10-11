$ErrorActionPreference='Stop'
$root='C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
$notes=Join-Path $root 'referencias-plan-de-negocios/notas-plan-de-negocios'
$topics=@{1='foro-bienvenida';2='evaluacion-diagnostica';3='examen-unidad-1';4='descripcion-empresa';5='demanda-oferta';6='imagen-empresa';7='area-geografica';8='mercadotecnia-publicidad';9='examen-capitulo-2';10='investigacion-mercados';11='diagrama-flujo';12='recursos-humanos';13='examen-capitulos-1-4';14='documento-integrador';15='presentacion-video'}
$directories=@{}
foreach($number in 1..15){$directories[(Join-Path $notes "actividad-$number")]=Join-Path $notes ('actividad-'+$number.ToString('00')+'-'+$topics[$number])}
$mapping=@{}
foreach($sourceDir in $directories.Keys){foreach($file in Get-ChildItem -LiteralPath $sourceDir -Recurse -File){$mapping[$file.FullName]=Join-Path $directories[$sourceDir] ([IO.Path]::GetRelativePath($sourceDir,$file.FullName))}}
function Activity-Path($number,$tail){Join-Path $directories[(Join-Path $notes "actividad-$number")] $tail}
foreach($file in Get-ChildItem -LiteralPath (Join-Path $root 'investigacion-aulatex') -Recurse -File){
 $relative=[IO.Path]::GetRelativePath((Join-Path $root 'investigacion-aulatex'),$file.FullName).Replace('\','/')
 $target=if($relative.StartsWith('actividad-5/')){Activity-Path 5 ('investigacion/'+$relative.Substring(12))}else{Join-Path $notes ('materiales-generales/investigacion/'+$relative)}
 $mapping[$file.FullName]=$target
}
foreach($file in Get-ChildItem -LiteralPath $notes -Directory -Filter 'historico-word*' | ForEach-Object {Get-ChildItem -LiteralPath $_.FullName -File}){
 $match=[regex]::Match($file.Name,'Actividad-(\d+)')
 $target=if($match.Success){Activity-Path ([int]$match.Groups[1].Value) ('historico/'+$file.Directory.Name+'/'+$file.Name)}else{Join-Path $notes ('materiales-generales/historico/'+$file.Directory.Name+'/'+$file.Name)}
 $mapping[$file.FullName]=$target
}
$manual=@{
 'foro-participacion-Actividad-1.md'=(Activity-Path 1 'participacion-propuesta.md')
 'imagen-empresa-Actividad-6-amTaller.md'=(Activity-Path 6 'variantes/imagen-am-taller.md')
 'imagen-empresa-Actividad-6-industrial-revolucionaria.md'=(Activity-Path 6 'variantes/imagen-industrial-revolucionaria.md')
 'realizar-actividad-4-descripcion-empresa.md'=(Activity-Path 4 'borrador-descripcion-empresa.md')
 'caso-provisional.json'=(Join-Path $notes 'materiales-generales/casos/caso-provisional-2026-09-20.json')
 'ejecucion.json'=(Join-Path $notes 'materiales-generales/registros/ejecucion-2026-09-20.json')
 'NUMERACION-ACTIVIDADES.json'=(Join-Path $notes 'materiales-generales/registros/numeracion-actividades.json')
 'VALIDACION-ACTIVIDADES-1-15.json'=(Join-Path $notes 'materiales-generales/registros/validacion-actividades-1-15.json')
}
foreach($name in $manual.Keys){$mapping[(Join-Path $root $name)]=$manual[$name]}
$mapping[(Join-Path $notes 'actividad-5-diseno-instrumentos.md')]=Activity-Path 5 'diseno-instrumentos.md'
$mapping[(Join-Path $notes 'actividades-2-3-4-reportes.md')]=Join-Path $notes 'materiales-generales/revisiones/actividades-2-3-4.md'
$mapping[(Join-Path $notes 'confirmacion-alcance-6-7-8-2026-09-23.md')]=Join-Path $notes 'materiales-generales/confirmaciones/alcance-6-7-8-2026-09-23.md'
foreach($file in Get-ChildItem -LiteralPath $root -Filter '*.pdf' -File){
 if($file.Name -match 'Actividad-12-Recursos-Humanos-Portada-Oficial|Actividad-13-.*Portada-Oficial'){continue}
 if(Test-Path -LiteralPath ([IO.Path]::ChangeExtension($file.FullName,'.tex'))){continue}
 $match=[regex]::Match($file.Name,'Actividad-(\d+)')
 $number=if($match.Success){[int]$match.Groups[1].Value}elseif($file.Name.StartsWith('Sondeo')){10}else{0}
 if($number -gt 0){$mapping[$file.FullName]=Activity-Path $number ('historico/pdf-raiz/'+$file.Name)}
}
$records=@()
foreach($source in $mapping.Keys){if(-not(Test-Path -LiteralPath $source)){throw "Origen ausente: $source"};if(Test-Path -LiteralPath $mapping[$source]){throw "Destino existente: $($mapping[$source])"};$records+=[pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$mapping[$source]).Replace('\','/');sha256=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()}}
function Remap($absolute){if($mapping.ContainsKey($absolute)){return $mapping[$absolute]};foreach($directory in $directories.Keys){if($absolute -eq $directory){return $directories[$directory]};if($absolute.StartsWith($directory+[IO.Path]::DirectorySeparatorChar)){return Join-Path $directories[$directory] ([IO.Path]::GetRelativePath($directory,$absolute))}};return $absolute}
foreach($file in @(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.json','.py','.ps1','.tex','.bib'))){
 $target=Remap $file.FullName;$oldDir=$file.DirectoryName;$newDir=Split-Path $target;$text=[IO.File]::ReadAllText($file.FullName);$updated=$text
 if($file.Extension -eq '.md'){
 $updated=[regex]::Replace($updated,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
 $url=$match.Groups[1].Value;if($url -match '^[a-z]+://|^#'){return $match.Value};$parts=$url.Split('#',2);$absolute=[IO.Path]::GetFullPath((Join-Path $oldDir ([Uri]::UnescapeDataString($parts[0]))));$absolute=Remap $absolute;$relative=[IO.Path]::GetRelativePath($newDir,$absolute).Replace('\','/').Replace(' ','%20');if($parts.Count -gt 1){$relative+='#'+$parts[1]};return "]($relative)"})}
 if($file.Extension -eq '.json'){
 $data=$updated|ConvertFrom-Json
 function Rebase($node){if($node -is [array]){foreach($child in $node){Rebase $child};return};if($node -isnot [pscustomobject]){return};foreach($prop in $node.PSObject.Properties){if($prop.Value -is [string] -and $prop.Value.Length -lt 600 -and $prop.Value -notmatch '^[a-z]+://|[\r\n]' -and $prop.Name -notin @('origen','location_original','text','texto','title','respaldo')){foreach($base in @($oldDir,$root,'C:/Users/Sysx/Documents/AulaTeX-Academico')){try{$absolute=[IO.Path]::GetFullPath((Join-Path $base $prop.Value))}catch{continue};$newAbsolute=Remap $absolute;if($newAbsolute -ne $absolute -or ($oldDir -ne $newDir -and (Test-Path -LiteralPath $absolute -PathType Leaf))){$newBase=if($base -eq $oldDir){$newDir}else{$base};$prop.Value=[IO.Path]::GetRelativePath($newBase,$newAbsolute).Replace('\','/');break}}}else{Rebase $prop.Value}}}
 Rebase $data;$updated=$data|ConvertTo-Json -Depth 100}
 if($file.Extension -in @('.py','.ps1','.tex','.bib')){foreach($record in $records){$updated=$updated.Replace($record.origen,$record.destino)}}
 if($target -ne $file.FullName -or $updated -ne $text){New-Item -ItemType Directory -Path $newDir -Force|Out-Null;[IO.File]::WriteAllText($target,$updated,[Text.UTF8Encoding]::new($false))}
}
foreach($source in $mapping.Keys){$target=$mapping[$source];if(Test-Path -LiteralPath $target){Remove-Item -LiteralPath $source}else{New-Item -ItemType Directory -Path (Split-Path $target) -Force|Out-Null;Move-Item -LiteralPath $source -Destination $target}}
foreach($record in $records){if([IO.Path]::GetExtension($record.destino) -notin @('.md','.json','.py','.ps1','.tex','.bib')){if((Get-FileHash -LiteralPath (Join-Path $root $record.destino)).Hash.ToLowerInvariant() -ne $record.sha256){throw 'Hash incorrecto'}}}
foreach($directory in @($directories.Keys)+@(Join-Path $root 'investigacion-aulatex')+@(Get-ChildItem -LiteralPath $notes -Directory -Filter 'historico-word*'|ForEach-Object FullName)){if(Test-Path -LiteralPath $directory){if(Get-ChildItem -LiteralPath $directory -Recurse -File){throw "Carpeta no vacia: $directory"};Remove-Item -LiteralPath $directory -Recurse}}
[IO.File]::WriteAllText((Join-Path $notes 'materiales-generales/registros/orden-notas-2026-10-10.json'),(@{fecha='2026-10-10';movimientos=$records;nota='Hashes previos a actualizacion de rutas de texto; archivos activos y Entregas conservados'}|ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
Write-Output "$($records.Count) archivos reubicados; 15 carpetas de actividad renombradas y binarios verificados."