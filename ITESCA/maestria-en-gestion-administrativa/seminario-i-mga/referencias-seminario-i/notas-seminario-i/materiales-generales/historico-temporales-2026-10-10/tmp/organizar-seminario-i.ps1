$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
$refs = 'referencias-seminario-i'
$notes = "$refs/notas-seminario-i"
$pairs = @{
 "$refs/Formato 01. Matriz de estado del arte.docx"="$notes/actividad-3-estado-del-arte/materiales/Formato 01 - Matriz de estado del arte.docx"
 "$refs/Formato 01. Matriz de estado del arte.rtf"="$notes/actividad-3-estado-del-arte/materiales/Formato 01 - Matriz de estado del arte.rtf"
 "$notes/unidad-1/consideraciones-preliminares.md"="$notes/actividad-1-ruta-titulacion/consideraciones-preliminares.md"
 "$notes/unidad-2/revision-actividad-04.md"="$notes/actividad-4-errores-circulo-covey/revision-actividad-04.md"
 "$notes/unidad-2/matriz-de-consistencia.md"="$notes/materiales-generales/coherencia-metodologica.md"
 "$notes/unidad-3/anteproyecto.md"="$notes/materiales-generales/anteproyecto-acumulativo.md"
 "$refs/metodologia/hernandez-sampieri-et-al-2014-metodologia-investigacion.pdf"="$refs/libros-seminario-i/Metodologia de la investigacion - Hernandez Sampieri y coautores - 2014.pdf"
 "$refs/metodologia/navarro-chavez-2014-epistemologia-metodologia-investigacion.pdf"="$refs/libros-seminario-i/Epistemologia y metodologia de la investigacion - Navarro Chavez - 2014.pdf"
 "$refs/metodologia/covey-2014-siete-habitos.pdf"="$refs/libros-seminario-i/Los siete habitos de la gente altamente efectiva - Stephen Covey - 2014.pdf"
 "$refs/metodologia/apa-reference-guide.pdf"="$refs/libros-seminario-i/Reference Guide for Journal Articles, Books, and Edited Book Chapters - APA - 2026.pdf"
 "$refs/metodologia/apa-reference-guide.txt"="$refs/libros-seminario-i/Reference Guide for Journal Articles, Books, and Edited Book Chapters - APA - 2026.txt"
 "$refs/metodologia/apa-reference-guide.json"="$notes/actividad-2-normas-apa/procedencia-guia-APA.json"
 'tarea6/materiales/Material para ejemplo.docx'="$notes/actividad-6-formato-institucional/materiales/Material para ejemplo.docx"
 'tarea6/materiales/Portada.docx'="$notes/actividad-6-formato-institucional/materiales/Portada.docx"
}
foreach($file in Get-ChildItem -LiteralPath (Join-Path $root "$refs/actividad-10") -Recurse -File){
 $old=[IO.Path]::GetRelativePath($root,$file.FullName).Replace('\','/')
 $tail=[IO.Path]::GetRelativePath((Join-Path $root "$refs/actividad-10"),$file.FullName).Replace('\','/')
 if($tail -eq '3.3-Formulacion-de-objetivos.pdf'){$tail='materiales/3.3 - Formulacion de objetivos.pdf'}
 $pairs[$old]="$notes/actividad-10-objetivos/$tail"
}
$mapping=@{}; $records=@()
foreach($old in $pairs.Keys){
 $source=[IO.Path]::GetFullPath((Join-Path $root $old)); $target=[IO.Path]::GetFullPath((Join-Path $root $pairs[$old]))
 if(-not(Test-Path -LiteralPath $source)){throw "Origen ausente: $old"}; if(Test-Path -LiteralPath $target){throw "Destino existente: $target"}
 $mapping[$source]=$target
 $records+=[pscustomobject]@{origen=$old;destino=$pairs[$old];sha256=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()}
}
$documents=@(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.json','.tex','.bib','.py'))
foreach($file in $documents){
 $newPath=$file.FullName; if($mapping.ContainsKey($newPath)){$newPath=$mapping[$newPath]}
 $text=[IO.File]::ReadAllText($file.FullName); $updated=$text
 foreach($source in $mapping.Keys){
  $old=[IO.Path]::GetRelativePath($file.DirectoryName,$source).Replace('\','/')
  $new=[IO.Path]::GetRelativePath((Split-Path $newPath),$mapping[$source]).Replace('\','/')
  foreach($prefix in @('', './')){
   $updated=$updated.Replace("]($prefix$old)","]($new)").Replace("]($prefix$($old.Replace(' ','%20')))","]($($new.Replace(' ','%20')))")
  }
  $updated=$updated.Replace($source.Replace('\','/'),$mapping[$source].Replace('\','/'))
  foreach($pair in @(@($old,$new),@([IO.Path]::GetRelativePath($root,$source).Replace('\','/'),[IO.Path]::GetRelativePath($root,$mapping[$source]).Replace('\','/')))){
   $updated=$updated.Replace('"'+$pair[0]+'"','"'+$pair[1]+'"').Replace("'"+$pair[0]+"'","'"+$pair[1]+"'").Replace('{'+$pair[0]+'}','{'+$pair[1]+'}').Replace('`'+$pair[0]+'`','`'+$pair[1]+'`')
  }
 }
 if($file.Name -eq 'procedencia-guia-APA.json' -or $file.FullName.EndsWith('metodologia\apa-reference-guide.json')){
  $data=$updated | ConvertFrom-Json
  $data.file=[IO.Path]::GetRelativePath((Split-Path $newPath),(Join-Path $root $pairs["$refs/metodologia/apa-reference-guide.pdf"])).Replace('\','/')
  $data.extraction=[IO.Path]::GetRelativePath((Split-Path $newPath),(Join-Path $root $pairs["$refs/metodologia/apa-reference-guide.txt"])).Replace('\','/')
  $updated=$data | ConvertTo-Json -Depth 20
 }
 if($file.FullName.EndsWith('tarea6\generar_tarea6.py')){$updated=$updated.Replace('MATERIALS = ROOT / "materiales"','MATERIALS = ROOT.parent / "referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/materiales"')}
 if($file.FullName.EndsWith('tarea6\importar_materiales.py')){$updated=$updated.Replace('Path(__file__).parent / "materiales"','Path(__file__).resolve().parents[1] / "referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/materiales"')}
 if($file.FullName.EndsWith('tarea6\validar_tarea6.py')){$updated=$updated.Replace('ROOT / "materiales" / "Material para ejemplo.docx"','ROOT.parent / "referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/materiales/Material para ejemplo.docx"')}
 if($updated -ne $text -or $newPath -ne $file.FullName){New-Item -ItemType Directory -Path (Split-Path $newPath) -Force | Out-Null; [IO.File]::WriteAllText($newPath,$updated,[Text.UTF8Encoding]::new($false))}
}
foreach($source in $mapping.Keys){$target=$mapping[$source]; if(Test-Path -LiteralPath $target){Remove-Item -LiteralPath $source}else{New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null; Move-Item -LiteralPath $source -Destination $target}}
foreach($record in $records){if([IO.Path]::GetExtension($record.destino) -in @('.pdf','.docx','.rtf','.txt')){if((Get-FileHash -LiteralPath (Join-Path $root $record.destino)).Hash.ToLowerInvariant() -ne $record.sha256){throw 'Contenido original cambiado'}}}
Get-ChildItem -LiteralPath (Join-Path $root $refs) -Directory -Recurse | Sort-Object {$_.FullName.Length} -Descending | ForEach-Object {if(-not(Get-ChildItem -LiteralPath $_.FullName)){Remove-Item -LiteralPath $_.FullName}}
$recordPath=Join-Path $root "$notes/materiales-generales/registro-organizacion-2026-10-10.json"
[IO.File]::WriteAllText($recordPath,(@{fecha='2026-10-10';movimientos=$records;nota='Hashes previos; solo rutas locales actualizadas en documentos de texto'} | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
Write-Output "$($records.Count) archivos organizados; PDF, DOCX, RTF y TXT originales integros."