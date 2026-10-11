$ErrorActionPreference = 'Stop'
$root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
$refs = Join-Path $root 'referencias-antecedentes-de-los-derechos-humanos'
$library = Join-Path $refs 'libros-antecedentes-de-los-derechos-humanos'
$titles = @{
 '21.-20DERECHO-20CONSTITUCIONAL-20-E2-80-94-20Elisur-20Arteaga'='Derecho constitucional - Elisur Arteaga'
 'Andrade_CPEUM-20comentada'='Constitucion Politica de los Estados Unidos Mexicanos comentada - Eduardo Andrade Sanchez'
 'Argumentacion-20y-20lenguaje-20juridico'='Argumentacion y lenguaje juridico - Aplicacion al analisis de una sentencia de la SCJN'
 'Curso-20de-20Derechos-20Humanos'='Curso de derechos humanos'
 'Derecho-20de-20los-20pueblso-20indigenas-20en-20sistemas-20de-20DDHH'='Los derechos de los pueblos indigenas y tribales en los sistemas de derechos humanos'
 'Derechos-20Humanos-20y-20Justicia-20Penal'='Derechos humanos y justicia penal - Javier Llobet Rodriguez'
 'Derechos-20Humanos'='Derechos humanos - Manual para parlamentarios numero 26 - UIP y ONU'
 'Diccionario-20Derechos-20Humanos'='Diccionario analitico de derechos humanos e integracion juridica'
 'Dignidad-20Humana'='Dignidad humana, derechos humanos y derecho a la vida'
 'el-20arte-20y-20los-20derechos-20humanos'='El arte y los derechos humanos'
 'El_neoconstitucionalismo_y_la_constitucionalizaci-C3-B3nPasiConsti'='El neoconstitucionalismo y la constitucionalizacion'
 'Epistemolog-C3-ADa-20y-20garantismo-20'='Epistemologia juridica y garantismo - Luigi Ferrajoli'
 'Ferrajoli-20--20El-20paradigma-20garantista-20'='El paradigma garantista - Luigi Ferrajoli'
 'Ferrajoli-20--20Garantismo-20Penal'='Garantismo penal - Luigi Ferrajoli'
 'Fundamentos-20axiol-C3-B3gicos-20de-20los-20DDHH'='Fundamentos axiologicos de los derechos humanos - Organos constitucionales y supranacionales'
 'Garant-C3-ADas-20Constitucionales-20'='Garantias constitucionales del proceso'
 'Garant-C3-ADas-20Constitucionales-Rafael-20Mart-C3-ADnez-20Morales'='Garantias constitucionales - Rafael Martinez Morales'
 'Garantias-20Constitucionales-20-E2-80-94-20Jesus-20de-20La-20Fuente-20Rodriguez'='Garantias constitucionales - Roberto Carlos Fonseca Lujan'
 'Generaciones-20de-20los-20Derechos-20Humanos'='Las generaciones de los derechos humanos - Ernesto Rey Cantor y coautoras'
 'Historia_mnima_del_neoliberalismo'='Historia minima del neoliberalismo'
 'INTERPRETACION-20CONSTITUCIONAL'='Interpretacion constitucional'
 'Introducci_n_a_la_Inteligencia_Artificial_para_Abogados_1773528805'='Introduccion a la inteligencia artificial para abogados - Jose Sepulveda Sanchis y Julia Martinez Candado'
 'libro-sobre-dignidad-y-principios'='Sobre la dignidad y los principios - M. Casado'
 'Manual-20de-20Normas-20APA-207a'='Normas APA 7a edicion - Guia de citacion y referenciacion - Deixa Moreno y Javier Carrillo'
 'Nogueira_Alcala_Humberto_Teoria_y_Dogmatica_de_Los_Derechos_FundamentalesSerie'='Teoria y dogmatica de los derechos fundamentales - Humberto Nogueira Alcala'
 'Principio-20Pro-20persona'='Principio pro persona - Ximena Medellin Urquiaga'
 'Teoria-20y-20Dogmatica-20de-20Los-20Derechos-20Fundamentales'='Teoria y dogmatica de los derechos fundamentales - Humberto Nogueira Alcala'
}
$localNames = @{
 'Constitucion Politica de los Es - Camara de Diputados del H. Cong.pdf'='Constitucion Politica de los Estados Unidos Mexicanos - Camara de Diputados.pdf'
 'CPEUM-consulta-2026-10-09.pdf'='Constitucion Politica de los Estados Unidos Mexicanos - Consulta 2026-10-09.pdf'
 'Derechos humanos, teorias y doc - Luis Manuel Marcano Salazar.pdf'='Derechos humanos, teorias y doctrina - Luis Manuel Marcano Salazar.pdf'
 '_Como se hicieron los derechos - Ricardo Rabinovich Berkman.pdf'='Como se hicieron los derechos humanos - Ricardo Rabinovich Berkman.pdf'
}
$moves = [System.Collections.Generic.List[object]]::new()
$reserved = @{}
foreach ($file in Get-ChildItem -LiteralPath $refs -File | Where-Object { $_.Name -match '^\d+-' -and $_.Extension -in @('.pdf','.txt') }) {
    $match = [regex]::Match($file.BaseName,'^(\d+)-(.+)$')
    $key = $match.Groups[2].Value
    if (-not $titles.ContainsKey($key)) { throw "Titulo no clasificado: $key" }
    $name = "$($titles[$key]) - captura $($match.Groups[1].Value)$($file.Extension)"
    $target = Join-Path $library $name
    if ((Test-Path -LiteralPath $target) -or $reserved.ContainsKey($target)) {
        $name = "$($titles[$key]) - captura $($match.Groups[1].Value) - variante$($file.Extension)"
        $target = Join-Path $library $name
    }
    if ((Test-Path -LiteralPath $target) -or $reserved.ContainsKey($target)) { throw 'Colision de nombres' }
    $reserved[$target] = $true
    $moves.Add([pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$file.FullName).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$target).Replace('\','/');sha256=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()})
}
foreach ($name in $localNames.Keys) {
    $source = Join-Path $library $name
    if (Test-Path -LiteralPath $source) {
        $target = Join-Path $library $localNames[$name]
        if (Test-Path -LiteralPath $target) { throw 'Destino existente' }
        $moves.Add([pscustomobject]@{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$target).Replace('\','/');sha256=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()})
    }
}
foreach ($move in $moves) {
    Move-Item -LiteralPath (Join-Path $root $move.origen) -Destination (Join-Path $root $move.destino)
    if ((Get-FileHash -LiteralPath (Join-Path $root $move.destino)).Hash.ToLowerInvariant() -ne $move.sha256) { throw 'Hash cambiado' }
}
function Update-Node($node, $directory) {
    if ($node -is [array]) { foreach ($child in $node) { Update-Node $child $directory }; return }
    if ($node -isnot [pscustomobject]) { return }
    foreach ($property in $node.PSObject.Properties) {
        if ($property.Value -is [string] -and $property.Name -in @('file','archivo','archivo_local','destino')) {
            foreach ($move in $moves) {
                $old = [IO.Path]::GetRelativePath($directory,(Join-Path $root $move.origen)).Replace('\','/')
                if ($property.Value -eq $old) { $property.Value = [IO.Path]::GetRelativePath($directory,(Join-Path $root $move.destino)).Replace('\','/'); break }
                if ($property.Name -eq 'destino' -and $property.Value -eq $move.origen) { $property.Value=$move.destino; break }
            }
        } else { Update-Node $property.Value $directory }
    }
}
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -Filter '*.json' -File | Where-Object { $_.Name -like 'inventario*' -or $_.Name -eq 'organizacion-materiales.json' }) {
    $data = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    Update-Node $data $file.DirectoryName
    [IO.File]::WriteAllText($file.FullName,($data | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
}
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.Extension -in @('.md','.tex','.bib') }) {
    $text = [IO.File]::ReadAllText($file.FullName)
    $updated = $text
    foreach ($move in $moves) {
        $old = [IO.Path]::GetRelativePath($file.DirectoryName,(Join-Path $root $move.origen)).Replace('\','/')
        $new = [IO.Path]::GetRelativePath($file.DirectoryName,(Join-Path $root $move.destino)).Replace('\','/')
        $updated = $updated.Replace("]($old)","]($new)").Replace("]($($old.Replace(' ','%20')))","]($($new.Replace(' ','%20')))")
    }
    if ($updated -ne $text) { [IO.File]::WriteAllText($file.FullName,$updated,[Text.UTF8Encoding]::new($false)) }
}
[IO.File]::WriteAllText((Join-Path $refs 'renombrado-bibliografia.json'),(@{fecha='2026-10-10';criterio='Titulo legible y autoria comprobada; captura distingue copias conservadas';movimientos=$moves.ToArray()} | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
Write-Output "$($moves.Count) documentos bibliograficos renombrados y cotejados por SHA256."