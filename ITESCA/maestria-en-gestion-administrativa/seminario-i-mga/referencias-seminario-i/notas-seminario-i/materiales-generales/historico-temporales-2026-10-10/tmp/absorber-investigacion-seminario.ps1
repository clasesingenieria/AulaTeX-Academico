$ErrorActionPreference='Stop'
$root='C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
$repo='C:/Users/Sysx/Documents/AulaTeX-Academico'
$notes='referencias-seminario-i/notas-seminario-i'
$oldFolder=Join-Path $root 'investigacion-aulatex'
$mapping=@{}
foreach($file in Get-ChildItem -LiteralPath $oldFolder -Recurse -File){
 $relative=[IO.Path]::GetRelativePath($oldFolder,$file.FullName).Replace('\','/')
 if($relative.StartsWith('actividad-10/')){$destination="$notes/actividad-10-objetivos/investigacion/"+$relative.Substring('actividad-10/'.Length)}
 else{$destination="$notes/materiales-generales/investigacion/"+$relative}
 $mapping[$file.FullName]=Join-Path $root $destination
}
$program=Join-Path $root 'programa-analitico-seminario-i.md'
$readme=Join-Path $root 'Readme - Seminario I.md'
$mapping[$program]=$readme
$records=@()
foreach($source in $mapping.Keys){if($source -ne $program -and (Test-Path -LiteralPath $mapping[$source])){throw 'Destino existente'};$records+=[pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$mapping[$source]).Replace('\','/');sha256=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()}}
$programText=[IO.File]::ReadAllText($program)
$programText=[regex]::Replace($programText,'(?m)^(#{1,5}) ','$1# ')
$readmeText=[IO.File]::ReadAllText($readme)
if($readmeText.Contains('## Programa analítico')){throw 'Programa ya integrado'}
$readmeText+="`n`n"+$programText.Trim()+"`n`nEl programa anterior se integra sin cambiar su calendario o porcentajes. Esta consolidacion no acredita una consulta nueva del aula ni actualiza su vigencia.`n"
[IO.File]::WriteAllText($readme,$readmeText,[Text.UTF8Encoding]::new($false))
foreach($file in @(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.json','.py','.tex','.bib'))){
 if($file.FullName -eq $program){continue}
 $target=$file.FullName;if($mapping.ContainsKey($target)){$target=$mapping[$target]}
 $oldDir=$file.DirectoryName;$newDir=Split-Path $target
 $text=[IO.File]::ReadAllText($file.FullName);$updated=$text
 if($file.Extension -eq '.md'){
  $updated=[regex]::Replace($updated,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
   $url=$match.Groups[1].Value;if($url -match '^[a-z]+://|^#'){return $match.Value}
   $parts=$url.Split('#',2);$absolute=[IO.Path]::GetFullPath((Join-Path $oldDir ([Uri]::UnescapeDataString($parts[0]))))
   if($mapping.ContainsKey($absolute)){$absolute=$mapping[$absolute]}
   $relative=[IO.Path]::GetRelativePath($newDir,$absolute).Replace('\','/').Replace(' ','%20');if($parts.Count -gt 1){$relative+='#'+$parts[1]};return "]($relative)"
  })
 }
 if($file.Extension -eq '.json'){
  $data=$updated | ConvertFrom-Json
  function Rebase($node){
   if($node -is [array]){foreach($child in $node){Rebase $child};return};if($node -isnot [pscustomobject]){return}
   foreach($prop in $node.PSObject.Properties){
    if($prop.Value -is [string] -and $prop.Name -notin @('origen','texto','text','title','location_original') -and $prop.Value.Length -lt 650 -and $prop.Value -notmatch '^[a-z]+://|[\r\n]'){
     foreach($base in @($oldDir,$root,$repo)){
      try{$absolute=[IO.Path]::GetFullPath((Join-Path $base $prop.Value))}catch{continue}
      $mapped=$mapping.ContainsKey($absolute);if($mapped){$absolute=$mapping[$absolute]}
      if($mapped -or ($oldDir -ne $newDir -and (Test-Path -LiteralPath $absolute -PathType Leaf))){$newBase=$base;if($base -eq $oldDir){$newBase=$newDir};$prop.Value=[IO.Path]::GetRelativePath($newBase,$absolute).Replace('\','/');break}
     }
    }else{Rebase $prop.Value}
   }
  }
  Rebase $data;$updated=$data | ConvertTo-Json -Depth 100
 }
 if($file.Extension -in @('.py','.tex','.bib')){foreach($record in $records){if($record.origen -ne 'programa-analitico-seminario-i.md'){$updated=$updated.Replace($record.origen,$record.destino)}}}
 if($file.Extension -eq '.py' -and $file.FullName.StartsWith($oldFolder)){
  $updated=$updated.Replace('ROOT = Path(__file__).resolve().parents[6]','ROOT = Path(__file__).resolve().parents[7]')
  $updated=$updated.Replace('SUBJECT = Path(__file__).resolve().parents[3]','SUBJECT = Path(__file__).resolve().parents[4]')
 }
 if($updated -ne $text -or $target -ne $file.FullName){New-Item -ItemType Directory -Path $newDir -Force | Out-Null;[IO.File]::WriteAllText($target,$updated,[Text.UTF8Encoding]::new($false))}
}
foreach($source in $mapping.Keys){if($source -eq $program){continue};$target=$mapping[$source];if(-not(Test-Path -LiteralPath $target)){New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null;Move-Item -LiteralPath $source -Destination $target}else{Remove-Item -LiteralPath $source}}
foreach($record in $records){if([IO.Path]::GetExtension($record.destino) -in @('.pdf','.docx','.png','.aux','.log','.fls','.toc','.nav','.snm','.out','.fdb_latexmk','.txt')){if((Get-FileHash -LiteralPath (Join-Path $root $record.destino)).Hash.ToLowerInvariant() -ne $record.sha256){throw 'Archivo original cambiado'}}}
Remove-Item -LiteralPath $program
if(Get-ChildItem -LiteralPath $oldFolder -Recurse -File){throw 'Carpeta no absorbida'}
Remove-Item -LiteralPath $oldFolder -Recurse
[IO.File]::WriteAllText((Join-Path $root "$notes/materiales-generales/absorcion-investigacion-2026-10-10.json"),(@{fecha='2026-10-10';movimientos=$records;nota='Hashes previos al ajuste de rutas en textos; programa integrado en Readme'} | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
Write-Output "$($records.Count-1) archivos de investigacion reubicados; programa integrado y carpetas originales retiradas."