$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
$base = Join-Path $root 'referencias-antecedentes-de-los-derechos-humanos/notas-antecedentes-de-los-derechos-humanos/materiales-generales'
$mapping = @{}
$titles = @{'C-digo-de--tica'='Codigo de Etica - UnADM';'Lineamientos-de-Evaluaci-n-del-Aprendizaje'='Lineamientos de evaluacion del aprendizaje - UnADM';'Lineamientos-de-uso-de-IA'='Lineamientos de uso de inteligencia artificial - UnADM';'Reglamento-Universitario'='Reglamento Universitario - UnADM'}
foreach($file in Get-ChildItem -LiteralPath $base -File){
    foreach($prefix in $titles.Keys){
        if($file.BaseName.StartsWith($prefix)){ $mapping[$file.FullName]=Join-Path $base ('normativa-institucional/'+$titles[$prefix]+$file.Extension); break }
    }
}
foreach($file in Get-ChildItem -LiteralPath (Join-Path $base 'capturas-aula') -File){
    $name=$file.Name
    if($name -eq 'curso-aula.txt'){ $name='Contenido del curso - Antecedentes de los Derechos Humanos.txt' }
    elseif($name -eq 'modulo-0.txt'){ $name='Avisos y novedades generales.txt' }
    elseif($file.Length -eq 0){ $name='capturas-sin-contenido/Captura sin contenido - indice '+($file.BaseName -replace 'modulo-','')+'.txt' }
    $mapping[$file.FullName]=Join-Path $base ('capturas-aula/'+$name)
}
$oldAudit=Join-Path $base 'auditoria-semana-2-2026-10-09'
foreach($file in Get-ChildItem -LiteralPath $oldAudit -Recurse -File){
    $relative=[IO.Path]::GetRelativePath($oldAudit,$file.FullName).Replace('\','/').Replace('20261009-185726-activity-01-observer','observacion-resena-2026-10-09-185726')
    if($relative -eq 'plataforma.json'){ $relative='Estado de plataforma - S2 - 2026-10-09.json' }
    $mapping[$file.FullName]=Join-Path $base ('auditorias/semana-2-2026-10-09/'+$relative)
}
$records=@()
foreach($source in $mapping.Keys){
    $target=$mapping[$source]
    if($source -eq $target){continue}
    $hash=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    if(Test-Path -LiteralPath $target){
        if((Get-FileHash -LiteralPath $target).Hash.ToLowerInvariant() -ne $hash){throw 'Colision de contenido'}
        Remove-Item -LiteralPath $source
        $action='duplicado exacto consolidado'
    }else{Move-Item -LiteralPath $source -Destination $target; $action='reubicado'}
    if((Get-FileHash -LiteralPath $target).Hash.ToLowerInvariant() -ne $hash){throw 'Hash cambiado'}
    $records+=[pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$target).Replace('\','/');sha256=$hash;accion=$action}
}
foreach($file in Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object Extension -in @('.md','.json')){
    $newDirectory=$file.DirectoryName
    $oldDirectory=$newDirectory
    $oldSource=@($mapping.Keys | Where-Object {$mapping[$_] -eq $file.FullName}) | Select-Object -First 1
    if($oldSource){$oldDirectory=Split-Path $oldSource}
    $content=[IO.File]::ReadAllText($file.FullName)
    if($file.Extension -eq '.md'){
        $content=[regex]::Replace($content,'\]\(([^)]+)\)',[Text.RegularExpressions.MatchEvaluator]{param($match)
            $url=$match.Groups[1].Value
            if($url -match '^[a-z]+://|^#'){return $match.Value}
            $parts=$url.Split('#',2)
            $absolute=[IO.Path]::GetFullPath((Join-Path $oldDirectory ([Uri]::UnescapeDataString($parts[0]))))
            if($mapping.ContainsKey($absolute)){$absolute=$mapping[$absolute]}
            $relative=[IO.Path]::GetRelativePath($newDirectory,$absolute).Replace('\','/').Replace(' ','%20')
            if($parts.Count -gt 1){$relative+='#'+$parts[1]}
            return "]($relative)"
        })
    }else{
        $data=$content | ConvertFrom-Json
        function Fix-Node($node){
            if($node -is [array]){foreach($child in $node){Fix-Node $child};return}
            if($node -isnot [pscustomobject]){return}
            foreach($property in $node.PSObject.Properties){
                if($property.Value -is [string] -and $property.Value -notmatch '^[a-z]+://|[\r\n]' -and $property.Name -notin @('origen','ruta_historica','texto')){
                    $bases=@($oldDirectory,$root)
                    if($property.Name -eq 'destino'){$bases=@($root,$oldDirectory)}
                    foreach($directory in $bases){
                        try{$absolute=[IO.Path]::GetFullPath((Join-Path $directory $property.Value))}catch{continue}
                        if($mapping.ContainsKey($absolute)){
                            $newBase=$newDirectory
                            if($directory -eq $root){$newBase=$root}
                            $property.Value=[IO.Path]::GetRelativePath($newBase,$mapping[$absolute]).Replace('\','/');break
                        }
                        if($oldDirectory -ne $newDirectory -and (Test-Path -LiteralPath $absolute -PathType Leaf)){
                            $property.Value=[IO.Path]::GetRelativePath($newDirectory,$absolute).Replace('\','/');break
                        }
                    }
                }else{Fix-Node $property.Value}
            }
        }
        Fix-Node $data
        $content=$data | ConvertTo-Json -Depth 100
    }
    [IO.File]::WriteAllText($file.FullName,$content,[Text.UTF8Encoding]::new($false))
}
Get-ChildItem -LiteralPath $oldAudit -Recurse -Directory | Sort-Object {$_.FullName.Length} -Descending | ForEach-Object {if(-not(Get-ChildItem -LiteralPath $_.FullName)){Remove-Item -LiteralPath $_.FullName}}
if(-not(Get-ChildItem -LiteralPath $oldAudit)){Remove-Item -LiteralPath $oldAudit}
[IO.File]::WriteAllText((Join-Path $base 'registros-organizacion/orden-materiales-generales.json'),(@{fecha='2026-10-10';movimientos=$records;nota='Hashes anteriores a actualizacion de rutas en documentos de texto'} | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
foreach($file in Get-ChildItem -LiteralPath $root -Recurse -Filter '*.md'){
    foreach($match in [regex]::Matches([IO.File]::ReadAllText($file.FullName),'\]\(([^)]+)\)')){
        $url=$match.Groups[1].Value
        if($url -match '^[a-z]+://|^#'){continue}
        if(-not(Test-Path -LiteralPath (Join-Path $file.DirectoryName ([Uri]::UnescapeDataString(($url -split '#')[0]))))){throw "Enlace roto: $url"}
    }
}
Write-Output "$($records.Count) operaciones verificadas; enlaces Markdown validos."