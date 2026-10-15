$ErrorActionPreference='Stop'
$root='C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
$before=@{}
Get-ChildItem -LiteralPath (Join-Path $root 'entregas-seminario-i') -File | ForEach-Object {$before[$_.Name]=(Get-FileHash -LiteralPath $_.FullName).Hash}
$names=@(Get-ChildItem -LiteralPath $root -Directory | Where-Object Name -ieq 'entregas-seminario-i')
if($names.Count -ne 1){throw 'Carpeta de entregas ambigua'}
if($names[0].Name -cne 'entregas-seminario-i'){
 Rename-Item -LiteralPath $names[0].FullName -NewName '__entregas_case_tmp'
 Rename-Item -LiteralPath (Join-Path $root '__entregas_case_tmp') -NewName 'entregas-seminario-i'
}
foreach($file in Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.json','.py','.tex','.bib','.ps1','.sh')){
 $text=[IO.File]::ReadAllText($file.FullName)
 $updated=$text.Replace('entregas-seminario-i/','entregas-seminario-i/').Replace('entregas-seminario-i\','entregas-seminario-i\').Replace('"entregas-seminario-i"','"entregas-seminario-i"').Replace("'entregas-seminario-i'","'entregas-seminario-i'")
 if($updated -ne $text){[IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false))}
}
foreach($name in $before.Keys){if((Get-FileHash -LiteralPath (Join-Path $root ('entregas-seminario-i/'+$name))).Hash -ne $before[$name]){throw "Archivo de entrega cambiado: $name"}}
Write-Output 'Entregas normalizada; todos sus archivos conservan SHA256.'